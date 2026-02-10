from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    database_url: str = "sqlite:///./app.db"
    yahoo_client_id: str = ""
    rakuten_app_id: str = ""
    rakuten_access_key: str = ""
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    ebay_refresh_token: str = ""
    ebay_marketplace_id: str = "EBAY_US"
    http_timeout_seconds: float = 15.0
    compliance_mode: str = "warn"
    block_auto_accept_cross_market: bool = True
    auto_accept_requires_trusted_price: bool = False
    yahoo_min_interval_seconds: float = 1.0
    rakuten_min_interval_seconds: float = 0.5
    ebay_min_interval_seconds: float = 0.25
    min_expected_margin_rate: float = 0.10
    category_min_margin_overrides: str = ""
    min_expected_profit_jpy: float = 0.0
    min_title_similarity_auto_accept: float = 0.35
    min_title_similarity_human_review: float = 0.20
    scheduler_enabled: bool = True
    scheduler_poll_seconds: int = 30
    fx_usd_jpy: float = 150.0
    fx_auto_update_enabled: bool = True
    fx_update_interval_minutes: int = 60
    fx_refresh_retry_minutes: int = 10
    fx_rate_provider_url: str = "https://open.er-api.com/v6/latest/USD"
    ebay_fee_rate: float = 0.13
    international_payment_fee_rate: float = 0.04
    packaging_cost_jpy: int = 120
    min_auto_accept_score: float = 0.85
    min_human_review_score: float = 0.40
    accessory_reject_score: float = 0.80
    scan_cooldown_minutes: int = 60
    scan_summary_reset_timezone: str = "Asia/Tokyo"
    yahoo_hourly_call_budget: int = 0
    rakuten_hourly_call_budget: int = 0
    ebay_hourly_call_budget: int = 0
    api_usage_use_ebay_rate_api: bool = True
    ebay_rate_limit_api_url: str = "https://api.ebay.com/developer/analytics/v1_beta/rate_limit/"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
