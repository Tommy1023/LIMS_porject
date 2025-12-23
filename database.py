from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session

# 1. 定義資料表模型
class Sample(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sample_id: str = Field(index=True)  
    weight: Optional[float] = None
    dilution_factor: float = 1.0
    result: Optional[float] = None
    batch_name: Optional[str] = None

# 2. 設定資料庫檔案位置
sqlite_file_name = "lims.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# 建立連線引擎
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

# 3. 建立資料表的函式
def create_db_and_tables():
    print("正在建立資料表...")
    SQLModel.metadata.create_all(engine)
    print("✅ 資料表建立完成！")

if __name__ == "__main__":
    create_db_and_tables()
    print(f"✅ 資料庫檔案 {sqlite_file_name} 已產出。")