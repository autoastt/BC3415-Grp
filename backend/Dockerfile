FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    TIKTOKEN_CACHE_DIR=/opt/tiktoken ANONYMIZED_TELEMETRY=False DATA_DIR=/data
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY backend/tests ./tests
COPY sample_data ./sample_data
COPY backend/docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && useradd -m appuser && mkdir -p /data && chown appuser /data
USER appuser
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
