import pandas as pd
import os

# Thư mục chứa các file Excel
folder_path = r'd:\KLTN_HealingBot\Code\chatbot_v1\healing-bot\data\evaluate'

# Tạo danh sách các file Excel cần merge và sắp xếp theo thứ tự
excel_files = sorted(
    [f for f in os.listdir(folder_path) if f.startswith('ragas_score_chunk') and f.endswith('.xlsx')],
    key=lambda x: int(x.split('_')[-1].split('.')[0])  # Lấy số thứ tự từ tên file
)

# Tạo một DataFrame trống để chứa dữ liệu merge
merged_data = pd.DataFrame()

# Lặp qua từng file và append dữ liệu vào DataFrame
for file in excel_files:
    file_path = os.path.join(folder_path, file)
    data = pd.read_excel(file_path)
    merged_data = pd.concat([merged_data, data], ignore_index=True)

# Lưu file Excel đã merge
output_file = os.path.join(folder_path, 'merged_ragas_output.xlsx')
merged_data.to_excel(output_file, index=False)

print(f'Merged file saved to {output_file}')