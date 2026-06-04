import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Periskope API
    PERISKOPE_API_KEY: str = os.getenv("PERISKOPE_API_KEY", "")
    PERISKOPE_ORG_PHONE: str = os.getenv("PERISKOPE_ORG_PHONE", "")

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # API Config
    API_ENV: str = os.getenv("API_ENV", "development")
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "dev_secret_change_in_production")
    API_PORT: int = int(os.getenv("API_PORT", 8000))

    # Claude CLI (dev only)
    CLAUDE_CLI_ENABLED: bool = os.getenv("CLAUDE_CLI_ENABLED", "false").lower() == "true"
    CLAUDE_CLI_TIMEOUT: int = int(os.getenv("CLAUDE_CLI_TIMEOUT", 30))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "./data/messages.db")

    # Rate Limiting
    MAX_BATCH_SIZE: int = int(os.getenv("MAX_BATCH_SIZE", 500))

    MESSAGE_MAX_LENGTH: int = 4096
    PHONE_REGEX_PATTERN: str = r"^\+?[1-9]\d{7,14}$"

    @classmethod
    def get_auth_headers(cls) -> dict:
        """Return Periskope-required headers for every API call."""
        return {
            "Authorization": f"Bearer {cls.PERISKOPE_API_KEY}",
            "x-phone": cls.PERISKOPE_ORG_PHONE,
            "Content-Type": "application/json",
        }

    @classmethod
    def validate(cls):
        if not cls.PERISKOPE_API_KEY:
            print("[WARNING] PERISKOPE_API_KEY not set in .env")
        if not cls.PERISKOPE_ORG_PHONE:
            print("[WARNING] PERISKOPE_ORG_PHONE not set in .env")
        if not cls.SUPABASE_URL or not cls.SUPABASE_KEY:
            print("[WARNING] SUPABASE_URL / SUPABASE_KEY not set — data will not persist")


settings = Settings()
