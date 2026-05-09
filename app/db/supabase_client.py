from supabase import create_client, Client
from app.config import settings

_supabase_client: Client | None = None
_supabase_admin_client: Client | None = None


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    return _supabase_client


def get_supabase_admin() -> Client:
    """Service-role client — bypasses RLS. Use only in server-side code."""
    global _supabase_admin_client
    if _supabase_admin_client is None:
        _supabase_admin_client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _supabase_admin_client
