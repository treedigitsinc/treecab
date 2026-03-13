from __future__ import annotations

from pathlib import Path

import httpx

from od_draw.config import OUTPUTS_DIR, SUPABASE_TABLE
from od_draw.engine.geometry_engine import prepare_project
from od_draw.sample_project import build_sample_project
from od_draw.sheets.sheet_composer import build_default_sheets
from od_draw.storage.serializer import project_from_dict, project_to_dict


class SupabaseProjectStore:
    backend_name = "supabase"

    def __init__(self, supabase_url: str, service_role_key: str, outputs_dir: Path = OUTPUTS_DIR) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key
        self.outputs_dir = outputs_dir
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.table = SUPABASE_TABLE

    @property
    def headers(self) -> dict:
        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }

    def output_dir(self, project_id: str) -> Path:
        path = self.outputs_dir / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _rest(self, method: str, path: str, **kwargs) -> httpx.Response:
        response = httpx.request(
            method,
            f"{self.supabase_url}/rest/v1/{path.lstrip('/')}",
            headers={**self.headers, **kwargs.pop("headers", {})},
            timeout=30,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def list_projects(self) -> list[dict]:
        response = self._rest(
            "GET",
            self.table,
            params={"select": "id,address,created_at,project_data", "order": "created_at.desc"},
        )
        items = []
        for row in response.json():
            items.append(
                {
                    "id": row["id"],
                    "address": row["address"],
                    "created_at": row["created_at"],
                    "room_count": len(row.get("project_data", {}).get("rooms", [])),
                }
            )
        return items

    def load(self, project_id: str):
        response = self._rest(
            "GET",
            self.table,
            params={"id": f"eq.{project_id}", "select": "project_data"},
            headers={"Accept": "application/json"},
        )
        rows = response.json()
        if not rows:
            raise FileNotFoundError(project_id)
        return project_from_dict(rows[0]["project_data"])

    def save(self, project):
        payload = project_to_dict(project)
        row = {
            "id": project.id,
            "address": project.address,
            "kcd_color": project.kcd_color,
            "kcd_style": project.kcd_style,
            "drawer_type": project.drawer_type,
            "uppers_height": project.uppers_height,
            "crown_molding": project.crown_molding,
            "designer": project.designer,
            "created_at": project.created_at.isoformat(),
            "project_data": payload,
        }
        self._rest(
            "POST",
            self.table,
            params={"on_conflict": "id"},
            headers={"Prefer": "resolution=merge-duplicates,return=representation"},
            json=[row],
        )
        return project

    def ensure_sample(self):
        try:
            return self.load("od-select-sample")
        except FileNotFoundError:
            project = build_sample_project()
            prepare_project(project)
            build_default_sheets(project)
            return self.save(project)
