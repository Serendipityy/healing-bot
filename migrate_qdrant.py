from qdrant_client import QdrantClient

from ragbase.config import Config

# Source: local Qdrant (on-disk)
print("Starting...")
source = QdrantClient(path=Config.Path.DATABASE_DIR)  # Đường dẫn tới thư mục bạn đã tạo collection
print("Starting 2...")
# Destination: Docker Qdrant server
dest = QdrantClient(host="localhost", port=6333)
print("Migrating từ local sang Docker...")
# Thực hiện migrate 2 collections: documents và summary
source.migrate(
    dest_client=dest,
    collection_names=["documents","summary"],
    
)

print("✅ Migration thành công từ local sang Docker")