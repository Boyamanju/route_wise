FROM python:3.12-slim

WORKDIR /app

COPY smart-delivery-route-logistics-optimization-engine-3/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY smart-delivery-route-logistics-optimization-engine-3/app ./app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 10000

# Render provides PORT at runtime. The fallback also makes the image usable locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
