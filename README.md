<p align="center">
  <img src="dashboard/static/logo.svg" alt="Energy Dashboard" width="96" height="96">
</p>

<h1 align="center">Energy Dashboard</h1>

<p align="center">
  Self-hosted Tesla energy and Powerwall analytics
</p>

---

Energy Dashboard is a self-hosted web app for Tesla home energy and Powerwall data. Docker is the recommended setup path, and a local Python workflow is also available if you prefer to run it directly on your host.

It supports a one-time native Tesla sign-in through the Tesla Auth helper:

- no Tesla Fleet API app
- no public callback URL
- user signs in on Tesla's own page
- the native helper captures `tesla://auth/callback` and provides an access/refresh token pair
- the dashboard validates that pair once and caches the Tesla session locally

This project is standalone. It does not shell out to `tesla-solar-download`, and it keeps its runtime files in a single predictable data folder. Legacy root-level installs are migrated into that layout automatically on startup.

## Features

- Flat local web UI for Tesla energy history
- Compare same day, ISO week, month, and year-to-date across years
- Trend, diagnostics, insight, and day-compare views
- Manual sync plus scheduled background sync with 15-minute cooldown
- CSV-first archive model with SQLite cache
- Container-friendly persistent storage under a single data mount
- Live status badges for sign-in, sync, and next scheduled sync

## Docker Quick Start

Pull the published image from GitHub Container Registry:

```bash
docker pull ghcr.io/tfindleton/energy-dashboard:latest
```

Run it with a persistent data volume:

```bash
docker run -d \
  --name energy-dashboard \
  --restart unless-stopped \
  -p 8000:8000 \
  -v energy-dashboard-data:/data \
  ghcr.io/tfindleton/energy-dashboard:latest
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

The sign-in page accepts Tesla access and refresh tokens, so keep the dashboard on localhost or behind trusted HTTPS authentication. Do not expose the setup UI directly to the public internet.

## Docker Configuration

Container defaults:

- port `8000`
- auto sync cron `0 1 * * *` (daily at 1:00 AM local server time)
- 15-minute minimum interval between syncs to stay within Tesla API rate limits
- full-history syncs reuse the local archive and only download missing Tesla files
- DB path `/data/dashboard.sqlite3`
- auth config `/data/tesla_auth.json`
- archive root `/data/download`

Container environment should stay minimal:

- `PORT`
- `DEBUG_HTTP`
- optional `TESLA_TIME_ZONE`

Tesla account email, pinned site selection, and sync schedule are managed inside the web UI and persisted under `/data`. You do not need to pass them into the container.

Example with a custom host port, debug HTTP logging, and an optional Tesla timezone fallback:

```bash
docker run -d \
  --name energy-dashboard \
  --restart unless-stopped \
  -p 8080:8000 \
  -e DEBUG_HTTP=1 \
  -e TESLA_TIME_ZONE=America/Los_Angeles \
  -v "$PWD/data:/data" \
  ghcr.io/tfindleton/energy-dashboard:latest
```

Use `TESLA_TIME_ZONE` only when the machine running the container is in a different timezone than the Tesla site and you want the first sync windows aligned before Tesla site metadata is cached. Once the app has saved the Tesla site timezone from Tesla itself or from the web UI, you usually do not need this override.

The image also works with Podman. If your host uses SELinux, add a relabel suffix such as `:Z` to the `/data` mount.

## Sign In

The recommended setup uses the native [Tesla Auth helper](https://github.com/adriankumpf/tesla_auth/releases/latest), which embeds Tesla's login page and captures the app callback without browser developer tools:

1. Enter your Tesla account email in the dashboard.
2. Download the helper for your operating system from its GitHub release page. On Windows it uses Microsoft Edge WebView2.
3. Run `tesla_auth --clear-browsing-data`, then complete Tesla login and MFA in its native window.
4. Copy both the **access token** and **refresh token** from the same result window.
5. Paste both into the dashboard and click `Import Token Pair`.
6. Click `Sync Now`.

Tesla currently requires the original code-exchange access token to bootstrap the first Owner API request. Exchanging only a refresh token before that first request produces `403 Forbidden`, even though the token refresh itself succeeds. The dashboard therefore validates the fresh pair with `GET /api/1/products`, then saves it in the same private local auth file used by the existing flow. Neither token is returned in an API response. After the initial bootstrap, normal refresh-token rotation is automatic.

The dashboard intentionally does not include a desktop-browser fallback. Tesla's custom app callback and verification page make that path unreliable in ordinary browsers, while Tesla Auth captures the same callback directly in its native window.

After that, the cached Tesla session is reused for scheduled and manual syncs until it expires or you sign out.

If your Tesla site timezone differs from the machine running the app, you can also set the Tesla timezone in the app, for example `America/Los_Angeles`. That setting is a fallback for archive window alignment when Tesla site metadata is missing or not cached yet. It does not change when the cron schedule runs; cron still uses the server or container local time.

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

## Versioning

The app version is defined once in `dashboard/__init__.py`:

```python
__version__ = "0.1.7"
```

`pyproject.toml` reads the version dynamically from that attribute, so `pip install` and CI/CD tagging both use the same source. The version is displayed in the web UI header and returned by the `/api/status` endpoint.

## Local Python

Local Python is still supported for development or direct host runs, but it is secondary to the container workflow.

Install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install --upgrade -r requirements.txt
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
python3 -m dashboard sync
python3 -m dashboard serve --sync-cron off
python3 -m dashboard serve --sync-cron "0 6 * * 1-5"
python3 -m dashboard serve --debug-http
```
