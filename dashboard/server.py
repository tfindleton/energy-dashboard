from __future__ import annotations

import datetime as dt
import json
import sys
import threading
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

from .common import (
    guess_content_type,
    INDEX_TEMPLATE_PATH,
    read_text_file,
    resolve_static_path,
    utc_now,
)
from .scheduler import DEFAULT_SYNC_CRON, describe_sync_schedule, next_scheduled_sync_utc, normalize_sync_cron, parse_sync_cron
from .service import TeslaSolarDashboard

CLIENT_DISCONNECT_ERRORS = (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)


def is_client_disconnect_error(error: BaseException) -> bool:
    return isinstance(error, CLIENT_DISCONNECT_ERRORS)


def http_request_logging_enabled(server: Any) -> bool:
    return bool(getattr(server, "log_http_requests", False))


class BackgroundSyncWorker:
    def __init__(
        self,
        app: TeslaSolarDashboard,
        sync_cron: str,
        site_id: Optional[str] = None,
    ) -> None:
        self.app = app
        self.default_sync_cron = normalize_sync_cron(sync_cron)
        self.site_id = site_id
        self.stop_event = threading.Event()
        self.refresh_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name="tesla-solar-sync", daemon=True)

    def start(self) -> None:
        self._apply_schedule_state(self.app.effective_sync_cron(self.default_sync_cron))
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.refresh_event.set()

    def refresh_schedule(self) -> None:
        self.refresh_event.set()

    def join(self, timeout: Optional[float] = None) -> None:
        self.thread.join(timeout=timeout)

    def _apply_schedule_state(self, sync_cron: str, next_run: Optional[dt.datetime] = None) -> None:
        enabled = parse_sync_cron(sync_cron) is not None
        self.app.auto_sync_enabled = enabled
        self.app.auto_sync_description = describe_sync_schedule(sync_cron)
        self.app.auto_sync_next_run = (
            next_run.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            if next_run is not None
            else None
        )
        self.app.auto_sync_site_id = self.site_id

    def _run(self) -> None:
        while not self.stop_event.is_set():
            sync_cron = self.app.effective_sync_cron(self.default_sync_cron)
            schedule = parse_sync_cron(sync_cron)
            if schedule is None:
                self._apply_schedule_state(sync_cron, next_run=None)
                self.refresh_event.wait()
                self.refresh_event.clear()
                continue

            next_run = next_scheduled_sync_utc(sync_cron)
            if next_run is None:
                self._apply_schedule_state(sync_cron, next_run=None)
                self.refresh_event.wait()
                self.refresh_event.clear()
                continue
            self._apply_schedule_state(sync_cron, next_run=next_run)
            wait_seconds = max((next_run - utc_now()).total_seconds(), 1.0)
            if self.refresh_event.wait(wait_seconds):
                self.refresh_event.clear()
                continue
            if self.stop_event.is_set():
                break
            if not self.app.auth_configured():
                continue
            try:
                result = self.app.sync(requested_site_id=self.site_id)
                print(json.dumps({"background_sync": True, **result}), flush=True)
            except Exception as error:
                print(f"[background-sync] {error}", file=sys.stderr, flush=True)


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "TeslaSolarDashboard/0.1"

    @property
    def app(self) -> TeslaSolarDashboard:
        return self.server.dashboard_app  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        try:
            if parsed.path == "/":
                self.respond_html(read_text_file(INDEX_TEMPLATE_PATH))
                return
            if parsed.path.startswith("/static/"):
                static_path = resolve_static_path(parsed.path[len("/static/"):])
                self.respond_file(static_path)
                return
            if parsed.path == "/api/status":
                self.respond_json(self.app.status_payload())
                return
            if parsed.path == "/api/comparison":
                query = urllib.parse.parse_qs(parsed.query)
                site_id = first_query_value(query, "site_id")
                mode = first_query_value(query, "mode") or "month"
                anchor = first_query_value(query, "anchor") or dt.date.today().isoformat()
                years = int(first_query_value(query, "years") or "6")
                self.respond_json(self.app.comparison_payload(site_id, mode, anchor, years))
                return
            if parsed.path == "/api/insights":
                query = urllib.parse.parse_qs(parsed.query)
                site_id = first_query_value(query, "site_id")
                self.respond_json(self.app.insights_payload(site_id))
                return
            if parsed.path == "/api/diagnostics":
                query = urllib.parse.parse_qs(parsed.query)
                site_id = first_query_value(query, "site_id")
                self.respond_json(self.app.diagnostics_payload(site_id))
                return
            if parsed.path == "/api/trend":
                query = urllib.parse.parse_qs(parsed.query)
                site_id = first_query_value(query, "site_id")
                start = first_query_value(query, "start")
                end = first_query_value(query, "end")
                granularity = first_query_value(query, "granularity") or "day"
                metrics = [item for item in (first_query_value(query, "metrics") or "").split(",") if item]
                self.respond_json(self.app.trend_payload(site_id, start, end, granularity, metrics))
                return
            if parsed.path == "/api/pattern":
                query = urllib.parse.parse_qs(parsed.query)
                site_id = first_query_value(query, "site_id")
                start = first_query_value(query, "start")
                end = first_query_value(query, "end")
                metrics = [item for item in (first_query_value(query, "metrics") or "").split(",") if item]
                value_mode = first_query_value(query, "value_mode") or "average"
                self.respond_json(self.app.weekday_pattern_payload(site_id, start, end, metrics, value_mode))
                return
            if parsed.path == "/api/day-compare":
                query = urllib.parse.parse_qs(parsed.query)
                site_id = first_query_value(query, "site_id")
                dates = [item for item in (first_query_value(query, "dates") or "").split(",") if item]
                metric = first_query_value(query, "metric") or "load_power"
                self.respond_json(self.app.day_compare_payload(site_id, dates, metric))
                return
            self.respond_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        except FileNotFoundError:
            self.respond_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as error:  # pragma: no cover - exercised manually
            self.respond_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        try:
            if parsed.path == "/api/auth/start":
                payload = self.read_json_body()
                self.respond_json(self.app.start_web_login(payload))
                return
            if parsed.path == "/api/auth/finish":
                payload = self.read_json_body()
                self.respond_json(self.app.finish_web_login(str(payload.get("authorization_response", "") or "").strip()))
                return
            if parsed.path == "/api/auth/logout":
                self.respond_json(self.app.logout())
                return
            if parsed.path == "/api/settings":
                payload = self.read_json_body()
                self.respond_json(self.app.save_sync_settings(payload))
                return
            if parsed.path == "/api/sync":
                payload = self.read_json_body()
                result = self.app.sync(requested_site_id=payload.get("site_id") or None)
                self.respond_json(result)
                return
            self.respond_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as error:  # pragma: no cover - exercised manually
            self.respond_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)

    def _write_response(self, payload: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except CLIENT_DISCONNECT_ERRORS:
            return

    def respond_html(self, content: str) -> None:
        self._write_response(content.encode("utf-8"), "text/html; charset=utf-8")

    def respond_file(self, path: str) -> None:
        with open(path, "rb") as handle:
            payload = handle.read()
        self._write_response(payload, guess_content_type(path))

    def respond_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._write_response(json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8", status)

    def read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError as error:
            raise RuntimeError("Invalid JSON body.") from error
        if not isinstance(payload, dict):
            raise RuntimeError("JSON body must be an object.")
        return payload

    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover
        if not http_request_logging_enabled(self.server):
            return
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))


