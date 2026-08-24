from __future__ import annotations

import base64
import binascii
import datetime as dt
import json
import os
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional

from .common import DEFAULT_TESLAPY_TIMEOUT, import_teslapy
from .scheduler import DEFAULT_SYNC_CRON, describe_sync_schedule, normalize_sync_cron
from .service_base import DashboardServiceBase


MAX_TOKEN_LENGTH = 32_768
TESLA_SSO_BASE_URL = "https://auth.tesla.com/"


def _normalize_named_token(value: Any, key: str, label: str) -> str:
    payload = value if isinstance(value, dict) else None
    raw = "" if payload is not None else str(value or "").strip()
    if payload is None and raw.startswith("{"):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise RuntimeError("The pasted token JSON is invalid.") from error
    if payload is not None:
        if not isinstance(payload, dict):
            raise RuntimeError("The pasted token JSON must be an object.")
        raw = str(payload.get(key, "") or "").strip()

    if not raw:
        raise RuntimeError(f"Paste the {label} from the native Tesla Auth helper.")
    if len(raw) > MAX_TOKEN_LENGTH:
        raise RuntimeError(f"The pasted {label} is unexpectedly large.")
    if any(character.isspace() for character in raw):
        raise RuntimeError(f"Paste only the {label}, without its label or extra text.")
    return raw


def normalize_refresh_token_input(value: Any) -> str:
    return _normalize_named_token(value, "refresh_token", "refresh token")


def normalize_access_token_input(value: Any) -> str:
    return _normalize_named_token(value, "access_token", "access token")


def decode_jwt_payload(token: str, label: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise RuntimeError(f"The pasted {label} is not a Tesla JWT.")
    try:
        encoded = parts[1] + ("=" * (-len(parts[1]) % 4))
        payload = json.loads(base64.urlsafe_b64decode(encoded).decode("utf-8"))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError, binascii.Error) as error:
        raise RuntimeError(f"The pasted {label} is malformed.") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"The pasted {label} has an invalid payload.")
    return payload


def validate_native_token_pair(access_token: str, refresh_token: str) -> int:
    access_claims = decode_jwt_payload(access_token, "access token")
    try:
        expires_at = int(access_claims.get("exp", 0) or 0)
    except (TypeError, ValueError) as error:
        raise RuntimeError("The pasted access token has no valid expiration time.") from error
    if expires_at <= int(time.time()) + 30:
        raise RuntimeError("The pasted access token is expired. Run Tesla Auth again and copy both fresh tokens.")

    audience = access_claims.get("aud", [])
    audiences = audience if isinstance(audience, list) else [audience]
    if not any("owner-api.teslamotors.com" in str(item) for item in audiences):
        raise RuntimeError("The pasted access token is not an Owner API token.")

    # Current code-exchange tokens carry this encrypted-session marker. Tesla
    # rejects a freshly refreshed token until the original pair bootstraps the
    # Owner API session, so accepting a generic JWT here would recreate the 403.
    if "x-enc" not in access_claims:
        raise RuntimeError(
            "This is not the original access token from Tesla Auth. "
            "Run Tesla Auth again and copy both tokens from the same fresh result."
        )

    try:
        refresh_claims = decode_jwt_payload(refresh_token, "refresh token")
    except RuntimeError:
        # Older Tesla refresh tokens may be opaque. The live bootstrap request
        # below remains the authoritative validation in that case.
        refresh_claims = {}
    if refresh_claims:
        access_subject = access_claims.get("sub")
        refresh_subject = refresh_claims.get("sub")
        if access_subject and refresh_subject and access_subject != refresh_subject:
            raise RuntimeError("The access and refresh tokens are from different Tesla sessions.")
        try:
            refresh_expires_at = int(refresh_claims.get("exp", 0) or 0)
        except (TypeError, ValueError):
            refresh_expires_at = 0
        if refresh_expires_at and refresh_expires_at <= int(time.time()) + 30:
            raise RuntimeError("The pasted refresh token is expired. Run Tesla Auth again.")
    return expires_at


