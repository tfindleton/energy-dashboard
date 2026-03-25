import datetime as dt
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from dashboard import (
    ARCHIVE_IMPORT_SCHEMA_VERSION,
    TeslaSolarDashboard,
    aggregate_daily_history_rows,
    build_comparison_payload,
    build_diagnostics_payload,
    build_insights_payload,
    build_trend_payload,
    build_weekday_pattern_payload,
    clamp_month_day,
    extract_history_rows,
    latest_scheduled_daily_sync_utc,
    normalize_cli_args,
    normalize_history_row,
    resolve_tzinfo,
)
from dashboard.cli import build_parser, migrate_legacy_storage_layout, resolve_runtime_paths
from dashboard.common import DEFAULT_CONFIG_PATH, DEFAULT_DB_PATH, DEFAULT_DOWNLOAD_ROOT
from dashboard.server import is_client_disconnect_error
from dashboard.service import extract_installation_date, extract_site_name, extract_timezone


class FakeTeslaSession:
    def __init__(self, authorized: bool = False) -> None:
        self.authorized = authorized
        self.fetch_token_calls = []

    def __enter__(self) -> "FakeTeslaSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def new_state(self) -> str:
        return "state-123"

    def new_code_verifier(self) -> str:
        return b"verifier-123"

    def authorization_url(self, state: str, code_verifier: str) -> str:
        return f"https://auth.tesla.com/oauth2/v3/authorize?state={state}&code_verifier={code_verifier}"

    def fetch_token(self, authorization_response: str) -> None:
        self.fetch_token_calls.append(authorization_response)
        self.authorized = True


class NormalizationTests(unittest.TestCase):
    def test_normalize_history_row_with_direct_and_path_metrics(self) -> None:
        row = {
            "timestamp": "2025-03-01T00:00:00-08:00",
            "solar_energy_exported": 24000,
            "consumer_energy_imported_from_solar": 18000,
            "consumer_energy_imported_from_grid": 6000,
            "grid_energy_imported": 6000,
            "grid_energy_exported_from_solar": 3000,
        }

        normalized = normalize_history_row(row)

        self.assertEqual(normalized["bucket_date"], "2025-03-01")
        self.assertEqual(normalized["solar_generation_wh"], 24000)
        self.assertEqual(normalized["home_usage_wh"], 24000)
        self.assertEqual(normalized["grid_import_wh"], 6000)
        self.assertEqual(normalized["grid_export_wh"], 3000)

    def test_normalize_history_row_with_nested_payload(self) -> None:
        row = {
            "time": "2025-03-02",
            "solar": {"energy_exported": 9000},
            "consumer": {
                "energy_imported_from_grid": 2000,
                "energy_imported_from_solar": 7000,
            },
            "grid": {
                "energy_imported": 2000,
                "energy_exported_from_solar": 1500,
            },
        }

        normalized = normalize_history_row(row)

        self.assertEqual(normalized["bucket_date"], "2025-03-02")
        self.assertEqual(normalized["solar_generation_wh"], 9000)
        self.assertEqual(normalized["home_usage_wh"], 9000)
        self.assertEqual(normalized["grid_import_wh"], 2000)
        self.assertEqual(normalized["grid_export_wh"], 1500)

    def test_aggregate_daily_history_rows_sums_intervals_by_day(self) -> None:
        rows = [
            {
                "bucket_date": "2025-03-01",
                "solar_generation_wh": 24000,
                "home_usage_wh": 18000,
                "grid_import_wh": 6000,
                "grid_export_wh": 3000,
                "raw_json": "{}",
            },
            {
                "bucket_date": "2025-03-01",
                "solar_generation_wh": 12000,
                "home_usage_wh": 13000,
                "grid_import_wh": 1000,
                "grid_export_wh": 0,
                "raw_json": "{}",
            },
            {
                "bucket_date": "2025-03-02",
                "solar_generation_wh": 9000,
                "home_usage_wh": 9000,
                "grid_import_wh": 0,
                "grid_export_wh": 500,
                "raw_json": "{}",
            },
        ]

        aggregated = aggregate_daily_history_rows(rows, csv_path="/tmp/2025-03.csv")

        self.assertEqual(len(aggregated), 2)
        self.assertEqual(aggregated[0]["bucket_date"], "2025-03-01")
        self.assertEqual(aggregated[0]["solar_generation_wh"], 36000)
        self.assertEqual(aggregated[0]["home_usage_wh"], 31000)
        self.assertEqual(aggregated[0]["grid_import_wh"], 7000)
        self.assertEqual(aggregated[0]["grid_export_wh"], 3000)
        self.assertIn("2025-03.csv", aggregated[0]["raw_json"])


class ComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            {
                "bucket_date": "2024-03-23",
                "solar_generation_wh": 10000,
                "home_usage_wh": 14000,
                "grid_import_wh": 4000,
                "grid_export_wh": 2500,
            },
            {
                "bucket_date": "2025-03-23",
                "solar_generation_wh": 12000,
                "home_usage_wh": 15000,
                "grid_import_wh": 3000,
                "grid_export_wh": 3500,
            },
            {
                "bucket_date": "2025-01-10",
                "solar_generation_wh": 7000,
                "home_usage_wh": 10000,
                "grid_import_wh": 3000,
                "grid_export_wh": 1200,
            },
            {
                "bucket_date": "2025-02-10",
                "solar_generation_wh": 8000,
                "home_usage_wh": 10500,
                "grid_import_wh": 2500,
                "grid_export_wh": 1800,
            },
            {
                "bucket_date": "2026-03-23",
                "solar_generation_wh": 13000,
                "home_usage_wh": 14800,
                "grid_import_wh": 2200,
                "grid_export_wh": 4200,
            },
            {
                "bucket_date": "2026-01-10",
                "solar_generation_wh": 6800,
                "home_usage_wh": 9900,
                "grid_import_wh": 3100,
                "grid_export_wh": 1100,
            },
            {
                "bucket_date": "2026-02-10",
                "solar_generation_wh": 8500,
                "home_usage_wh": 10800,
                "grid_import_wh": 2300,
                "grid_export_wh": 2000,
            },
        ]

    def test_day_comparison_uses_same_calendar_day(self) -> None:
        payload = build_comparison_payload(self.rows, "day", dt.date(2026, 3, 23), 3)

        self.assertEqual(payload["labels"], ["2024", "2025", "2026"])
        self.assertEqual(payload["rows"][0]["solar_generation"], 10.0)
        self.assertEqual(payload["rows"][2]["grid_export"], 4.2)

    def test_ytd_comparison_sums_through_anchor_day(self) -> None:
        payload = build_comparison_payload(self.rows, "ytd", dt.date(2026, 3, 23), 2)

        self.assertEqual(payload["labels"], ["2025", "2026"])
        self.assertEqual(payload["rows"][0]["solar_generation"], 27.0)
        self.assertEqual(payload["rows"][1]["home_usage"], 35.5)

    def test_trend_payload_groups_by_month(self) -> None:
        payload = build_trend_payload(
            self.rows,
            start_date=dt.date(2025, 1, 1),
            end_date=dt.date(2025, 3, 31),
            granularity="month",
            metrics=["solar_generation", "home_usage"],
        )

        self.assertEqual(payload["labels"], ["2025-01", "2025-02", "2025-03"])
        self.assertEqual(payload["series"][0]["values"], [7.0, 8.0, 12.0])
        self.assertEqual(payload["series"][1]["values"], [10.0, 10.5, 15.0])

    def test_trend_payload_groups_by_year(self) -> None:
        payload = build_trend_payload(
            self.rows,
            start_date=dt.date(2025, 1, 1),
            end_date=dt.date(2026, 12, 31),
            granularity="year",
            metrics=["solar_generation", "home_usage"],
        )

        self.assertEqual(payload["labels"], ["2025", "2026"])
        self.assertEqual(payload["series"][0]["values"], [27.0, 28.3])
        self.assertEqual(payload["series"][1]["values"], [35.5, 35.5])

    def test_weekday_pattern_payload_groups_by_weekday(self) -> None:
        payload = build_weekday_pattern_payload(
            self.rows,
            start_date=dt.date(2024, 1, 1),
            end_date=dt.date(2026, 12, 31),
            metrics=["solar_generation", "home_usage"],
            value_mode="average",
        )

        self.assertEqual(payload["labels"], ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        monday_row = next(row for row in payload["rows"] if row["label"] == "Monday")
        self.assertEqual(monday_row["solar_generation"], 10.5)
        self.assertEqual(monday_row["home_usage"], 12.65)


class InsightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            {
                "bucket_date": "2025-03-23",
                "solar_generation_wh": 12000,
                "home_usage_wh": 15000,
                "grid_import_wh": 3000,
                "grid_export_wh": 3500,
            },
            {
                "bucket_date": "2025-07-15",
                "solar_generation_wh": 16000,
                "home_usage_wh": 14000,
                "grid_import_wh": 1200,
                "grid_export_wh": 6000,
            },
            {
                "bucket_date": "2026-01-10",
                "solar_generation_wh": 6800,
                "home_usage_wh": 9900,
                "grid_import_wh": 3100,
                "grid_export_wh": 1100,
            },
            {
                "bucket_date": "2026-03-23",
                "solar_generation_wh": 13000,
                "home_usage_wh": 14800,
                "grid_import_wh": 2200,
                "grid_export_wh": 4200,
            },
            {
                "bucket_date": "2026-08-10",
                "solar_generation_wh": 18000,
                "home_usage_wh": 17000,
                "grid_import_wh": 1500,
                "grid_export_wh": 7200,
            },
        ]

    def test_insights_payload_includes_lifetime_and_current_year_peaks(self) -> None:
        payload = build_insights_payload(self.rows)

        section_titles = [section["title"] for section in payload["sections"]]

        self.assertEqual(payload["data_start"], "2025-03-23")
        self.assertEqual(payload["data_end"], "2026-08-10")
        self.assertIn("Lifetime Solar Peaks", section_titles)
        self.assertIn("Lifetime Load Peaks", section_titles)
        self.assertIn("2026 Solar Peaks", section_titles)
        self.assertIn("2026 Load Peaks", section_titles)

        solar_lifetime = next(section for section in payload["sections"] if section["title"] == "Lifetime Solar Peaks")
        best_day = next(item for item in solar_lifetime["items"] if item["label"] == "Best Day")
        self.assertEqual(best_day["value"], 18.0)
        self.assertEqual(best_day["hint"], "Aug 10, 2026")

        solar_current = next(section for section in payload["sections"] if section["title"] == "2026 Solar Peaks")
        solar_ytd = next(item for item in solar_current["items"] if item["label"] == "Solar YTD")
        self.assertEqual(solar_ytd["value"], 37.8)
        self.assertEqual(solar_ytd["hint"], "Through 2026-08-10")

    def test_insights_payload_computes_action_signals(self) -> None:
        payload = build_insights_payload(self.rows)

        action_section = next(section for section in payload["sections"] if section["title"] == "Action Signals")
        self_power = next(item for item in action_section["items"] if item["label"] == "Self-Powered YTD")
        solar_delta = next(item for item in action_section["items"] if item["label"] == "Solar YTD vs Last Year")

        self.assertEqual(self_power["value"], 83.7)
        self.assertEqual(self_power["tone"], "good")
        self.assertEqual(solar_delta["value"], 35.0)
        self.assertEqual(solar_delta["tone"], "good")