def first_query_value(query: Dict[str, List[str]], key: str) -> str:
    values = query.get(key, [])
    return values[0] if values else ""


def run_server(
    app: TeslaSolarDashboard,
    host: str,
    port: int,
    open_browser: bool,
    debug_http: bool = False,
    sync_on_start: bool = False,
    sync_cron: str = DEFAULT_SYNC_CRON,
    site_id: Optional[str] = None,
) -> None:
    app.sync_cron_default = normalize_sync_cron(sync_cron)
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    server.dashboard_app = app  # type: ignore[attr-defined]
    server.log_http_requests = debug_http  # type: ignore[attr-defined]

    worker = BackgroundSyncWorker(app=app, sync_cron=app.sync_cron_default, site_id=site_id)
    app.sync_schedule_refresh = worker.refresh_schedule
    worker.start()

    url = f"http://{host}:{port}/"
    print(f"Serving Energy Dashboard at {url}")
    if debug_http:
        print("HTTP request logging enabled (debug mode).", flush=True)
    if app.auto_sync_enabled:
        print(f"Background sync scheduled: {app.auto_sync_description}.", flush=True)
    else:
        print("Background sync disabled.", flush=True)
    if open_browser:
        try:
            import webbrowser

            webbrowser.open(url)
        except Exception:
            pass
    if sync_on_start:
        def initial_sync_target() -> None:
            try:
                time.sleep(0.5)
                if app.auth_configured():
                    print("Initial sync starting in background.", flush=True)
                    print("Initial sync task: checking local archive, downloading missing Tesla data, and importing into SQLite.", flush=True)
                    result = app.sync(requested_site_id=site_id)
                    print("Initial sync completed successfully.", flush=True)
                    print(json.dumps(result, indent=2), flush=True)
                elif app.auth_login_ready():
                    print("Initial sync skipped: sign in with Tesla first.", file=sys.stderr, flush=True)
                else:
                    print(
                        "Initial sync skipped: enter your Tesla account email and complete sign-in.",
                        file=sys.stderr,
                        flush=True,
                    )
            except Exception as error:
                print(f"Initial sync failed: {error}", file=sys.stderr, flush=True)

        threading.Thread(
            target=initial_sync_target,
            name="tesla-solar-initial-sync",
            daemon=True,
        ).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
        app.sync_schedule_refresh = None
        worker.stop()
        worker.join(timeout=5)
