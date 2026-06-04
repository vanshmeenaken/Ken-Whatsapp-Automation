"""
Supabase client — returns None if credentials are not configured.
campaign_store.py checks for None and falls back to JSON storage.
"""

from config.settings import settings

_client = None


def get_client():
    global _client
    if _client is not None:
        return _client
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        return None
    try:
        from supabase import create_client
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return _client
    except Exception as e:
        print(f"[WARNING] Supabase init failed: {e} — falling back to JSON storage")
        return None


db = get_client
