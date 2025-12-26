from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, create_engine, Session
from decimal import Decimal, ROUND_HALF_EVEN

# --- 工具函數：實驗室修約 (四捨六入五成雙) ---
def lab_round(value: float, places: int) -> Optional[float]:
    if value is None: return None
    d = Decimal(str(value))
    # 建立格式，例如 places=2 -> '1.00'
    fmt = Decimal(f"1.{'0' * places}")
    return float(d.quantize(fmt, rounding=ROUND_HALF_EVEN))

# --- 1. 測試方法與元素 ---
class Method(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    method_code: str = Field(index=True, unique=True) # 如: M103C
    method_name: str
    default_weight: float = 0.5
    weight_unit: str = "g"
    is_amount: Optional[float] = None    # 內標添加量
    default_volume: float = 50.0

class MethodAnalyte(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    method_id: int = Field(foreign_key="method.id")
    analyte_name: str # Pb, Cd
    loq: float
    decimal_places: int

# --- 2. 消化條件 ---
class DigestionCondition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    temp_celsius: float
    duration_min: int
    reagents: str 

# --- 3. 批次表 ---
class PrepBatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    batch_no: str = Field(index=True, unique=True) # YYYYMMDD-Code-Seq
    method_id: int = Field(foreign_key="method.id")
    digestion_id: int = Field(foreign_key="digestioncondition.id")
    operator: str
    prep_date: str

    # 關聯屬性 (方便查詢)
    method: Optional[Method] = Relationship()
    digestion: Optional[DigestionCondition] = Relationship()
    records: List["TestRecord"] = Relationship(back_populates="batch")

# --- 4. 測試紀錄 (樣品) ---
class TestRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    batch_id: int = Field(foreign_key="prepbatch.id")
    job_no: str = Field(index=True)      # 條碼掃描目標
    sample_name: str
    weight: Optional[float] = None       # 輸入重量
    raw_read: Optional[float] = None     # 儀器讀值
    final_result: Optional[float] = None # 計算結果
    status: str = "Pending"              # Pending, Scanned, Saved

    batch: Optional[PrepBatch] = Relationship(back_populates="records")

# --- 資料庫連線設定 ---
sqlite_file_name = "lims.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)