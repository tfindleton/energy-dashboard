from __future__ import annotations

import json
import datetime as dt
import sys
import threading
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

from .common import (
    DEFAULT_HISTORY_DAYS,
    DEFAULT_DAILY_SYNC_TIME,
    guess_content_type,
    INDEX_TEMPLATE_PATH,
    parse_daily_sync_time,
    read_text_file,
    resolve_static_path,
    utc_now,
    describe_daily_sync_time,
)
from .service import TeslaSolarDashboard

class BackgroundSyncWorker:
    def __init__(
        self,
        app: TeslaSolarDashboard,
        interval_minutes: int,
        daily_sync_time: str,
        days_back: int,
        site_id: Optional[str] = None,
    ) -> None:
        self.app = app
        self.interval_minutes = max(interval_minutes, 0)
        self.daily_sync_time = daily_sync_time
        self.daily_sync_parts = parse_daily_sync_time(daily_sync_time)
        self.days_back = days_back
        self.site_id = site_id
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name="tesla-solar-sync", daemon=True)

    def start(self) -> None:
        self.app.auto_sync_enabled = True
        self.app.auto_sync_interval_minutes = self.interval_minutes
        self.app.auto_sync_daily_time = self.daily_sync_time
        self.app.auto_sync_description = (
            f"Every {self.interval_minutes} min"
            if self.interval_minutes > 0
            else describe_daily_sync_time(self.daily_sync_time)
        )
        self.app.auto_sync_site_id = self.site_id
        self._set_next_run()
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def join(self, timeout: Optional[float] = None) -> None:
        self.thread.join(timeout=timeout)

    def _next_run(self) -> dt.datetime:
        if self.interval_minutes > 0:
            return utc_now() + dt.timedelta(minutes=self.interval_minutes)
        if self.daily_sync_parts is None:
            raise RuntimeError("Auto sync is disabled.")
        hour, minute = self.daily_sync_parts
        local_now = dt.datetime.now().astimezone()
        next_local = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_local <= local_now:
            next_local += dt.timedelta(days=1)
        return next_local.astimezone(dt.timezone.utc)

    def _set_next_run(self) -> dt.datetime:
        next_run = self._next_run()
        self.app.auto_sync_next_run = next_run.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        return next_run

    def _run(self) -> None:
        while True:
            next_run = self._set_next_run()
            wait_seconds = max((next_run - utc_now()).total_seconds(), 1.0)
            if self.stop_event.wait(wait_seconds):
                break
            if not self.app.auth_configured():
                continue
            try:
                result = self.app.sync(days_back=self.days_back, requested_site_id=self.site_id)
                print(json.dumps({"background_sync": True, **result}), flush=True)
            except Exception as error:
                print(f"[background-sync] {error}", file=sys.stderr, flush=True)
            finally:
                self._set_next_run()


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
            if parsed.path == "/api/sync":
                payload = self.read_json_body()
                result = self.app.sync(
                    days_back=int(payload.get("days_back") or DEFAULT_HISTORY_DAYS),
                    requested_site_id=payload.get("site_id") or None,
                )
                self.respond_json(result)
                return
            self.respond_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as error:  # pragma: no cover - exercised manually
            self.respond_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)

    def respond_html(self, content: str) -> None:
        encoded = content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def respond_file(self, path: str) -> None:
        with open(path, "rb") as handle:
            payload = handle.read()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", guess_content_type(path))
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def respond_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

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

    def log_message(self, fmt: str, *args: Any) -> None:  # pragma: no cover
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))


def first_query_value(query: Dict[str, List[str]], key: str) -> str:
    values = query.get(key, [])
    return values[0] if values else ""


def run_server(
    app: TeslaSolarDashboard,
    host: str,
    port: int,
    open_browser: bool,
    sync_on_start: bool = False,
    sync_interval_minutes: int = 0,
    daily_sync_time: str = DEFAULT_DAILY_SYNC_TIME,
    days_back: int = DEFAULT_HISTORY_DAYS,
    site_id: Optional[str] = None,
) -> None:
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    server.dashboard_app = app  # type: ignore[attr-defined]
    worker = None
    if sync_interval_minutes > 0 or parse_daily_sync_time(daily_sync_time) is not None:
        worker = BackgroundSyncWorker(
            app=app,
            interval_minutes=sync_interval_minutes,
            daily_sync_time=daily_sync_time,
            days_back=days_back,
            site_id=site_id,
        )
        worker.start()
    url = f"http://{host}:{port}/"
    print(f"Serving Energy Dashboard at {url}")
    if worker:
        print(f"Background sync scheduled: {app.auto_sync_description}.", flush=True)
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
                    result = app.sync(days_back=days_back, requested_site_id=site_id)
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
        if worker:
            worker.stop()
            worker.join(timeout=5)
