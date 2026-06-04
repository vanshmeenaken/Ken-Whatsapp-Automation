"""
Supabase client singleton.
Import `db` from this module everywhere you need database access.
"""

from supabase import create_client, Client
from config.settings import settings

_client: Client = None


def get_client() -> Client:
    global _client
    if _client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env"
            )
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client


# Shorthand used throughout the codebase
db = get_client