class DiagnosticTests(unittest.TestCase):
    def test_diagnostics_payload_flags_low_solar_and_high_usage(self) -> None:
        rows = [
            {
                "bucket_date": "2024-07-01",
                "solar_generation_wh": 20000,
                "home_usage_wh": 12000,
                "grid_import_wh": 1500,
                "grid_export_wh": 9000,
            },
            {
                "bucket_date": "2024-07-02",
                "solar_generation_wh": 21000,
                "home_usage_wh": 11800,
                "grid_import_wh": 1200,
                "grid_export_wh": 9800,
            },
            {
                "bucket_date": "2025-07-01",
                "solar_generation_wh": 19000,
                "home_usage_wh": 12500,
                "grid_import_wh": 1800,
                "grid_export_wh": 7600,
            },
            {
                "bucket_date": "2025-07-02",
                "solar_generation_wh": 20500,
                "home_usage_wh": 12100,
                "grid_import_wh": 1500,
                "grid_export_wh": 8600,
            },
            {
                "bucket_date": "2026-07-01",
                "solar_generation_wh": 10000,
                "home_usage_wh": 18200,
                "grid_import_wh": 8200,
                "grid_export_wh": 900,
            },
            {
                "bucket_date": "2026-07-02",
                "solar_generation_wh": 9200,
                "home_usage_wh": 19100,
                "grid_import_wh": 9100,
                "grid_export_wh": 700,
            },
        ]

        payload = build_diagnostics_payload(rows)

        self.assertIn("±2 day windows", payload["summary"])
        solar_section = next(section for section in payload["sections"] if section["title"] == "Solar Watch")
        load_section = next(section for section in payload["sections"] if section["title"] == "Load Watch")
        solar_last_30 = next(item for item in solar_section["items"] if item["label"] == "Last 30 Days vs Prior Years")
        load_last_30 = next(item for item in load_section["items"] if item["label"] == "Last 30 Days vs Prior Years")

        self.assertEqual(solar_last_30["tone"], "bad")
        self.assertLess(solar_last_30["value"], 0)
        self.assertEqual(load_last_30["tone"], "bad")
        self.assertGreater(load_last_30["value"], 0)
        self.assertGreaterEqual(len(payload["alerts"]), 2)
        self.assertEqual(payload["tables"][0]["title"], "Potential Low Solar Days")
        self.assertEqual(payload["tables"][0]["rows"][0]["date"], "2026-07-02")
        self.assertIn("2024:", payload["tables"][0]["rows"][0]["history_summary"])
        self.assertEqual(payload["tables"][0]["rows"][0]["inspect_metric"], "solar_power")
        self.assertEqual(payload["tables"][1]["title"], "Potential High Usage Days")
        self.assertEqual(payload["tables"][1]["rows"][0]["date"], "2026-07-02")
        self.assertIn("2025:", payload["tables"][1]["rows"][0]["history_summary"])
        self.assertEqual(payload["tables"][1]["rows"][0]["inspect_metric"], "load_power")

    def test_diagnostics_payload_excludes_today_when_today_is_partial(self) -> None:
        class FakeDate(dt.date):
            @classmethod
            def today(cls) -> "FakeDate":
                return cls(2026, 7, 2)

        rows = [
            {
                "bucket_date": "2024-07-01",
                "solar_generation_wh": 20000,
                "home_usage_wh": 12000,
                "grid_import_wh": 1500,
                "grid_export_wh": 9000,
            },
            {
                "bucket_date": "2025-07-01",
                "solar_generation_wh": 19000,
                "home_usage_wh": 12500,
                "grid_import_wh": 1800,
                "grid_export_wh": 7600,
            },
            {
                "bucket_date": "2026-07-01",
                "solar_generation_wh": 10000,
                "home_usage_wh": 18200,
                "grid_import_wh": 8200,
                "grid_export_wh": 900,
            },
            {
                "bucket_date": "2026-07-02",
                "solar_generation_wh": 2000,
                "home_usage_wh": 22000,
                "grid_import_wh": 12000,
                "grid_export_wh": 0,
            },
        ]

        with mock.patch("dashboard.payloads.dt.date", FakeDate):
            payload = build_diagnostics_payload(rows)

        self.assertIn("through 2026-07-01", payload["summary"])
        low_solar_dates = [row["date"] for row in payload["tables"][0]["rows"]]
        high_usage_dates = [row["date"] for row in payload["tables"][1]["rows"]]
        self.assertNotIn("2026-07-02", low_solar_dates)
        self.assertNotIn("2026-07-02", high_usage_dates)

    def test_diagnostics_payload_suppresses_isolated_high_usage_spike(self) -> None:
        rows = [
            {
                "bucket_date": "2024-07-01",
                "solar_generation_wh": 18000,
                "home_usage_wh": 12000,
                "grid_import_wh": 1800,
                "grid_export_wh": 7000,
            },
            {
                "bucket_date": "2025-07-01",
                "solar_generation_wh": 18200,
                "home_usage_wh": 11800,
                "grid_import_wh": 1600,
                "grid_export_wh": 7200,
            },
            {
                "bucket_date": "2026-07-01",
                "solar_generation_wh": 17900,
                "home_usage_wh": 26000,
                "grid_import_wh": 9800,
                "grid_export_wh": 1100,
            },
        ]

        payload = build_diagnostics_payload(rows)

        load_section = next(section for section in payload["sections"] if section["title"] == "Load Watch")
        persistent_runs = next(item for item in load_section["items"] if item["label"] == "Persistent High Usage Runs")
        self.assertEqual(persistent_runs["value"], 0)
        self.assertEqual(payload["tables"][1]["rows"], [])


