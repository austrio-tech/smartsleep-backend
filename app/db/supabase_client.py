from supabase import create_client, Client
from app.config import settings


def get_supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def get_supabase_admin() -> Client:
    """Service-role client — bypasses RLS. Use only in server-side code."""
    return create_client(settings.supabase_url, settings.supabase_service_key)


def exec(query) -> list:
    """Execute a supabase query and always return a list (never None)."""
    result = query.execute()
    if result is None:
        return []
    return result.data or []
