import io
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import redis
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP
from PIL import Image, UnidentifiedImageError

from api_endpoint import config_old as C
from api_endpoint.mcp.routes import router as mcp_router
from api_endpoint.runnable_floorplan.core.pipeline_old import (
    load_models as load_models_old,
    run_pipeline,
    run_pipeline_preview,
)
from api_endpoint.runnable_floorplan.core.pipeline import (
    load_models as load_models_new,
)
from api_endpoint.runnable_floorplan.routers.four_wall import (
    router as four_wall_router,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
)
log = logging.getLogger("main")

_jobs: dict[str, dict] = {}

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Loading old panorama models...")
    load_models_old()

    log.info("Loading new four-wall models...")
    load_models_new()

    log.info("Models ready.")
    yield
    log.info("Shutdown complete.")


app = FastAPI(
    title="2D CAD Floor Plan API",
    description=(
        "Supports both panorama-based and four-wall-image-based room-to-floorplan generation."
    ),
    version="3.0.0",
    lifespan=lifespan,
)

app.include_router(mcp_router)
app.include_router(four_wall_router, prefix="/api", tags=["four-wall-room"])

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")

mcp = FastApiMCP(app)
mcp.mount_http()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg"}


@app.post("/analytics/visit")
async def add_visit():
    count = r.incr("visits:generate_async")
    return {"count": count}


@app.get("/analytics/visit-count")
async def get_visit_count():
    count = r.get("visits:generate_async") or "0"
    return {"count": int(count)}


def _serialize_result(job_id: str, result: dict) -> dict:
    return {
        "status": "done",
        "job_id": job_id,
        "download_png": f"/download/{job_id}/png",
        "download_dxf": f"/download/{job_id}/dxf",
        "debug_layout_png": f"/download/{job_id}/layout-debug",
        "debug_openings_png": f"/download/{job_id}/openings-debug",
        "debug_furniture_png": f"/download/{job_id}/furniture-debug",
        "room_size_m": result.get("room_size_m"),
        "walls": result.get("walls"),
        "openings": result.get("openings"),
        "furniture": result.get("furniture"),
        "png_path": result.get("png_path"),
        "dxf_path": result.get("dxf_path"),
        "layout_debug_png_path": result.get("layout_debug_png_path"),
        "openings_debug_png_path": result.get("openings_debug_png_path"),
        "furniture_debug_png_path": result.get("furniture_debug_png_path"),
    }


async def _read_and_validate_image(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Upload a JPEG or PNG image.")

    image_bytes = await file.read()

    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            im.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise HTTPException(status_code=422, detail="Invalid image file.")

    return image_bytes


def _run_background(image_bytes: bytes, job_id: str):
    try:
        result = run_pipeline(image_bytes, job_id)
        _jobs[job_id] = _serialize_result(job_id, result)
    except Exception as e:
        log.exception("Background job %s failed", job_id)
        _jobs[job_id] = {"status": "error", "detail": str(e)}


def _get_job(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] == "processing":
        raise HTTPException(status_code=202, detail="Job still processing")
    if job["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail=job.get("detail", "Pipeline error"),
        )
    return job


def _get_output_path(job_id: str, ext: str) -> Path:
    _get_job(job_id)
    path = C.OUTPUT_DIR / f"{job_id}_floorplan.{ext}"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{ext.upper()} file not found")
    return path


def _get_named_output(job_id: str, key: str) -> Path:
    job = _get_job(job_id)
    raw = job.get(key)
    if not raw:
        raise HTTPException(status_code=404, detail="Debug file not found")

    path = Path(raw)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Debug file not found")
    return path


@app.get("/")
async def root():
    return {
        "message": "2D CAD Floor Plan API is running",
        "docs": "/docs",
        "panorama_generate": "/generate",
        "four_wall_generate": "/api/room/four-walls",
    }


@app.post("/generate", tags=["Floor Plan"], operation_id="generate_floorplan")
async def generate_floorplan(file: UploadFile = File(...)):
    image_bytes = await _read_and_validate_image(file)
    job_id = uuid.uuid4().hex

    try:
        result = run_pipeline(image_bytes, job_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.exception("Job %s failed", job_id)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    response = _serialize_result(job_id, result)
    _jobs[job_id] = response
    return response


@app.post(
    "/generate/async",
    tags=["Floor Plan"],
    status_code=202,
    operation_id="generate_floorplan_async",
)
async def generate_floorplan_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    image_bytes = await _read_and_validate_image(file)
    job_id = uuid.uuid4().hex

    _jobs[job_id] = {"status": "processing"}
    background_tasks.add_task(_run_background, image_bytes, job_id)

    return {
        "job_id": job_id,
        "status": "processing",
        "poll_url": f"/jobs/{job_id}",
    }


@app.post("/generate-preview", tags=["Floor Plan"], operation_id="generate_floorplan_preview")
async def generate_preview(file: UploadFile = File(...)):
    image_bytes = await _read_and_validate_image(file)

    try:
        png_bytes = run_pipeline_preview(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.exception("Preview job failed")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    return Response(content=png_bytes, media_type="image/png")


@app.get("/jobs/{job_id}", tags=["Floor Plan"], operation_id="get_floorplan_job_status")
async def get_job_status(job_id: str):
    return _get_job(job_id)


@app.get("/download/{job_id}/png", tags=["Floor Plan"])
async def download_png(job_id: str):
    path = _get_output_path(job_id, "png")
    return FileResponse(
        path,
        media_type="image/png",
        filename=f"{job_id}_floorplan.png",
    )


@app.get("/download/{job_id}/dxf", tags=["Floor Plan"])
async def download_dxf(job_id: str):
    path = _get_output_path(job_id, "dxf")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=f"{job_id}_floorplan.dxf",
    )


@app.get("/download/{job_id}/layout-debug", tags=["Floor Plan"])
async def download_layout_debug(job_id: str):
    path = _get_named_output(job_id, "layout_debug_png_path")
    return FileResponse(
        path,
        media_type="image/png",
        filename=path.name,
    )


@app.get("/download/{job_id}/openings-debug", tags=["Floor Plan"])
async def download_openings_debug(job_id: str):
    path = _get_named_output(job_id, "openings_debug_png_path")
    return FileResponse(
        path,
        media_type="image/png",
        filename=path.name,
    )


@app.get("/download/{job_id}/furniture-debug", tags=["Floor Plan"])
async def download_furniture_debug(job_id: str):
    path = _get_named_output(job_id, "furniture_debug_png_path")
    return FileResponse(
        path,
        media_type="image/png",
        filename=path.name,
    )