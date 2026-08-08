FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# กำหนดให้ฟังผ่าน 0.0.0.0 เพื่อให้ Container อื่นหรือเบราว์เซอร์เข้าถึงได้
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]