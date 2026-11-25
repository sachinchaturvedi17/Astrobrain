# AstroNaradMuni v1.4.0 Production Container (Hostinger Managed Apps / VPS Docker)
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000

COPY pyproject.toml README.md run_server.py ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . pymysql

EXPOSE 8000

CMD ["python3", "run_server.py"]
