# treecab

Local implementation workspace for the OD Select drawing engine.

The app now supports two persistence backends:

- `local`: JSON files in `data/projects/`
- `supabase`: hosted project storage in Supabase

The intended hosted backend for this repo is Supabase project `wrvjvijhehyqzrowsfyv`.

Copy `.env.example` values into your environment before using Supabase:

```powershell
$env:OD_DRAW_STORE="supabase"
$env:SUPABASE_PROJECT_REF="wrvjvijhehyqzrowsfyv"
$env:SUPABASE_URL="https://wrvjvijhehyqzrowsfyv.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="..."
```

The app also falls back to the existing system env var `JZ_SUP_TREEDIGITSINC_SERVROLE` if `SUPABASE_SERVICE_ROLE_KEY` is not set.

Apply the database schema in [supabase/migrations/20260313170000_create_projects_table.sql](C:/Users/JZ/git/treecab/supabase/migrations/20260313170000_create_projects_table.sql) to the hosted project before running in Supabase mode.

Run the local editor with:

```powershell
python -m od_draw.main serve --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`.

The app serves:

- project CRUD over FastAPI
- persistence via local JSON or Supabase
- generated previews and outputs in `data/outputs/`
- a no-build local browser editor in `frontend/`

Run the sample workflow with:

```powershell
python -m od_draw.main sample --output build/sample
```

Run tests with:

```powershell
python -m unittest discover -s tests -v
```