class ServiceAuthMixin(DashboardServiceBase):
    def load_config(self) -> Dict[str, Any]:
        config: Dict[str, Any] = {}
        self.config_warning = ""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                    if isinstance(loaded, dict):
                        config.update(loaded)
            except json.JSONDecodeError:
                stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_path = f"{self.config_path}.invalid-{stamp}"
                os.replace(self.config_path, backup_path)
                self.config_warning = (
                    f"Saved an invalid auth config backup to {os.path.basename(backup_path)}. "
                    "Please start Tesla sign-in again."
                )
                print(f"[config] Backed up invalid config to {backup_path}", file=sys.stderr, flush=True)
        if not config.get("time_zone") and os.environ.get("TESLA_TIME_ZONE"):
            config["time_zone"] = os.environ["TESLA_TIME_ZONE"]
        return config

    def save_config(self, config: Dict[str, Any]) -> None:
        config_dir = os.path.dirname(os.path.abspath(self.config_path)) or "."
        os.makedirs(config_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=config_dir,
            prefix=".tesla-auth-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(config, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = handle.name
        os.replace(temp_path, self.config_path)

    def effective_sync_cron(self, default_sync_cron: Optional[str] = None) -> str:
        config = self.load_config()
        saved = str(config.get("sync_cron", "") or "").strip()
        if saved:
            return normalize_sync_cron(saved)
        fallback = default_sync_cron or self.sync_cron_default or DEFAULT_SYNC_CRON
        return normalize_sync_cron(fallback)

    def _notify_sync_schedule_changed(self) -> None:
        refresh = self.sync_schedule_refresh
        if callable(refresh):
            refresh()

    def teslapy_available(self) -> bool:
        try:
            import_teslapy()
            return True
        except RuntimeError:
            return False

    def config_public_payload(self) -> Dict[str, Any]:
        config = self.load_config()
        return {
            "email": config.get("email", ""),
            "energy_site_id": config.get("energy_site_id", ""),
            "time_zone": config.get("time_zone", ""),
            "sync_cron": self.effective_sync_cron(),
            "download_root": os.path.relpath(self.download_root),
        }

    def save_user_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        config = self.load_config()
        old_email = config.get("email")

        for key in ("email", "energy_site_id", "time_zone"):
            if key in updates:
                value = str(updates.get(key, "") or "").strip()
                if value:
                    config[key] = value
                else:
                    config.pop(key, None)

        if config.get("email") != old_email:
            for key in ("teslapy_cache", "pending_auth", "owner_api_bootstrapped"):
                config.pop(key, None)

        self.save_config(config)
        return self.config_public_payload()

    def save_sync_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        config = self.load_config()
        sync_cron = normalize_sync_cron(str(updates.get("sync_cron", "") or "").strip())
        config["sync_cron"] = sync_cron
        self.save_config(config)
        self._notify_sync_schedule_changed()
        return {
            "sync_cron": self.effective_sync_cron(),
            "auto_sync_description": describe_sync_schedule(sync_cron),
            "auto_sync_enabled": sync_cron != "off",
        }

    def missing_login_fields(self, config: Optional[Dict[str, Any]] = None) -> List[str]:
        active = config or self.load_config()
        return ["Tesla account email"] if not active.get("email") else []

    def auth_login_ready(self) -> bool:
        return self.teslapy_available() and not self.missing_login_fields()

    def auth_configured(self) -> bool:
        if not self.auth_login_ready():
            return False
        config = self.load_config()
        if not config.get("owner_api_bootstrapped"):
            return False
        try:
            with self._tesla_session() as tesla:
                return bool(tesla.authorized)
        except RuntimeError:
            return False

    def _teslapy_cache_loader(self) -> Dict[str, Any]:
        return dict(self.load_config().get("teslapy_cache", {}))

    def _teslapy_cache_dumper(self, cache: Dict[str, Any]) -> None:
        config = self.load_config()
        config["teslapy_cache"] = cache
        self.save_config(config)

    def _tesla_session(self, email: Optional[str] = None) -> Any:
        teslapy = import_teslapy()
        config = self.load_config()
        active_email = email or config.get("email")
        if not active_email:
            raise RuntimeError("Tesla account email is required.")
        return teslapy.Tesla(
            active_email,
            cache_loader=self._teslapy_cache_loader,
            cache_dumper=self._teslapy_cache_dumper,
            retry=2,
            timeout=DEFAULT_TESLAPY_TIMEOUT,
        )

    def import_token_pair(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        access_token = normalize_access_token_input(updates.get("access_token"))
        refresh_token = normalize_refresh_token_input(updates.get("refresh_token"))
        expires_at = validate_native_token_pair(access_token, refresh_token)
        self.save_user_config(updates)
        config = self.load_config()
        email = str(config.get("email", "") or "").strip()
        if not email:
            raise RuntimeError("Tesla account email is required.")

        now = int(time.time())
        config["teslapy_cache"] = {
            email: {
                "url": TESLA_SSO_BASE_URL,
                "sso": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "Bearer",
                    "expires_at": expires_at,
                    "expires_in": max(expires_at - now, 1),
                },
            }
        }
        config.pop("owner_api_bootstrapped", None)
        self.save_config(config)

        try:
            with self._tesla_session(email=email) as tesla:
                if not tesla.authorized:
                    raise RuntimeError("Tesla did not accept the native token pair.")
                # This first Owner API request is required before refresh-token
                # rotation works reliably. Do not refresh the imported pair first.
                tesla.api("PRODUCT_LIST")
        except Exception as error:
            failed_config = self.load_config()
            failed_config.pop("teslapy_cache", None)
            failed_config.pop("owner_api_bootstrapped", None)
            self.save_config(failed_config)
            response = getattr(error, "response", None)
            status_code = getattr(response, "status_code", None)
            if status_code in (401, 403) or "403" in str(error):
                raise RuntimeError(
                    "Tesla rejected this token pair. Run Tesla Auth again and paste both the access token "
                    "and refresh token from the same fresh result; importing only a refresh token causes this 403."
                ) from error
            raise RuntimeError(f"Unable to validate the Tesla token pair: {error}") from error

        config = self.load_config()
        config.pop("pending_auth", None)
        config["owner_api_bootstrapped"] = True
        self.save_config(config)
        return {"authorized": True}

    def logout(self) -> Dict[str, Any]:
        config = self.load_config()
        config.pop("teslapy_cache", None)
        config.pop("pending_auth", None)
        config.pop("owner_api_bootstrapped", None)
        self.save_config(config)
        return {"authorized": False}
