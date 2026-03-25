# Energy Dashboard

Energy Dashboard is a self-hosted web app for Tesla home energy and Powerwall data. Docker is the recommended setup path, and a local Python workflow is also available if you prefer to run it directly on your host.

It uses the same local-browser Tesla sign-in pattern as `netzero-labs/tesla-solar-download`:

- no Tesla Fleet API app
- no public callback URL
- user signs in on Tesla's own page
- the final Tesla URL is pasted back into the app once
- the Tesla session is cached locally for future syncs

This project is standalone. It does not shell out to `tesla-solar-download`, and it keeps its runtime files in a single predictable data folder. Legacy root-level installs are migrated into that layout automatically on startup.

## Features

- Flat local web UI for Tesla energy history
- Compare same day, ISO week, month, and year-to-date across years
- Trend, diagnostics, insight, and day-compare views
- Manual sync plus scheduled background sync
- CSV-first archive model with SQLite cache
- Container-friendly persistent storage under a single data mount

## Docker Quick Start

Build the image:

```bash
docker build -t energy-dashboard .
```

Run it with a persistent data volume:

```bash
docker run -d \
  --name energy-dashboard \
  --restart unless-stopped \
  -p 8000:8000 \
  -v energy-dashboard-data:/data \
  energy-dashboard
```

Open:

```text
http://127.0.0.1:8000/
```

The container keeps all runtime state under `/data`:

- `/data/dashboard.sqlite3`
- `/data/tesla_auth.json`
- `/data/download`

That auth JSON contains your Tesla session cache. Keep the mounted volume private and out of source control. The default ignore rules in this repo already exclude the local auth file, database, and download archive.

## Docker Configuration

Container defaults:

- port `8000`
- auto sync cron `0 1 * * *` (daily at 1:00 AM local server time)
- full-history syncs reuse the local archive and only download missing Tesla files
- DB path `/data/dashboard.sqlite3`
- auth config `/data/tesla_auth.json`
- archive root `/data/download`

Other common environment variables:

- `TESLA_EMAIL`
- `TESLA_ENERGY_SITE_ID`
- `TESLA_TIME_ZONE`
- `PORT`
- `SYNC_CRON`
- `DEBUG_HTTP`

Example with overrides:

```bash
docker run -d \
  --name energy-dashboard \
  --restart unless-stopped \
  -p 8080:8000 \
  -e TESLA_EMAIL=you@example.com \
  -e TESLA_ENERGY_SITE_ID=1234567890 \
  -e SYNC_CRON="30 3 * * *" \
  -e DEBUG_HTTP=1 \
  -v "$PWD/data:/data" \
  energy-dashboard
```

The image also works with Podman. If your host uses SELinux, add a relabel suffix such as `:Z` to the `/data` mount.

## Sign In

The app uses a guided TeslaPy local browser flow:

1. Enter your Tesla account email in the page.
2. Click `Start Sign In`.
3. Sign in on Tesla's page.
4. Tesla will end on a `Page Not Found` screen at `auth.tesla.com`. That is expected.
5. Copy the full URL from that final Tesla page.
6. Paste it into the app and click `Finish Sign In`.
7. Click `Sync Now`.

After that, the cached Tesla session is reused for scheduled and manual syncs until it expires or you sign out.

## Data Storage

The app keeps raw CSV files as the durable archive and SQLite as the fast query cache for charts.

Files are stored like this:

```text
data/download/<site_id>/energy/YYYY-MM.csv
data/download/<site_id>/energy/YYYY-MM.partial.csv
data/download/<site_id>/power/YYYY-MM-DD.csv
data/download/<site_id>/power/YYYY-MM-DD.partial.csv
```

Behavior:

- finalized monthly energy files are downloaded once and then reused
- the current month is refreshed as `.partial.csv`
- recent intraday power files are cached by day
- the current day is refreshed as `.partial.csv`
- SQLite is upserted from the local CSV archive after each sync
- legacy root-level `download/` archives are migrated and imported automatically

## Local Python

Local Python is still supported for development or direct host runs, but it is secondary to the container workflow.

Install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Run the dashboard from the repo root:

```bash
python3 -m dashboard
```

By default, local runs keep runtime state under `data/`:

- `data/dashboard.sqlite3`
- `data/tesla_auth.json`
- `data/download`

If you install the package, use the current console command `tesla-energy-dashboard`.

That defaults to `serve` on `0.0.0.0:8000`, starts the web UI immediately, and runs scheduled syncs with the same defaults used by the container. Syncs always walk the full archive window, but finalized CSVs are reused so only missing Tesla files are fetched. The server does not open a browser unless you explicitly pass `--open-browser`, so container runs stay headless by default. Per-request HTTP logs are also off by default; pass `--debug-http` locally or set `DEBUG_HTTP=1` in the container when you want to see every request while troubleshooting.

On Windows, you can also run `start-local.bat`. It creates `.venv` with `uv`, installs requirements, and starts the dashboard on `http://127.0.0.1:8000/` without opening a browser automatically.

Useful local commands:

```bash
python3 -m dashboard auth-start --email you@example.com
python3 -m dashboard auth-finish --url "https://auth.tesla.com/void/callback?code=..."
python3 -m dashboard sync
python3 -m dashboard serve --sync-cron off
python3 -m dashboard serve --sync-cron "0 6 * * 1-5"
python3 -m dashboard serve --debug-http
```
