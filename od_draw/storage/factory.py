from __future__ import annotations

from od_draw.config import STORE_BACKEND, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL
from od_draw.storage.project_store import ProjectStore
from od_draw.storage.supabase_store import SupabaseProjectStore


def resolve_project_store():
    if STORE_BACKEND == "supabase":
        if not SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required when OD_DRAW_STORE=supabase")
        return SupabaseProjectStore(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return ProjectStore()
