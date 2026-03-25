# Energy Dashboard

Self-hosted Python dashboard for Tesla home energy / Powerwall history.

It uses the same local-browser Tesla sign-in pattern as `netzero-labs/tesla-solar-download`:

- no Tesla Fleet API app
- no public callback URL
- user signs in on Tesla's own page
- the final Tesla URL is pasted back into the app once
- the Tesla session is cached locally for future syncs

This project is standalone. It does not shell out to `tesla-solar-download` to fetch data. It uses
TeslaPy directly inside this app, but it can also reuse an existing `tesla-solar-download` archive by
pointing `--download-root` at that folder.

The app keeps two local data stores:

- monthly Tesla energy CSV files as the durable backup/archive
- SQLite as the fast query cache for charts

Each sync reuses existing finalized CSV files, refreshes only the current partial month, and then imports those CSVs into SQLite.

## Features

- Flat dark local web UI
- Compare same day across years
- Compare same ISO week across years
- Compare same month across years
- Compare year-to-date across years
- Custom day / week / month trend charts
- Manual sync plus scheduled background sync
- CSV-first archive model with SQLite cache
- Container-friendly persistent storage

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Optional package install:

```bash
pip install .
tesla-energy-dashboard
```

## Run

Start the local dashboard:

```bash
python3 app.py
```

That defaults to:

- `serve`
- `0.0.0.0:8000`
- if already signed in, the web UI starts first and the initial sync runs in the background
- daily auto-sync at `1:00 AM` local server time

Open:

```text
http://127.0.0.1:8000/
```

The Python code is now split into a small package under `dashboard/`, with `app.py` kept as the thin entrypoint for local runs and `pip install .`.

## Sign In

The app uses a guided TeslaPy local browser flow, similar to `tesla-solar-download`.

1. Enter your Tesla account email in the page.
2. Click `Start Sign In`.
3. Sign in on Tesla's page.
4. Tesla will end on a `Page Not Found` screen at `auth.tesla.com`. That is expected.
5. Copy the full URL from that final Tesla page.
6. Paste it into the app and click `Finish Sign In`.
7. Click `Sync Data`.

After that, the cached Tesla session is reused for scheduled/manual syncs until it expires or you sign out.

## Sync Model

The dashboard currently archives Tesla monthly energy history because that is the source needed for the existing comparison and trend charts.

Files are stored like this:

```text
download/<site_id>/energy/YYYY-MM.csv
download/<site_id>/energy/YYYY-MM.partial.csv
```

Behavior:

- finalized months are downloaded once and then reused
- the current month is always refreshed as `.partial.csv`
- SQLite is upserted from those CSV files after each sync
- the raw CSV archive remains available as a backup
- existing archives already under `download/` are imported automatically

Default local file locations:

- SQLite: `./tesla_solar.sqlite3`
- Auth/session cache: `./tesla_auth.json`
- CSV archive: `./download`

## CLI

Print a Tesla sign-in URL:

```bash
python3 app.py auth-start --email you@example.com
```

Open that URL automatically:

```bash
python3 app.py auth-start --email you@example.com --open-browser
```

Finish sign-in from the final Tesla URL:

```bash
python3 app.py auth-finish --url "https://auth.tesla.com/void/callback?code=..."
```

Run a one-off sync:

```bash
python3 app.py sync --days-back 1825
```

Use a custom CSV archive directory:

```bash
python3 app.py --download-root ./download serve
```

Serve with a different sync cadence:

```bash
python3 app.py serve --sync-interval-minutes 30
python3 app.py serve --daily-sync-time off --sync-interval-minutes 0
```

To reuse CSVs that another `tesla-solar-download` run is already producing:

```bash
python3 app.py --download-root "/path/to/existing/download" serve
```

## Environment Variables

- `TESLA_EMAIL`
- `TESLA_ENERGY_SITE_ID`
- `TESLA_TIME_ZONE`
- `PORT`
- `SYNC_DAYS_BACK`
- `SYNC_INTERVAL_MINUTES`
- `SYNC_DAILY_TIME`
- `SOLAR_DASHBOARD_DB`
- `SOLAR_DASHBOARD_CONFIG`
- `SOLAR_DASHBOARD_DOWNLOAD_ROOT`

## Containers

The included image definition works with both Docker and Podman.

Build with Docker:

```bash
docker build -t tesla-energy-dashboard .
```

Build with Podman:

```bash
podman build -t tesla-energy-dashboard .
```

Run with Docker:

```bash
docker run -d \
  --name tesla-energy-dashboard \
  -p 8000:8000 \
  -v tesla-solar-data:/data \
  tesla-energy-dashboard
```

Run with Podman:

```bash
podman run -d \
  --name tesla-energy-dashboard \
  -p 8000:8000 \
  -v tesla-solar-data:/data \
  tesla-energy-dashboard
```

The container persists:

- `/data/tesla_solar.sqlite3`
- `/data/tesla_auth.json`
- `/data/download`

Container defaults:

- port `8000`
- daily sync at `1:00 AM`
- `1825` day initial/backfill window

If your host uses SELinux, you may need to add a relabel suffix such as `:Z` to the `/data` mount when using Podman.

## Testing

```bash
python3 -m py_compile app.py dashboard/*.py tests/test_dashboard.py
python3 -m unittest -q
```

## Notes

- This app now depends on `teslapy`.
- The sign-in/session model is local and homelab-friendly, but it is based on TeslaPy and the same general approach used by `tesla-solar-download`, not Tesla Fleet API onboarding.
- Tokens and cached auth should stay out of version control.

## Attribution

This project builds on the work of other Tesla community projects and should not be presented as inventing those pieces from scratch.

- [`TeslaPy`](https://github.com/tdorssers/TeslaPy) by `tdorssers` is the Python Tesla API library this app uses directly for local sign-in/session handling and Tesla data access.
- [`tesla-solar-download`](https://github.com/netzero-labs/tesla-solar-download) by `netzero-labs` was a major reference for the local-browser sign-in flow, CSV archive approach, and the homelab-friendly Tesla energy download pattern used here.
