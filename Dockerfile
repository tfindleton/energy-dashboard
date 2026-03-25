FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    SOLAR_DASHBOARD_DB=/data/dashboard.sqlite3 \
    SOLAR_DASHBOARD_CONFIG=/data/tesla_auth.json \
    SOLAR_DASHBOARD_DOWNLOAD_ROOT=/data/download \
    PORT=8000 \
    SYNC_DAYS_BACK=1825 \
    SYNC_INTERVAL_MINUTES=0 \
    SYNC_DAILY_TIME=01:00

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY dashboard /app/dashboard

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD \
  python3 -c "import json, urllib.request; json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/status', timeout=5))"

CMD ["sh", "-c", "python3 -m dashboard --db ${SOLAR_DASHBOARD_DB:-/data/dashboard.sqlite3} --config ${SOLAR_DASHBOARD_CONFIG:-/data/tesla_auth.json} --download-root ${SOLAR_DASHBOARD_DOWNLOAD_ROOT:-/data/download} serve --host 0.0.0.0 --port ${PORT:-8000} --sync-on-start --days-back ${SYNC_DAYS_BACK:-1825} --daily-sync-time ${SYNC_DAILY_TIME:-01:00} --sync-interval-minutes ${SYNC_INTERVAL_MINUTES:-0}"]
