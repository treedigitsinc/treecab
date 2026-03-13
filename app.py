import traceback

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()

try:
    from od_draw.main import app as inner_app

    app.mount("/", inner_app)
except Exception:
    trace = traceback.format_exc()
    print(trace)

    @app.get("/{path:path}")
    def import_failure(path: str = ""):
        return PlainTextResponse("Application failed to start.", status_code=500)