class DateHelperTests(unittest.TestCase):
    def test_clamp_month_day_handles_non_leap_year(self) -> None:
        self.assertEqual(clamp_month_day(2023, 2, 29), dt.date(2023, 2, 28))

    def test_resolve_tzinfo_falls_back_when_zoneinfo_key_is_missing(self) -> None:
        with mock.patch("dashboard.common.ZoneInfo", side_effect=Exception("missing")):
            tzinfo = resolve_tzinfo("America/Los_Angeles")
        self.assertIsNotNone(tzinfo)

    def test_service_extract_helpers_handle_nested_site_payloads(self) -> None:
        payload = {
            "response": {
                "site_name": "My Home",
                "installation_time_zone": "America/Los_Angeles",
                "installation_date": "2021-08-25T11:22:33-07:00",
            }
        }

        self.assertEqual(extract_site_name(payload, "Fallback"), "My Home")
        self.assertEqual(extract_timezone(payload, "UTC"), "America/Los_Angeles")
        self.assertEqual(extract_installation_date(payload), dt.date(2021, 8, 25))

    def test_latest_scheduled_daily_sync_utc_uses_last_due_slot(self) -> None:
        now = dt.datetime(2026, 3, 23, 20, 30, tzinfo=dt.timezone.utc)
        scheduled = latest_scheduled_daily_sync_utc("01:00", now=now)

        self.assertEqual(
            scheduled,
            dt.datetime(2026, 3, 23, 8, 0, tzinfo=dt.timezone.utc),
        )

    def test_extract_history_rows_tolerates_empty_time_series(self) -> None:
        self.assertEqual(extract_history_rows({"response": {"time_series": None}}), [])


