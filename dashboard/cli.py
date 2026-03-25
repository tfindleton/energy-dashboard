from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from typing import List, Optional, Sequence, Tuple

from .common import (
    DEFAULT_DB_PATH,
    DEFAULT_SERVE_HOST,
    default_config_path_for_db_path,
    default_download_root_for_db_path,
)
from .scheduler import DEFAULT_SYNC_CRON, normalize_sync_cron
from .server import run_server
from .service import TeslaSolarDashboard

LEGACY_DB_FILENAME = "tesla_solar.sqlite3"
LEGACY_CONFIG_PATH = "tesla_auth.json"
LEGACY_DOWNLOAD_ROOT = "download"


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
    global_options_with_values = {"--db"}

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
    db_default = os.environ.get("SOLAR_DASHBOARD_DB", DEFAULT_DB_PATH)
    sync_cron_default = os.environ.get("SYNC_CRON", DEFAULT_SYNC_CRON)

    parser = argparse.ArgumentParser(
        description="Sync Tesla energy history locally and serve a comparison dashboard."
    )
    parser.add_argument(
        "--db",
        default=db_default,
        help=(
            f"SQLite database path (default: {db_default}; "
            "auth config, sync schedule, and downloads stay alongside the DB)"
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    auth_start = subparsers.add_parser("auth-start", help="Print a Tesla sign-in URL using TeslaPy.")
    auth_start.add_argument("--email", required=True, help="Tesla account email address.")
    auth_start.add_argument("--open-browser", action="store_true", help="Open the Tesla sign-in URL in your browser.")

    auth_finish = subparsers.add_parser("auth-finish", help="Finish TeslaPy sign-in from the final Tesla URL.")
    auth_finish.add_argument("--url", required=True, help="Full URL from Tesla's final Page Not Found screen.")

    sync = subparsers.add_parser("sync", help="Download and import the full Tesla archive into SQLite.")
    sync.add_argument("--site-id", help="Optional energy site id override.")

    serve = subparsers.add_parser("serve", help="Start the local dashboard web server.")
    serve.add_argument("--host", default=DEFAULT_SERVE_HOST, help="Bind host.")
    serve.add_argument("--port", type=int, default=8000, help="Bind port.")
    serve.add_argument("--open-browser", action="store_true", help="Open the local page when the server starts.")
    serve.add_argument("--debug-http", action="store_true", help="Print every HTTP request for troubleshooting.")
    serve.add_argument("--sync-on-start", dest="sync_on_start", action="store_true", help="Run a full sync before serving.")
    serve.add_argument(
        "--no-sync-on-start",
        dest="sync_on_start",
        action="store_false",
        help="Skip the initial sync and rely on scheduled or manual sync.",
    )
    serve.add_argument("--site-id", help="Optional energy site id override for scheduled or startup syncs.")
    serve.add_argument(
        "--sync-cron",
        default=sync_cron_default,
        help="Cron schedule in local server time, for example '0 1 * * *'. Use 'off' to disable.",
    )
    serve.set_defaults(sync_on_start=True)

    return parser


def resolve_runtime_paths(args: argparse.Namespace) -> Tuple[str, str, str]:
    db_path = args.db
    config_path = default_config_path_for_db_path(db_path)
    download_root = default_download_root_for_db_path(db_path)
    return db_path, config_path, download_root


def _move_path_if_missing(source_path: str, target_path: str) -> Optional[str]:
    if not source_path or os.path.normpath(source_path) == os.path.normpath(target_path):
        return None
    if not os.path.exists(source_path) or os.path.exists(target_path):
        return None
    target_parent = os.path.dirname(target_path)
    if target_parent:
        os.makedirs(target_parent, exist_ok=True)
    shutil.move(source_path, target_path)
    return f"Migrated {source_path} -> {target_path}"


def _migration_candidates(target_path: str, legacy_name: str) -> List[str]:
    target_dir = os.path.dirname(os.path.normpath(target_path))
    candidates = []
    if target_dir:
        candidates.append(os.path.join(target_dir, legacy_name))
    candidates.append(legacy_name)
    return list(dict.fromkeys(candidates))


def migrate_legacy_storage_layout(db_path: str, config_path: str, download_root: str) -> List[str]:
    messages: List[str] = []

    for candidate in _migration_candidates(db_path, LEGACY_DB_FILENAME):
        moved = _move_path_if_missing(candidate, db_path)
        if moved:
            messages.append(moved)
            break

    for candidate in _migration_candidates(config_path, LEGACY_CONFIG_PATH):
        moved = _move_path_if_missing(candidate, config_path)
        if moved:
            messages.append(moved)
            break

    for candidate in _migration_candidates(download_root, LEGACY_DOWNLOAD_ROOT):
        moved = _move_path_if_missing(candidate, download_root)
        if moved:
            messages.append(moved)
            break

    return messages


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(normalize_cli_args(raw_args))
    command = args.command
    db_path, config_path, download_root = resolve_runtime_paths(args)

    for message in migrate_legacy_storage_layout(db_path, config_path, download_root):
        print(message)

    app = TeslaSolarDashboard(db_path=db_path, config_path=config_path, download_root=download_root)

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
        result = app.sync(requested_site_id=args.site_id)
        print(json.dumps(result, indent=2))
        return 0

    if command == "serve":
        app.sync_cron_default = normalize_sync_cron(args.sync_cron)
        run_server(
            app,
            host=args.host,
            port=args.port,
            open_browser=args.open_browser,
            debug_http=args.debug_http,
            sync_on_start=args.sync_on_start,
            sync_cron=app.sync_cron_default,
            site_id=args.site_id,
        )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
