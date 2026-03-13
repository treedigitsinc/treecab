from __future__ import annotations

import json
from pathlib import Path

from od_draw.config import MASTER_ASSETS_DIR, MASTER_OUTPUTS_DIR, MASTER_PROJECTS_DIR
from od_draw.sample_master_project import build_sample_master_project
from od_draw.storage.master_serializer import project_from_dict, project_to_dict


class MasterProjectStore:
    backend_name = "local-master"

    def __init__(
        self,
        projects_dir: Path = MASTER_PROJECTS_DIR,
        outputs_dir: Path = MASTER_OUTPUTS_DIR,
        assets_dir: Path = MASTER_ASSETS_DIR,
    ) -> None:
        self.projects_dir = projects_dir
        self.outputs_dir = outputs_dir
        self.assets_dir = assets_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    def project_path(self, project_id: str) -> Path:
        return self.projects_dir / f"{project_id}.json"

    def output_dir(self, project_id: str) -> Path:
        path = self.outputs_dir / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def asset_dir(self, project_id: str) -> Path:
        path = self.assets_dir / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def list_projects(self) -> list[dict]:
        items: list[dict] = []
        for path in sorted(self.projects_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(
                {
                    "id": data["id"],
                    "address": data.get("address", ""),
                    "created_at": data.get("date", ""),
                    "room_count": len(data.get("model", {}).get("rooms", [])),
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
        project_id = "od-select-master-sample"
        if self.project_path(project_id).exists():
            return self.load(project_id)
        project = build_sample_master_project()
        project.id = project_id
        return self.save(project)
