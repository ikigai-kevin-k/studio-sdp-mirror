# 使用Python 3.12作為基礎映像
FROM python:3.12-slim

# 設置工作目錄
WORKDIR /app

# 複製requirements.txt
COPY requirements.txt .

# 安裝系統依賴（opencv需要）
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 安裝Python依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案文件
COPY ./side_record.py .

# 設置容器啟動時執行的命令
CMD ["python", "side_record.py"]