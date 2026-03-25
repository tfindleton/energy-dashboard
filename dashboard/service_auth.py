from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional

from .common import DEFAULT_TESLAPY_TIMEOUT, import_teslapy, normalize_code_verifier
from .scheduler import DEFAULT_SYNC_CRON, describe_sync_schedule, normalize_sync_cron
from .service_base import DashboardServiceBase


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
        env_map = {
            "email": "TESLA_EMAIL",
            "energy_site_id": "TESLA_ENERGY_SITE_ID",
            "time_zone": "TESLA_TIME_ZONE",
        }
        for key, env_name in env_map.items():
            if os.environ.get(env_name):
                config[key] = os.environ[env_name]
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
        pending_auth = config.get("pending_auth") or {}
        return {
            "email": config.get("email", ""),
            "energy_site_id": config.get("energy_site_id", ""),
            "time_zone": config.get("time_zone", ""),
            "sync_cron": self.effective_sync_cron(),
            "auth_pending": bool(pending_auth),
            "pending_auth_url": pending_auth.get("authorization_url", ""),
            "download_root": self.download_root,
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
            for key in ("teslapy_cache", "pending_auth"):
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

    def _tesla_session(
        self,
        email: Optional[str] = None,
        state: Optional[str] = None,
        code_verifier: Optional[str] = None,
    ) -> Any:
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
            state=state,
            code_verifier=code_verifier,
        )

    def start_web_login(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        self.save_user_config(updates)
        config = self.load_config()
        if not config.get("email"):
            raise RuntimeError("Tesla account email is required.")
        with self._tesla_session() as tesla:
            if tesla.authorized:
                return {"authorization_url": "", "already_authorized": True}
            state = tesla.new_state()
            code_verifier = tesla.new_code_verifier()
            authorization_url = tesla.authorization_url(state=state, code_verifier=code_verifier)
        config["pending_auth"] = {
            "email": config["email"],
            "state": state,
            "code_verifier": normalize_code_verifier(code_verifier),
            "authorization_url": authorization_url,
        }
        self.save_config(config)
        return {"authorization_url": authorization_url, "already_authorized": False}

    def finish_web_login(self, authorization_response: str) -> Dict[str, Any]:
        if not authorization_response:
            raise RuntimeError("Paste the full Tesla URL from the final page.")
        config = self.load_config()
        pending_auth = config.get("pending_auth") or {}
        email = pending_auth.get("email") or config.get("email")
        state = pending_auth.get("state")
        code_verifier = pending_auth.get("code_verifier")
        if not (email and state and code_verifier):
            raise RuntimeError("No Tesla sign-in is in progress. Start sign-in first.")
        with self._tesla_session(email=email, state=state, code_verifier=code_verifier) as tesla:
            tesla.fetch_token(authorization_response=authorization_response)
        config = self.load_config()
        config.pop("pending_auth", None)
        self.save_config(config)
        return {"authorized": True}

    def logout(self) -> Dict[str, Any]:
        config = self.load_config()
        config.pop("teslapy_cache", None)
        config.pop("pending_auth", None)
        self.save_config(config)
        return {"authorized": False}
