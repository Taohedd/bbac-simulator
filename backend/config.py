"""
Configuration management for the BBAC Simulator backend.
Loads environment variables from the .env file using Pydantic Settings.
All other modules import the global `settings` instance from this file.
"""

from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # --- Database ---
    DATABASE_URL: str

    # --- API Server ---
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True

    # --- CORS ---
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # --- Security ---
    SECRET_KEY: str

    # --- Simulation Engine ---
    SIMULATION_INTERVAL_MS: int = 1000

    # --- Risk Thresholds ---
    RISK_LOW_THRESHOLD: int = 30    # 0–30   → ALLOW
    RISK_HIGH_THRESHOLD: int = 70   # 31–69  → MFA_CHALLENGE, 70–100 → BLOCK

    # --- Machine Learning ---
    ML_MIN_LOGS_FOR_BASELINE: int = 50
    ML_CONTAMINATION_RATE: float = 0.05
    ML_N_ESTIMATORS: int = 100

    # --- Authentication (hardcoded for demo — migrate to DB auth in production) ---
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    USER_USERNAME: str
    USER_PASSWORD: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse a comma-separated string into a list of origin URLs."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        raise ValueError(
            f"CORS_ORIGINS must be a list or comma-separated string, got: {type(v)}"
        )

    @field_validator("ML_CONTAMINATION_RATE", mode="before")
    @classmethod
    def validate_contamination_rate(cls, v: float) -> float:
        """Isolation Forest requires contamination to be between 0.0 and 0.5."""
        v = float(v)
        if not (0.0 < v <= 0.5):
            raise ValueError(
                f"ML_CONTAMINATION_RATE must be between 0.0 and 0.5, got: {v}"
            )
        return v

    @model_validator(mode="after")
    def validate_risk_thresholds(self) -> "Settings":
        """Ensure RISK_LOW_THRESHOLD is strictly less than RISK_HIGH_THRESHOLD."""
        if self.RISK_LOW_THRESHOLD >= self.RISK_HIGH_THRESHOLD:
            raise ValueError(
                f"RISK_LOW_THRESHOLD ({self.RISK_LOW_THRESHOLD}) must be "
                f"less than RISK_HIGH_THRESHOLD ({self.RISK_HIGH_THRESHOLD})"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Global singleton — import this instance everywhere in the application:
# from config import settings
settings = Settings()