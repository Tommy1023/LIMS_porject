from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select, func
from database import engine, create_db_and_tables, PrepBatch, Method, DigestionCondition, TestRecord, lab_round
from contextlib import asynccontextmanager
from datetime import datetime
from pydantic import BaseModel

# 初始化與生命週期
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    # 初始化一些假資料方便測試 (若資料庫為空)
    with Session(engine) as session:
        if not session.exec(select(Method)).first():
            print("初始化測試資料...")
            m = Method(method_code="M103C", method_name="ICP-MS 重金屬檢測", default_weight=0.5, is_amount=0.5)
            d = DigestionCondition(temp_celsius=120, duration_min=120, reagents="HNO3: 5ml")
            session.add(m)
            session.add(d)
            session.commit()
    yield

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# Pydantic 模型用於接收 JSON 數據
class WeightUpdate(BaseModel):
    weight: float
    
# --- 0. 首頁入口  ---
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- 1. 建立新批次 (自動編號邏輯) ---
@app.post("/create_batch")
async def create_batch(method_code: str = Form(...), operator: str = Form(...)):
    with Session(engine) as session:
        # 找方法與預設消化條件
        method = session.exec(select(Method).where(Method.method_code == method_code)).first()
        if not method: raise HTTPException(404, "Method not found")
        digest = session.exec(select(DigestionCondition)).first() # 暫時抓第一個

        # 自動編號: YYYYMMDD-Code-Seq
        today_str = datetime.now().strftime("%Y%m%d")
        base_no = f"{today_str}-{method_code}"
        count = session.exec(select(func.count(PrepBatch.id)).where(PrepBatch.batch_no.like(f"{base_no}%"))).one()
        new_batch_no = f"{base_no}-{count + 1}"

        # 建立批次
        new_batch = PrepBatch(
            batch_no=new_batch_no, 
            method_id=method.id, 
            digestion_id=digest.id, 
            operator=operator, 
            prep_date=today_str
        )
        session.add(new_batch)
        session.commit()
        session.refresh(new_batch)
        
        # 自動建立一些測試樣品 (模擬)
        for i in range(1, 6):
            rec = TestRecord(batch_id=new_batch.id, job_no=f"JOB{today_str}{i:03d}", sample_name=f"Sample-{i}")
            session.add(rec)
        session.commit()
        
        return {"status": "ok", "batch_no": new_batch_no}

# --- 2. 批次作業介面 (HTML) ---
@app.get("/batch/{batch_no}")
async def view_batch(request: Request, batch_no: str):
    with Session(engine) as session:
        batch = session.exec(select(PrepBatch).where(PrepBatch.batch_no == batch_no)).first()
        if not batch: raise HTTPException(404, "Batch not found")
        # 確保關聯資料載入
        records = sorted(batch.records, key=lambda r: r.job_no)
        
        return templates.TemplateResponse("batch_view.html", {
            "request": request, 
            "batch": batch, 
            "records": records
        })

# --- 3. 條碼掃描更新重量 API ---
@app.patch("/record/{record_id}")
async def update_record_weight(record_id: int, data: WeightUpdate):
    with Session(engine) as session:
        record = session.get(TestRecord, record_id)
        if not record: raise HTTPException(404, "Record not found")
        
        record.weight = data.weight
        record.status = "Saved"
        # 這裡未來可以加入即時計算 final_result 的邏輯
        session.add(record)
        session.commit()
        return {"status": "success", "new_weight": record.weight}