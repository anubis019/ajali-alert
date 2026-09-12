from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ── Application ───────────────────────────────
    APP_NAME: str = "Ajali Alert System"
    APP_VERSION: str = "2.0.0"
    APP_DESCRIPTION: str = "Kenya Emergency Response Platform — Accidents, Fire, Medical & Security"
    DEBUG: bool = False

    # ── Database ──────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./ajali.db"

    # ── Authentication ─────────────────────────────
    JWT_SECRET: str = "ajali-emergency-response-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 480  # 8-hour shift

    # ── USSD Gateway (Africa's Talking) ────────────
    USSD_CODE: str = "*1233#"
    USSD_SESSION_TIMEOUT: int = 180  # seconds
    AFRICAS_TALKING_API_KEY: str = ""
    AFRICAS_TALKING_USERNAME: str = "sandbox"
    AFRICAS_TALKING_SHORTCODE: str = "12345"

    # ── SMS Gateway ───────────────────────────────
    SMS_PROVIDER: str = "africas_talking"  # africas_talking | twilio | mock
    SMS_FROM: str = "AJALI"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # ── Emergency Response Thresholds ──────────────
    # Golden Hour targets per emergency type (minutes)
    GOLDEN_HOUR_ACCIDENT: int = 5    # Critical accident → 5 min dispatch
    GOLDEN_HOUR_FIRE: int = 3        # Critical fire → 3 min dispatch
    GOLDEN_HOUR_MEDICAL: int = 4     # Critical medical → 4 min dispatch
    GOLDEN_HOUR_SECURITY: int = 5   # Critical security → 5 min dispatch

    # Default escalation check interval (seconds)
    ESCALATION_CHECK_INTERVAL: int = 30

    # Default escalation delays per category+severity (minutes)
    # Critical
    ESCALATION_DELAY_CRITICAL_ACCIDENT: int = 3
    ESCALATION_DELAY_CRITICAL_FIRE: int = 2
    ESCALATION_DELAY_CRITICAL_MEDICAL: int = 3
    ESCALATION_DELAY_CRITICAL_SECURITY: int = 3
    # High
    ESCALATION_DELAY_HIGH: int = 10
    # Medium
    ESCALATION_DELAY_MEDIUM: int = 30
    # Low
    ESCALATION_DELAY_LOW: int = 1440

    # ── Responder Capacity ────────────────────────
    MAX_ACTIVE_ALERTS_PER_RESPONDER: int = 5
    DISPATCH_TIMEOUT_SECONDS: int = 120  # 2 min to accept dispatch

    # ── CORS ───────────────────────────────────────
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173",
                          "https://ajali-alert.vercel.app"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
