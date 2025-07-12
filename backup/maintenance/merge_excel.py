import pandas as pd
import glob
import os

# Thư mục chứa các file Excel (đặt '.' nếu cùng thư mục với script)
folder_path = './data/ragas_score/advanced_rag'

# Tìm tất cả file Excel có tên bắt đầu bằng "comparison_batch_"
excel_files = glob.glob(os.path.join(folder_path, "batch_*.xlsx"))

# Danh sách chứa các DataFrame
df_list = []

# Đọc từng file và thêm vào danh sách
for file in excel_files:
    try:
        df = pd.read_excel(file)
        df_list.append(df)
    except Exception as e:
        print(f"❌ Không đọc được file {file}: {e}")

# Gộp tất cả DataFrame lại
merged_df = pd.concat(df_list, ignore_index=True)

# Ghi ra file Excel mới
output_file = 'merged_comparison_advanced.xlsx'
merged_df.to_excel(output_file, index=False)

print(f"✅ Đã merge {len(df_list)} file vào '{output_file}'")
