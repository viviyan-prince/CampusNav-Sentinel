"""FastAPI web application for CampusNav Sentinel."""

from __future__ import annotations

import json
import logging
import shutil
import time
import uuid
from pathlib import Path
from typing import Optional

import cv2
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import Config
from app.pipeline import Pipeline

logger = logging.getLogger(__name__)

config = Config.from_env()
app = FastAPI(title="CampusNav Sentinel", version="1.0.0",
              description="Agentic Visual Hazard Analysis for Autonomous Campus Shuttles")

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
STATIC_DIR = Path(__file__).parent.parent / "static"
TEMPLATE_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

jobs: dict[str, dict] = {}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "opencv_version": cv2.__version__,
        "service": "campusnav-sentinel",
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics():
    return {
        "total_jobs": len(jobs),
        "completed_jobs": sum(1 for j in jobs.values() if j.get("status") == "completed"),
        "failed_jobs": sum(1 for j in jobs.values() if j.get("status") == "failed"),
        "opencv_version": cv2.__version__,
    }


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in (".mp4", ".avi", ".mov", ".mkv", ".webm", ".jpg", ".jpeg", ".png", ".bmp"):
        raise HTTPException(400, f"Unsupported format: {ext}")

    job_id = str(uuid.uuid4())[:8]
    upload_dir = config.upload_dir / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    input_path = upload_dir / f"input{ext}"

    try:
        content = await file.read()
        if len(content) > config.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"File too large (max {config.max_upload_mb}MB)")
        with open(input_path, "wb") as f:
            f.write(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {e}")

    output_dir = config.output_dir / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    jobs[job_id] = {"status": "processing", "started": time.time()}

    try:
        pipeline = Pipeline(config)
        report = pipeline.run(str(input_path), str(output_dir))
        jobs[job_id] = {"status": "completed", "report": report, "output_dir": str(output_dir)}
        return {"job_id": job_id, "status": "completed", "report": report}
    except Exception as e:
        logger.error("Analysis failed for job %s: %s", job_id, e, exc_info=True)
        jobs[job_id] = {"status": "failed", "error": str(e)}
        raise HTTPException(500, f"Analysis failed: {e}")


@app.get("/results/{job_id}")
def get_results(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[job_id]


@app.get("/results/{job_id}/output")
def get_output_file(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    job = jobs[job_id]
    if job.get("status") != "completed":
        raise HTTPException(400, "Job not completed")
    out_dir = Path(job["output_dir"])
    for ext in ("mp4", "jpg", "png"):
        candidate = out_dir / f"annotated_output.{ext}"
        if candidate.exists():
            return FileResponse(str(candidate))
    raise HTTPException(404, "Output file not found")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"opencv_version": cv2.__version__})


def create_app() -> FastAPI:
    return app
