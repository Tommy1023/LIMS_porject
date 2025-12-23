import pandas as pd
import io
from fastapi import FastAPI, Depends, HTTPException,UploadFile, File
from sqlmodel import Session, select
from typing import List
from contextlib import asynccontextmanager # 1. 引入這個工具

# 1. 初始化 FastAPI 實例
# 引入你的資料庫邏輯
from database import engine, Sample, create_db_and_tables

# 2. 定義 lifespan 邏輯
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 【啟動時執行】
    print("正在啟動系統，檢查資料庫...")
    create_db_and_tables()
    
    yield # 分隔線：yield 之前是啟動，之後是關閉
    
    # 【關閉時執行】
    print("正在關閉系統...")

# 3. 初始化 FastAPI 時傳入 lifespan
app = FastAPI(
    title="我的實驗室 LIMS 系統", 
    lifespan=lifespan # 綁定 lifespan
)

# 3. 首頁路由
@app.get("/")
def read_root():
    return {
        "status": "Online",
        "message": "LIMS 系統運行中",
        "endpoints": {
            "查看樣品清單": "/samples",
            "互動式 API 文件": "/docs"
        }
    }

# 4. 取得所有樣品清單的 API
@app.get("/samples", response_model=List[Sample])
def get_all_samples():
    with Session(engine) as session:
        # 執行 SELECT * FROM sample
        statement = select(Sample)
        results = session.exec(statement).all()
        return results

# 5. 根據樣品編號查詢特定數據的 API
@app.get("/samples/{sample_id}", response_model=Sample)
def get_sample_by_id(sample_id: str):
    with Session(engine) as session:
        statement = select(Sample).where(Sample.sample_id == sample_id)
        result = session.exec(statement).first()
        if not result:
            raise HTTPException(status_code=404, detail="找不到該樣品數據")
        return result
    
@app.post("/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    # 1. 檢查副檔名
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="請上傳 Excel 檔案")

    # 2. 讀取上傳的內容到記憶體
    contents = await file.read()
    
    try:
        # 3. 使用 Pandas 解析記憶體中的 Excel (不需存成實體檔案)
        df = pd.read_excel(io.BytesIO(contents), sheet_name='批次表', skiprows=2)
        
        with Session(engine) as session:
            count = 0
            for _, row in df.iterrows():
                # 排除空行
                if pd.isna(row.get('樣品編號')):
                    continue
                
                # 建立樣品物件
                new_sample = Sample(
                    sample_id=str(row['樣品編號']),
                    weight=row.get('取樣重量(g)'),
                    batch_name=f"Upload_{file.filename}"
                )
                session.add(new_sample)
                count += 1
            
            session.commit()
            return {"message": "導入成功", "filename": file.filename, "imported_count": count}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失敗: {str(e)}")