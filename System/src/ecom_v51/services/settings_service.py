from __future__ import annotations

from dataclasses import asdict

from ecom_v51.config.settings import settings


class SettingsService:
    def get_overview(self) -> dict[str, object]:
        data = asdict(settings)
        return {
            "runtime": {
                "app_env": data["app_env"],
                "debug": data["debug"],
                "timezone": data["timezone"],
                "default_currency": data["default_currency"],
            },
            "data_sources": {
                "database_url": data["database_url"],
                "redis_url": data["redis_url"],
            },
            "scheduler": {
                "hourly": data["scheduler_hourly_enabled"],
                "daily": data["scheduler_daily_enabled"],
                "weekly": data["scheduler_weekly_enabled"],
            },
        }
