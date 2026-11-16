from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import asyncio
import json
import logging
import os
import shutil
import sys

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .loader import MAX_BYTES
from .models import ReportOptions
from .orchestrator import run_report

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    with TemporaryDirectory(prefix="vkr_reports_") as folder:
        app.state.workspace = Path(folder)
        yield

app = FastAPI(title="Генератор управленческих презентаций", lifespan=lifespan)

class SqlRequest(BaseModel):
    database_url: str
    query: str
    period: str
    title: str = "Управленческая презентация"
    template: str = "standard"
    chart_type: str = "column"
    style: str = "corporate"
    include_cover: bool = True
    subtitle: str = ""
    author: str = ""
    report_type: str = "plan_fact"
    period_end: str = ""
    indicator: str = ""
    one_chart_per_slide: bool = False
    slides_config: list[dict] | None = None


def fail(exc: Exception):
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logging.exception("Ошибка формирования отчета")
    raise HTTPException(status_code=500, detail="Не удалось сформировать презентацию") from exc

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/generate/file")
async def generate_file(file: UploadFile = File(...), period: str = Form(...),
                        title: str = Form("Управленческая презентация"), template: str = Form("standard"),
                        chart_type: str = Form("column"), style: str = Form("corporate"),
                        include_cover: bool = Form(True), subtitle: str = Form(""), author: str = Form(""),
                        report_type: str = Form("plan_fact"), period_end: str = Form(""), indicator: str = Form(""),
                        one_chart_per_slide: bool = Form(False), slides_config: str = Form("")):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".xlsx", ".sql"}:
        raise HTTPException(422, "Допустимы CSV, XLSX и SQL-файлы")
    with TemporaryDirectory(dir=app.state.workspace) as folder:
        incoming = Path(folder) / ("source" + suffix)
        size = 0
        with incoming.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, "Размер файла превышает 100 МБ")
                target.write(chunk)
        try:
            configs = json.loads(slides_config) if slides_config else None
            dest = Path(folder) / "report.pptx"
            await asyncio.to_thread(run_report, ReportOptions(period, title, template, chart_type, style, include_cover, subtitle, author, report_type, period_end, indicator, one_chart_per_slide, configs), dest, incoming)
            # FileResponse needs the file until transmission completes. Copy to workspace and return it.
            from uuid import uuid4
            exported = app.state.workspace / f"{uuid4().hex}.pptx"
            shutil.copy2(dest, exported)
            from starlette.background import BackgroundTask
            return FileResponse(exported, filename="report.pptx", media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                background=BackgroundTask(lambda: exported.unlink(missing_ok=True)))
        except HTTPException:
            raise
        except Exception as exc:
            fail(exc)

@app.post("/api/generate/sql")
async def generate_sql(payload: SqlRequest):
    from uuid import uuid4
    dest = app.state.workspace / f"{uuid4().hex}.pptx"
    try:
        await asyncio.to_thread(run_report, ReportOptions(payload.period, payload.title, payload.template, payload.chart_type,
                                                               payload.style, payload.include_cover, payload.subtitle, payload.author, payload.report_type, payload.period_end, payload.indicator, payload.one_chart_per_slide, payload.slides_config),
                                dest, None, payload.database_url, payload.query)
        from starlette.background import BackgroundTask
        return FileResponse(dest, filename="report.pptx", media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            background=BackgroundTask(lambda: dest.unlink(missing_ok=True)))
    except Exception as exc:
        dest.unlink(missing_ok=True)
        fail(exc)

static_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "static"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
