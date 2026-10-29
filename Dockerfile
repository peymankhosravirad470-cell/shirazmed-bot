FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 🆕 ممیزی (بخش J): کپی داده‌ی استاتیک خارج از دیسک mount‌شده /app/data —
# اگر دیسک پایدار خالی باشد، app/data_seed.py فایل‌های غایب را در startup برمی‌گرداند.
COPY data /app/data_seed

COPY . .

CMD ["python", "main.py"]