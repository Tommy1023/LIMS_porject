import pandas as pd
from sqlmodel import Session
from database import engine, Sample, create_db_and_tables

# 1. 設定檔案名稱 (請確認與資料夾中的檔名一致)
FILE_NAME = "=251202電子簽章=重金屬前處理批次表_1.3&測試紀錄表_ICP-MS_1.3_範本"

def import_data_from_excel():
    print(f"正在讀取檔案: {FILE_NAME} ...")
    
    # 2. 使用 Pandas 讀取工作表
    # 根據你的檔案，我們讀取「批次表」工作表
    # skiprows=2 代表跳過前兩行標頭，直接從欄位名稱開始讀取
    try:
        df = pd.read_excel(FILE_NAME, sheet_name='批次表', skiprows=2)
    except Exception as e:
        print(f"❌ 讀取失敗: {e}")
        return

    # 3. 準備寫入資料庫
    with Session(engine) as session:
        count = 0
        for index, row in df.iterrows():
            # 判斷「樣品編號」是否為空，若為空則跳過
            if pd.isna(row.get('樣品編號')):
                continue
            
            # 建立資料物件 (欄位名稱需與 Excel 標題對應)
            # 這裡假設你的 Excel 標題有 '樣品編號', '取樣重量(g)' 等
            new_sample = Sample(
                sample_id=str(row['樣品編號']),
                weight=row.get('取樣重量(g)'), # 若名稱不同請修改此處
                batch_name="Batch_20251223"
            )
            
            session.add(new_sample)
            count += 1
        
        session.commit()
        print(f"✅ 成功導入 {count} 筆樣品數據！")

if __name__ == "__main__":
    import_data_from_excel()