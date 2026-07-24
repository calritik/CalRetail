# CalRetail — Hugging Face Space image.
#
# Runs both processes of the two-tier app in one container: FastAPI stays
# internal on 127.0.0.1:8000 (services/api.py already points there), Dash is
# the only thing bound to 0.0.0.0 and the port HF's proxy actually routes to.
FROM python:3.11-slim

# libgomp1: xgboost's prebuilt wheel links OpenMP at import time and the slim
# base image doesn't ship it — without this the container boots, then every
# capability that touches xgboost 500s with "libgomp.so.1: cannot open shared
# object file", which is a confusing failure to debug from the Space logs alone.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-space.txt .
RUN pip install --no-cache-dir -r requirements-space.txt

COPY backend/ backend/
COPY frontend_dash/ frontend_dash/
COPY notebooks/ notebooks/
COPY data/processed/ data/processed/
RUN mkdir -p data/models
COPY start.sh .
RUN chmod +x start.sh

ENV PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1 \
    DASH_HOST=0.0.0.0 \
    DASH_PORT=7860

EXPOSE 7860

CMD ["./start.sh"]
