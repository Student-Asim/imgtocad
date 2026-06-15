import io
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from api_endpoint.runnable_floorplan.core.pipeline import (
    load_models,
    run_four_wall_pipeline,
)
from api_endpoint.runnable_floorplan.types import RoomScaleHint, WallImageInput

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
)
log = logging.getLogger("main")

_jobs: dict[str, dict] = {}

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Loading models...")
    load_models()
    log.info("Models ready.")
    yield
    log.info("Shutdown complete.")


app = FastAPI(
    title="4-Wall Floor Plan API",
    description="Upload front, right, back, and left wall images to generate a 2D floor plan.",
    version="1.0.0",
    lifespan=lifespan,
)


async def _read_and_validate_image(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Upload JPEG or PNG images only.")

    image_bytes = await file.read()

    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            im.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise HTTPException(status_code=422, detail=f"Invalid image file: {file.filename}")

    return image_bytes


def _serialize_result(job_id: str, result: dict) -> dict:
    return {
        "status": "done",
        "job_id": job_id,
        "walls": result.get("walls"),
        "room_size_m": result.get("room_size_m"),
        "wall_lengths_m": result.get("wall_lengths_m"),
        "openings": result.get("openings"),
        "furniture": result.get("furniture"),
        "png_path": result.get("png_path"),
        "dxf_path": result.get("dxf_path"),
        "layout_debug_png_path": result.get("layout_debug_png_path"),
        "openings_debug_png_path": result.get("openings_debug_png_path"),
        "furniture_debug_png_path": result.get("furniture_debug_png_path"),
        "download_png": f"/download/{job_id}/png",
        "download_dxf": f"/download/{job_id}/dxf",
        "debug_layout_png": f"/download/{job_id}/layout-debug",
        "debug_openings_png": f"/download/{job_id}/openings-debug",
        "debug_furniture_png": f"/download/{job_id}/furniture-debug",
    }


def _get_job(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _get_output_path(job_id: str, key: str) -> Path:
    job = _get_job(job_id)
    raw = job.get(key)
    if not raw:
        raise HTTPException(status_code=404, detail="Output file not found")

    path = Path(raw)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")
    return path


@app.get("/")
async def root():
    return {
        "message": "4-Wall Floor Plan API is running",
        "docs": "/docs",
        "generate": "/generate",
    }


@app.post("/generate", tags=["Floor Plan"])
async def generate_floorplan(
    front: UploadFile = File(...),
    right: UploadFile = File(...),
    back: UploadFile = File(...),
    left: UploadFile = File(...),
):
    job_id = uuid.uuid4().hex

    front_bytes = await _read_and_validate_image(front)
    right_bytes = await _read_and_validate_image(right)
    back_bytes = await _read_and_validate_image(back)
    left_bytes = await _read_and_validate_image(left)

    wall_inputs = [
        WallImageInput(wall="front", image_bytes=front_bytes, image_name=front.filename or "front.png"),
        WallImageInput(wall="right", image_bytes=right_bytes, image_name=right.filename or "right.png"),
        WallImageInput(wall="back", image_bytes=back_bytes, image_name=back.filename or "back.png"),
        WallImageInput(wall="left", image_bytes=left_bytes, image_name=left.filename or "left.png"),
    ]

    scale_hint = RoomScaleHint(
        fallback_room_width_m=4.0,
        fallback_room_depth_m=4.0,
    )

    try:
        result = run_four_wall_pipeline(
            wall_inputs=wall_inputs,
            scale_hint=scale_hint,
            job_id=job_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.exception("Job %s failed", job_id)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    response = _serialize_result(job_id, result)
    _jobs[job_id] = response
    return response


@app.get("/jobs/{job_id}", tags=["Floor Plan"])
async def get_job_status(job_id: str):
    return _get_job(job_id)


@app.get("/download/{job_id}/png", tags=["Floor Plan"])
async def download_png(job_id: str):
    path = _get_output_path(job_id, "png_path")
    return FileResponse(path=path, media_type="image/png", filename=path.name)


@app.get("/download/{job_id}/dxf", tags=["Floor Plan"])
async def download_dxf(job_id: str):
    path = _get_output_path(job_id, "dxf_path")
    return FileResponse(path=path, media_type="application/octet-stream", filename=path.name)


@app.get("/download/{job_id}/layout-debug", tags=["Floor Plan"])
async def download_layout_debug(job_id: str):
    path = _get_output_path(job_id, "layout_debug_png_path")
    return FileResponse(path=path, media_type="image/png", filename=path.name)


@app.get("/download/{job_id}/openings-debug", tags=["Floor Plan"])
async def download_openings_debug(job_id: str):
    path = _get_output_path(job_id, "openings_debug_png_path")
    return FileResponse(path=path, media_type="image/png", filename=path.name)


@app.get("/download/{job_id}/furniture-debug", tags=["Floor Plan"])
async def download_furniture_debug(job_id: str):
    path = _get_output_path(job_id, "furniture_debug_png_path")
    return FileResponse(path=path, media_type="image/png", filename=path.name)