class CliTests(unittest.TestCase):
    def test_no_args_defaults_to_serve(self) -> None:
        self.assertEqual(normalize_cli_args([]), ["serve"])

    def test_global_options_before_implicit_serve_are_preserved(self) -> None:
        self.assertEqual(
            normalize_cli_args(
                [
                    "--db",
                    "custom.sqlite3",
                    "--port",
                    "9000",
                    "--no-sync-on-start",
                ]
            ),
            [
                "--db",
                "custom.sqlite3",
                "serve",
                "--port",
                "9000",
                "--no-sync-on-start",
            ],
        )

    def test_explicit_command_is_untouched(self) -> None:
        self.assertEqual(
            normalize_cli_args(["sync", "--days-back", "30"]),
            ["sync", "--days-back", "30"],
        )

    def test_default_runtime_paths_use_shared_data_directory(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            parser = build_parser()
            args = parser.parse_args(["serve"])

        db_path, config_path, download_root = resolve_runtime_paths(args)

        self.assertEqual(db_path, DEFAULT_DB_PATH)
        self.assertEqual(config_path, DEFAULT_CONFIG_PATH)
        self.assertEqual(download_root, DEFAULT_DOWNLOAD_ROOT)

    def test_config_and_download_root_follow_custom_db_directory(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            parser = build_parser()
            args = parser.parse_args(["--db", os.path.join("custom", "store.sqlite3"), "serve"])

        db_path, config_path, download_root = resolve_runtime_paths(args)

        self.assertEqual(db_path, os.path.join("custom", "store.sqlite3"))
        self.assertEqual(config_path, os.path.join("custom", "tesla_auth.json"))
        self.assertEqual(download_root, os.path.join("custom", "download"))

    def test_legacy_default_storage_is_migrated_into_data_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            previous_cwd = os.getcwd()
            os.chdir(tempdir)
            try:
                Path("tesla_solar.sqlite3").write_text("db")
                Path("tesla_auth.json").write_text("auth")
                Path("download").mkdir()
                Path("download/marker.txt").write_text("archive")

                messages = migrate_legacy_storage_layout(DEFAULT_DB_PATH, DEFAULT_CONFIG_PATH, DEFAULT_DOWNLOAD_ROOT)

                self.assertEqual(len(messages), 3)
                self.assertTrue(Path(DEFAULT_DB_PATH).exists())
                self.assertTrue(Path(DEFAULT_CONFIG_PATH).exists())
                self.assertTrue(Path(DEFAULT_DOWNLOAD_ROOT, "marker.txt").exists())
                self.assertFalse(Path("tesla_solar.sqlite3").exists())
                self.assertFalse(Path("tesla_auth.json").exists())
                self.assertFalse(Path("download").exists())
            finally:
                os.chdir(previous_cwd)

    def test_legacy_root_storage_moves_next_to_custom_db(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            previous_cwd = os.getcwd()
            os.chdir(tempdir)
            try:
                Path("tesla_solar.sqlite3").write_text("db")
                Path("tesla_auth.json").write_text("auth")
                Path("download").mkdir()
                Path("download/marker.txt").write_text("archive")

                db_path = os.path.join("custom", "store.sqlite3")
                config_path = os.path.join("custom", "tesla_auth.json")
                download_root = os.path.join("custom", "download")

                messages = migrate_legacy_storage_layout(db_path, config_path, download_root)

                self.assertEqual(len(messages), 3)
                self.assertTrue(Path(db_path).exists())
                self.assertTrue(Path(config_path).exists())
                self.assertTrue(Path(download_root, "marker.txt").exists())
                self.assertFalse(Path("tesla_solar.sqlite3").exists())
                self.assertFalse(Path("tesla_auth.json").exists())
                self.assertFalse(Path("download").exists())
            finally:
                os.chdir(previous_cwd)


class ServerTests(unittest.TestCase):
    def test_client_disconnect_errors_are_detected(self) -> None:
        self.assertTrue(is_client_disconnect_error(BrokenPipeError()))
        self.assertTrue(is_client_disconnect_error(ConnectionAbortedError()))
        self.assertTrue(is_client_disconnect_error(ConnectionResetError()))
        self.assertFalse(is_client_disconnect_error(RuntimeError("boom")))


class CsvArchiveTests(unittest.TestCase):
    def test_existing_download_archive_is_imported_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            app = TeslaSolarDashboard(
                db_path=f"{tempdir}/test.sqlite3",
                config_path=f"{tempdir}/tesla_auth.json",
                download_root=f"{tempdir}/archive",
            )

            csv_path = app._write_energy_csv(
                site_id="12345",
                month_date=dt.date(2025, 3, 1),
                time_series=[
                    {
                        "timestamp": "2025-03-01T01:00:00-08:00",
                        "solar_energy_exported": 24000,
                        "consumer_energy_imported_from_solar": 18000,
                        "consumer_energy_imported_from_grid": 6000,
                        "grid_energy_imported": 6000,
                        "grid_energy_exported_from_solar": 3000,
                    },
                    {
                        "timestamp": "2025-03-01T01:30:00-08:00",
                        "solar_energy_exported": 12000,
                        "consumer_energy_imported_from_solar": 11000,
                        "consumer_energy_imported_from_grid": 1000,
                        "grid_energy_imported": 1000,
                        "grid_energy_exported_from_solar": 500,
                    }
                ],
            )

            sites = app.list_sites()
            rows = app.query_site_rows("12345")

            self.assertTrue(csv_path.endswith(".csv"))
            self.assertEqual(len(sites), 1)
            self.assertEqual(sites[0]["site_id"], "12345")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["bucket_date"], "2025-03-01")
            self.assertEqual(rows[0]["solar_generation_wh"], 36000)
            self.assertEqual(rows[0]["home_usage_wh"], 36000)
            self.assertEqual(rows[0]["grid_import_wh"], 7000)
            self.assertEqual(rows[0]["grid_export_wh"], 3500)

    def test_archive_schema_version_forces_reimport_of_existing_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            app = TeslaSolarDashboard(
                db_path=f"{tempdir}/test.sqlite3",
                config_path=f"{tempdir}/tesla_auth.json",
                download_root=f"{tempdir}/archive",
            )

            app._write_energy_csv(
                site_id="12345",
                month_date=dt.date(2025, 3, 1),
                time_series=[
                    {
                        "timestamp": "2025-03-01T01:00:00-08:00",
                        "solar_energy_exported": 12000,
                        "consumer_energy_imported_from_solar": 9000,
                        "consumer_energy_imported_from_grid": 3000,
                        "grid_energy_imported": 3000,
                        "grid_energy_exported_from_solar": 1000,
                    }
                ],
            )

            app.list_sites()
            app.upsert_daily_rows(
                "12345",
                [
                    {
                        "bucket_date": "2025-03-01",
                        "solar_generation_wh": 0,
                        "home_usage_wh": 0,
                        "grid_import_wh": 0,
                        "grid_export_wh": 0,
                        "raw_json": "{}",
                    }
                ],
            )
            app.set_sync_state("archive_import_version", "1")

            app.list_sites()
            rows = app.query_site_rows("12345")

            self.assertEqual(app.get_sync_state("archive_import_version"), ARCHIVE_IMPORT_SCHEMA_VERSION)
            self.assertEqual(rows[0]["solar_generation_wh"], 12000)
            self.assertEqual(rows[0]["home_usage_wh"], 12000)
            self.assertEqual(rows[0]["grid_import_wh"], 3000)
            self.assertEqual(rows[0]["grid_export_wh"], 1000)


class PowerArchiveTests(unittest.TestCase):
    def test_day_compare_payload_reads_power_csvs_and_reports_missing_days(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            app = TeslaSolarDashboard(
                db_path=f"{tempdir}/test.sqlite3",
                config_path=f"{tempdir}/tesla_auth.json",
                download_root=f"{tempdir}/archive",
            )
            app.upsert_site_metadata("12345", "Home", "America/Los_Angeles", "{}")

            app._write_power_csv(
                site_id="12345",
                day_date=dt.date(2025, 3, 1),
                time_series=[
                    {
                        "timestamp": "2025-03-01T00:00:00-08:00",
                        "solar_power": 400,
                        "battery_power": 0,
                        "grid_power": 800,
                    },
                    {
                        "timestamp": "2025-03-01T00:05:00-08:00",
                        "solar_power": 600,
                        "battery_power": 0,
                        "grid_power": 1200,
                    },
                ],
            )
            app._write_power_csv(
                site_id="12345",
                day_date=dt.date(2025, 3, 2),
                time_series=[
                    {
                        "timestamp": "2025-03-02T00:00:00-08:00",
                        "load_power": 1800,
                        "solar_power": 500,
                    },
                    {
                        "timestamp": "2025-03-02T00:05:00-08:00",
                        "load_power": 900,
                        "solar_power": 300,
                    },
                ],
            )

            payload = app.day_compare_payload(
                "12345",
                ["2025-03-01", "2025-03-02", "2025-03-03"],
                "load_power",
            )

            self.assertEqual(payload["metric"], "load_power")
            self.assertEqual(payload["unit"], "kW")
            self.assertEqual(payload["labels"], ["00:00", "00:05"])
            self.assertEqual(len(payload["series"]), 2)
            self.assertEqual(payload["series"][0]["values"], [1.2, 1.8])
            self.assertEqual(payload["series"][1]["values"], [1.8, 0.9])
            self.assertEqual(payload["rows"][0]["date"], "2025-03-01")
            self.assertEqual(payload["rows"][0]["label"], "Mar 01, 2025")
            self.assertEqual(payload["rows"][0]["total_kwh"], 0.25)
            self.assertEqual(payload["rows"][0]["estimated_total_kwh"], 0.25)
            self.assertEqual(payload["rows"][0]["total_source"], "estimated")
            self.assertEqual(payload["rows"][0]["peak_kw"], 1.8)
            self.assertEqual(payload["rows"][0]["peak_time"], "00:05")
            self.assertAlmostEqual(payload["rows"][1]["total_kwh"], 0.22, places=2)
            self.assertEqual(payload["rows"][1]["total_source"], "estimated")
            self.assertEqual(payload["rows"][1]["peak_kw"], 1.8)
            self.assertEqual(payload["rows"][1]["peak_time"], "00:00")
            self.assertEqual(payload["missing_dates"], ["2025-03-03"])

    def test_day_compare_payload_prefers_daily_energy_totals_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            app = TeslaSolarDashboard(
                db_path=f"{tempdir}/test.sqlite3",
                config_path=f"{tempdir}/tesla_auth.json",
                download_root=f"{tempdir}/archive",
            )
            app.upsert_site_metadata("12345", "Home", "America/Los_Angeles", "{}")
            app.upsert_daily_rows(
                "12345",
                [
                    {
                        "bucket_date": "2025-03-01",
                        "solar_generation_wh": 25000,
                        "home_usage_wh": 41000,
                        "grid_import_wh": 5000,
                        "grid_export_wh": 12000,
                        "raw_json": "{}",
                    }
                ],
            )

            app._write_power_csv(
                site_id="12345",
                day_date=dt.date(2025, 3, 1),
                time_series=[
                    {
                        "timestamp": "2025-03-01T12:00:00-08:00",
                        "solar_power": 3000,
                        "load_power": 4200,
                        "grid_power": -800,
                    },
                    {
                        "timestamp": "2025-03-01T12:05:00-08:00",
                        "solar_power": 3200,
                        "load_power": 4300,
                        "grid_power": -900,
                    },
                ],
            )

            payload = app.day_compare_payload("12345", ["2025-03-01"], "solar_power")

            self.assertEqual(payload["rows"][0]["total_kwh"], 25.0)
            self.assertEqual(payload["rows"][0]["estimated_total_kwh"], 0.52)
            self.assertEqual(payload["rows"][0]["total_source"], "energy")
            self.assertEqual(payload["rows"][0]["peak_kw"], 3.2)
            self.assertEqual(payload["rows"][0]["peak_time"], "12:05")

    def test_day_compare_payload_derives_grid_export_and_import_from_grid_power(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            app = TeslaSolarDashboard(
                db_path=f"{tempdir}/test.sqlite3",
                config_path=f"{tempdir}/tesla_auth.json",
                download_root=f"{tempdir}/archive",
            )
            app.upsert_site_metadata("12345", "Home", "America/Los_Angeles", "{}")

            app._write_power_csv(
                site_id="12345",
                day_date=dt.date(2025, 3, 1),
                time_series=[
                    {"timestamp": "2025-03-01T12:00:00-08:00", "grid_power": -2500},
                    {"timestamp": "2025-03-01T12:05:00-08:00", "grid_power": 900},
                ],
            )

            export_payload = app.day_compare_payload("12345", ["2025-03-01"], "grid_export_power")
            import_payload = app.day_compare_payload("12345", ["2025-03-01"], "grid_import_power")

            self.assertEqual(export_payload["series"][0]["values"], [2.5, 0.0])
            self.assertEqual(import_payload["series"][0]["values"], [0.0, 0.9])


class AuthFlowTests(unittest.TestCase):
    def test_save_user_config_clears_cached_session_when_email_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            app = TeslaSolarDashboard(
                db_path=f"{tempdir}/test.sqlite3",
                config_path=f"{tempdir}/tesla_auth.json",
                download_root=f"{tempdir}/archive",
            )

            app.save_config(
                {
                    "email": "first@example.com",
                    "teslapy_cache": {"refresh_token": "token"},
                    "pending_auth": {"state": "old"},
                }
            )
            app.save_user_config({"email": "second@example.com", "energy_site_id": "999"})

            config = app.load_config()

            self.assertEqual(config["email"], "second@example.com")
            self.assertEqual(config["energy_site_id"], "999")
            self.assertNotIn("teslapy_cache", config)
            self.assertNotIn("pending_auth", config)

    def test_start_web_login_saves_pending_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            app = TeslaSolarDashboard(
                db_path=f"{tempdir}/test.sqlite3",
                config_path=f"{tempdir}/tesla_auth.json",
                download_root=f"{tempdir}/archive",
            )
            fake_session = FakeTeslaSession(authorized=False)

            with mock.patch.object(app, "_tesla_session", return_value=fake_session):
                payload = app.start_web_login({"email": "user@example.com", "energy_site_id": "123"})

            config = app.load_config()

            self.assertIn("authorization_url", payload)
            self.assertFalse(payload["already_authorized"])
            self.assertEqual(config["email"], "user@example.com")
            self.assertEqual(config["energy_site_id"], "123")
            self.assertEqual(config["pending_auth"]["state"], "state-123")
            self.assertEqual(config["pending_auth"]["code_verifier"], "verifier-123")
            self.assertIn("authorization_url", config["pending_auth"])

    def test_finish_web_login_clears_pending_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            app = TeslaSolarDashboard(
                db_path=f"{tempdir}/test.sqlite3",
                config_path=f"{tempdir}/tesla_auth.json",
                download_root=f"{tempdir}/archive",
            )
            app.save_config(
                {
                    "email": "user@example.com",
                    "pending_auth": {
                        "email": "user@example.com",
                        "state": "state-123",
                        "code_verifier": "verifier-123",
                    },
                }
            )
            fake_session = FakeTeslaSession(authorized=False)

            with mock.patch.object(app, "_tesla_session", return_value=fake_session):
                payload = app.finish_web_login("https://auth.tesla.com/void/callback?code=abc")

            self.assertTrue(payload["authorized"])
            self.assertEqual(
                fake_session.fetch_token_calls,
                ["https://auth.tesla.com/void/callback?code=abc"],
            )
            self.assertNotIn("pending_auth", app.load_config())

    def test_status_payload_messages_reflect_install_and_sign_in_states(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            app = TeslaSolarDashboard(
                db_path=f"{tempdir}/test.sqlite3",
                config_path=f"{tempdir}/tesla_auth.json",
                download_root=f"{tempdir}/archive",
            )

            with mock.patch.object(app, "teslapy_available", return_value=False):
                self.assertIn("pip install -r requirements.txt", app.status_payload()["message"])

            app.save_user_config({"email": "user@example.com"})
            with mock.patch.object(app, "teslapy_available", return_value=True), mock.patch.object(
                app, "auth_configured", return_value=False
            ):
                self.assertIn("Start Sign In", app.status_payload()["message"])

            app.save_config(
                {
                    "email": "user@example.com",
                    "pending_auth": {
                        "email": "user@example.com",
                        "state": "state-123",
                        "code_verifier": "verifier-123",
                    },
                }
            )
            with mock.patch.object(app, "teslapy_available", return_value=True), mock.patch.object(
                app, "auth_configured", return_value=False
            ):
                self.assertIn("Paste the final Tesla URL", app.status_payload()["message"])

    def test_status_payload_marks_missed_daily_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            app = TeslaSolarDashboard(
                db_path=f"{tempdir}/test.sqlite3",
                config_path=f"{tempdir}/tesla_auth.json",
                download_root=f"{tempdir}/archive",
            )
            app.auto_sync_enabled = True
            app.auto_sync_interval_minutes = 0
            app.auto_sync_daily_time = "01:00"
            app.set_sync_state("last_sync", "2026-03-22T00:30:00Z")

            with mock.patch("dashboard.service.utc_now", return_value=dt.datetime(2026, 3, 23, 20, 30, tzinfo=dt.timezone.utc)):
                payload = app.status_payload()

            self.assertTrue(payload["auto_sync_missed"])
            self.assertEqual(payload["auto_sync_missed_since"], "2026-03-23T08:00:00Z")


if __name__ == "__main__":
    unittest.main()
