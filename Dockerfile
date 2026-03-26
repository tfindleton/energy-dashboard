FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    DEBUG_HTTP=0 \
    PORT=8000

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY dashboard /app/dashboard
RUN mkdir -p /data && ln -sfn /data /app/data

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD \
  python3 -c "import json, urllib.request; json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/status', timeout=5))"

CMD ["sh", "-c", "set -- python3 -m dashboard serve --host 0.0.0.0 --port \"${PORT:-8000}\" --sync-on-start; case \"${DEBUG_HTTP:-0}\" in 1|true|TRUE|yes|YES) set -- \"$@\" --debug-http ;; esac; exec \"$@\""]
