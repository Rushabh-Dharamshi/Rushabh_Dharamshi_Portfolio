FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    ANONYMIZED_TELEMETRY=False \
    IS_PERSISTENT=TRUE \
    PERSIST_DIRECTORY=/data \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=5

WORKDIR /chroma

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt

RUN mkdir -p /data

EXPOSE 8000

CMD ["chroma", "run", "--host", "0.0.0.0", "--port", "8000", "--path", "/data"]
