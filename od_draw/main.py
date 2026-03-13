from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from od_draw.api.app import create_app
from od_draw.catalog.kcd_export import export_project_tsv
from od_draw.config import DEFAULT_OUTPUT_DIR
from od_draw.engine.geometry_engine import prepare_project
from od_draw.renderer.drawing_renderer import DrawingRenderer
from od_draw.sample_project import build_sample_project
from od_draw.sheets.sheet_composer import build_default_sheets

app = create_app()


def run_sample(output_dir: Path) -> None:
    project = prepare_project(build_sample_project())
    build_default_sheets(project)
    renderer = DrawingRenderer()
    pdf_path = renderer.render_project(project, output_dir)
    tsv_path = export_project_tsv(project, output_dir / f"{project.id}.tsv")
    print(f"PDF: {pdf_path}")
    print(f"TSV: {tsv_path}")
    print(f"SVG sheets: {output_dir}")


def serve(host: str, port: int) -> None:
    uvicorn.run("od_draw.main:app", host=host, port=port, reload=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OD Select local drawing engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sample_parser = subparsers.add_parser("sample", help="Generate the sample project outputs")
    sample_parser.add_argument("--output", default=str(DEFAULT_OUTPUT_DIR), help="Output directory")

    serve_parser = subparsers.add_parser("serve", help="Run the local editing app")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "sample":
        run_sample(Path(args.output))
        return
    if args.command == "serve":
        serve(args.host, args.port)


if __name__ == "__main__":
    main()
