from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from typing import List, Optional, Sequence

from .common import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_DB_PATH,
    DEFAULT_DAILY_SYNC_TIME,
    DEFAULT_DOWNLOAD_ROOT,
    DEFAULT_HISTORY_DAYS,
    DEFAULT_SERVE_HOST,
    DEFAULT_SYNC_INTERVAL_MINUTES,
)
from .server import run_server
from .service import TeslaSolarDashboard

def normalize_cli_args(argv: Sequence[str]) -> List[str]:
    args = list(argv)
    if not args:
        return ["serve"]
    if any(flag in args for flag in ("-h", "--help")):
        return args
    commands = {"auth-start", "auth-finish", "sync", "serve"}
    if any(arg in commands for arg in args):
        return args

    normalized: List[str] = []
    index = 0
    global_options_with_values = {"--db", "--config", "--download-root"}

    while index < len(args):
        token = args[index]
        if token in global_options_with_values:
            normalized.append(token)
            index += 1
            if index < len(args):
                normalized.append(args[index])
                index += 1
            continue
        if any(token.startswith(f"{option}=") for option in global_options_with_values):
            normalized.append(token)
            index += 1
            continue
        break

    return normalized + ["serve"] + args[index:]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync Tesla energy history locally and serve a comparison dashboard."
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help=f"SQLite database path (default: {DEFAULT_DB_PATH})")
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help=f"Auth config JSON path (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--download-root",
        default=os.environ.get("SOLAR_DASHBOARD_DOWNLOAD_ROOT", DEFAULT_DOWNLOAD_ROOT),
        help=f"Directory for archived Tesla CSV files (default: {DEFAULT_DOWNLOAD_ROOT})",
    )
    subparsers = parser.add_subparsers(dest="command")

    auth_start = subparsers.add_parser("auth-start", help="Print a Tesla sign-in URL using TeslaPy.")
    auth_start.add_argument("--email", required=True, help="Tesla account email address.")
    auth_start.add_argument("--open-browser", action="store_true", help="Open the Tesla sign-in URL in your browser.")

    auth_finish = subparsers.add_parser("auth-finish", help="Finish TeslaPy sign-in from the final Tesla URL.")
    auth_finish.add_argument("--url", required=True, help="Full URL from Tesla's final Page Not Found screen.")

    sync = subparsers.add_parser("sync", help="Download daily energy history into SQLite.")
    sync.add_argument("--days-back", type=int, default=DEFAULT_HISTORY_DAYS, help="How much history to fetch.")
    sync.add_argument("--site-id", help="Optional energy site id override.")

    serve = subparsers.add_parser("serve", help="Start the local dashboard web server.")
    serve.add_argument("--host", default=DEFAULT_SERVE_HOST, help="Bind host.")
    serve.add_argument("--port", type=int, default=8000, help="Bind port.")
    serve.add_argument("--open-browser", action="store_true", help="Open the local page when the server starts.")
    serve.add_argument("--sync-on-start", dest="sync_on_start", action="store_true", help="Run a sync before serving.")
    serve.add_argument(
        "--no-sync-on-start",
        dest="sync_on_start",
        action="store_false",
        help="Skip the initial sync and rely on scheduled or manual sync.",
    )
    serve.add_argument("--days-back", type=int, default=DEFAULT_HISTORY_DAYS, help="History window if syncing on start.")
    serve.add_argument("--site-id", help="Optional energy site id override for sync-on-start.")
    serve.add_argument(
        "--daily-sync-time",
        default=os.environ.get("SYNC_DAILY_TIME", DEFAULT_DAILY_SYNC_TIME),
        help="Daily auto-sync time in local server time (HH:MM). Use 'off' to disable.",
    )
    serve.add_argument(
        "--sync-interval-minutes",
        type=int,
        default=DEFAULT_SYNC_INTERVAL_MINUTES,
        help="Optional fixed background sync interval. Set above 0 to override the daily schedule.",
    )
    serve.set_defaults(sync_on_start=True)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(normalize_cli_args(raw_args))
    command = args.command
    app = TeslaSolarDashboard(db_path=args.db, config_path=args.config, download_root=args.download_root)

    if command == "auth-start":
        payload = app.start_web_login({"email": args.email})
        url = payload.get("authorization_url", "")
        print(url)
        if args.open_browser:
            import webbrowser

            webbrowser.open(url)
        return 0

    if command == "auth-finish":
        payload = app.finish_web_login(args.url)
        print(json.dumps(payload, indent=2))
        return 0

    if command == "sync":
        result = app.sync(days_back=args.days_back, requested_site_id=args.site_id)
        print(json.dumps(result, indent=2))
        return 0

    if command == "serve":
        run_server(
            app,
            host=args.host,
            port=args.port,
            open_browser=args.open_browser,
            sync_on_start=args.sync_on_start,
            sync_interval_minutes=max(args.sync_interval_minutes, 0),
            daily_sync_time=args.daily_sync_time,
            days_back=args.days_back,
            site_id=args.site_id,
        )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
