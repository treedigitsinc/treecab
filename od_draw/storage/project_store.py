from __future__ import annotations

import json
from pathlib import Path

from od_draw.config import OUTPUTS_DIR, PROJECTS_DIR
from od_draw.engine.geometry_engine import prepare_project
from od_draw.sample_project import build_sample_project
from od_draw.sheets.sheet_composer import build_default_sheets
from od_draw.storage.serializer import project_from_dict, project_to_dict


class ProjectStore:
    backend_name = "local"

    def __init__(self, projects_dir: Path = PROJECTS_DIR, outputs_dir: Path = OUTPUTS_DIR) -> None:
        self.projects_dir = projects_dir
        self.outputs_dir = outputs_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def project_path(self, project_id: str) -> Path:
        return self.projects_dir / f"{project_id}.json"

    def output_dir(self, project_id: str) -> Path:
        path = self.outputs_dir / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def list_projects(self) -> list[dict]:
        items = []
        for path in sorted(self.projects_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(
                {
                    "id": data["id"],
                    "address": data["address"],
                    "created_at": data["created_at"],
                    "room_count": len(data.get("rooms", [])),
                }
            )
        return items

    def load(self, project_id: str):
        path = self.project_path(project_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        return project_from_dict(data)

    def save(self, project):
        path = self.project_path(project.id)
        path.write_text(json.dumps(project_to_dict(project), indent=2), encoding="utf-8")
        return project

    def ensure_sample(self):
        if self.project_path("od-select-sample").exists():
            return self.load("od-select-sample")
        project = build_sample_project()
        prepare_project(project)
        build_default_sheets(project)
        return self.save(project)
