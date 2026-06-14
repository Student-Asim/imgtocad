import base64
import io
import uuid
import logging
from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image

from .schemas import ImageBytesRequest, PreviewRequest
from api_endpoint.runnable_floorplan.core.pipeline_old import run_pipeline, run_pipeline_preview

router = APIRouter(prefix="/mcp", tags=["MCP"])

log = logging.getLogger("mcp")

_jobs = {}

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

@router.post("/generate", operation_id="generate_floorplan_from_base64")
async def generate_floorplan_from_base64(payload: ImageBytesRequest):
    try:
        image_bytes = base64.b64decode(payload.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image")

    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            im.verify()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid image file")

    job_id = uuid.uuid4().hex

    try:
        result = run_pipeline(image_bytes, job_id)
    except Exception as e:
        log.exception("MCP generate failed")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    response = _serialize_result(job_id, result)
    _jobs[job_id] = response
    return response

@router.post("/generate-preview", operation_id="generate_floorplan_preview_from_base64")
async def generate_preview_from_base64(payload: PreviewRequest):
    try:
        image_bytes = base64.b64decode(payload.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image")

    try:
        png_bytes = run_pipeline_preview(image_bytes)
    except Exception as e:
        log.exception("MCP preview failed")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    return StreamingResponse(BytesIO(png_bytes), media_type="image/png")