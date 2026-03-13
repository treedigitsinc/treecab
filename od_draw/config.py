"""Project-wide constants for local rendering."""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT_DIR / "build" / "sample"
DATA_DIR = ROOT_DIR / "data"
PROJECTS_DIR = DATA_DIR / "projects"
OUTPUTS_DIR = DATA_DIR / "outputs"
FRONTEND_DIR = ROOT_DIR / "frontend"

STORE_BACKEND = os.getenv("OD_DRAW_STORE", "local")
SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "wrvjvijhehyqzrowsfyv")
SUPABASE_URL = os.getenv("SUPABASE_URL", f"https://{SUPABASE_PROJECT_REF}.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_TABLE = os.getenv("SUPABASE_PROJECTS_TABLE", "projects")
