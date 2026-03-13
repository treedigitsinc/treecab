"""Project-wide constants for local rendering."""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT_DIR / "build" / "sample"
DEFAULT_DATA_DIR = Path("/tmp/od_draw") if os.getenv("VERCEL") else ROOT_DIR / "data"


def resolve_data_dir() -> Path:
    configured = Path(os.getenv("OD_DRAW_DATA_DIR", str(DEFAULT_DATA_DIR)))
    try:
        configured.mkdir(parents=True, exist_ok=True)
        probe = configured / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return configured
    except OSError:
        fallback = Path("/tmp/od_draw")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


DATA_DIR = resolve_data_dir()
PROJECTS_DIR = DATA_DIR / "projects"
OUTPUTS_DIR = DATA_DIR / "outputs"
MASTER_PROJECTS_DIR = DATA_DIR / "master-projects"
MASTER_OUTPUTS_DIR = DATA_DIR / "master-outputs"
MASTER_ASSETS_DIR = DATA_DIR / "master-assets"
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_BUILD_DIR = FRONTEND_DIR / "dist"
FRONTEND_STATIC_DIR = FRONTEND_BUILD_DIR if FRONTEND_BUILD_DIR.exists() else FRONTEND_DIR
FRONTEND_INDEX_FILE = FRONTEND_STATIC_DIR / "index.html"

STORE_BACKEND = os.getenv("OD_DRAW_STORE", "local")
SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "wrvjvijhehyqzrowsfyv")
SUPABASE_URL = os.getenv("SUPABASE_URL", f"https://{SUPABASE_PROJECT_REF}.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("JZ_SUP_TREEDIGITSINC_ANON", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv(
    "JZ_SUP_TREEDIGITSINC_SERVROLE", ""
)
SUPABASE_TABLE = os.getenv("SUPABASE_PROJECTS_TABLE", "projects")
SITE_PASSWORD = os.getenv("TREECAB_SITE_PASSWORD", "nina@123@321")
AUTH_COOKIE_NAME = os.getenv("TREECAB_AUTH_COOKIE_NAME", "treecab_auth")
AUTH_COOKIE_VALUE = os.getenv("TREECAB_AUTH_COOKIE_VALUE", "treecab-session")
AUTH_COOKIE_SECURE = os.getenv("TREECAB_AUTH_COOKIE_SECURE", "").lower() in {"1", "true", "yes", "on"}
