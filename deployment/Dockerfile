FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONUTF8=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 depbridge && useradd --uid 10001 --gid depbridge --create-home depbridge \
    && mkdir /data && chown depbridge:depbridge /data
COPY . /app
# Fail the build if the selected backup UI was accidentally excluded from the context.
RUN test -f /app/demo_frontend/index.html && test -f /app/demo_frontend/static/start.html \
    && python -m pip install '.[verification]'
USER 10001:10001
ENV DEPBRIDGE_DATA_DIR=/data DEPBRIDGE_FRONTEND_DIR=/app/demo_frontend
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/health', timeout=3)"
CMD ["python", "-m", "uvicorn", "depbridge_service.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
