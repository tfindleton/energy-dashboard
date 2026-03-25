from __future__ import annotations

import datetime as dt
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from .common import flatten_scalars, parse_dateish

def chunk_date_ranges(start_date: dt.date, end_date: dt.date, chunk_days: int = 90) -> List[Tuple[dt.date, dt.date]]:
    chunks = []
    cursor = start_date
    while cursor <= end_date:
        chunk_end = min(cursor + dt.timedelta(days=chunk_days - 1), end_date)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + dt.timedelta(days=1)
    return chunks


def json_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    form_data: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
) -> Any:
    request_headers = dict(headers or {})
    payload = None
    if form_data is not None:
        payload = urllib.parse.urlencode(form_data).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    request = urllib.request.Request(url, data=payload, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
            if isinstance(payload, dict):
                message = payload.get("error_description") or payload.get("error") or body
            else:
                message = body
        except json.JSONDecodeError:
            message = body
        raise RuntimeError(f"Tesla API error {error.code}: {message}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Request failed for {url}: {error.reason}") from error
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Non-JSON response from {url}") from error


def unwrap_response(payload: Any) -> Any:
    if isinstance(payload, dict) and "response" in payload:
        return payload["response"]
    return payload


def extract_energy_sites(products_payload: Any) -> List[Dict[str, Any]]:
    payload = unwrap_response(products_payload)
    items = payload if isinstance(payload, list) else []
    sites = []
    for item in items:
        if not isinstance(item, dict):
            continue
        site_id = item.get("energy_site_id")
        resource_type = str(item.get("resource_type", "")).lower()
        if site_id is None and not any(term in resource_type for term in ("solar", "battery", "powerwall", "energy")):
            continue
        site_id = str(site_id if site_id is not None else item.get("id", ""))
        if not site_id:
            continue
        sites.append(
            {
                "site_id": site_id,
                "site_name": item.get("site_name") or item.get("display_name") or f"Site {site_id}",
                "resource_type": item.get("resource_type", ""),
                "raw": item,
            }
        )
    deduped: Dict[str, Dict[str, Any]] = {site["site_id"]: site for site in sites}
    return list(deduped.values())


def extract_timezone(payload: Any, fallback: str) -> str:
    flat = flatten_scalars(unwrap_response(payload))
    for key, value in flat.items():
        if not isinstance(value, str):
            continue
        if ("time_zone" in key or "timezone" in key) and "/" in value:
            return value
    return fallback


def extract_site_name(payload: Any, fallback: str) -> str:
    flat = flatten_scalars(unwrap_response(payload))
    for candidate in ("site_name", "display_name", "name"):
        if candidate in flat and isinstance(flat[candidate], str):
            return flat[candidate]
    return fallback


def extract_installation_date(payload: Any) -> Optional[dt.date]:
    flat = flatten_scalars(unwrap_response(payload))
    for key, value in flat.items():
        if "installation_date" not in key:
            continue
        parsed = parse_dateish(value)
        if parsed is not None:
            return parsed
    return None


def extract_history_rows(payload: Any) -> List[Dict[str, Any]]:
    unwrapped = unwrap_response(payload)
    if isinstance(unwrapped, list):
        return [item for item in unwrapped if isinstance(item, dict)]
    if isinstance(unwrapped, dict):
        for key in ("time_series", "history", "series", "calendar_history", "records"):
            if key in unwrapped and unwrapped.get(key) in (None, "", []):
                return []
            rows = unwrapped.get(key)
            if isinstance(rows, list):
                return [item for item in rows if isinstance(item, dict)]
        for value in unwrapped.values():
            if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                return [item for item in value if isinstance(item, dict)]
        if not unwrapped:
            return []
    raise RuntimeError("Unexpected Tesla history payload shape.")

__all__ = [
    "chunk_date_ranges",
    "extract_energy_sites",
    "extract_history_rows",
    "extract_installation_date",
    "extract_site_name",
    "extract_timezone",
    "json_request",
    "unwrap_response",
]
