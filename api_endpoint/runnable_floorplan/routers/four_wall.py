from fastapi import APIRouter, File, Form, UploadFile

from ..core.pipeline import run_four_wall_pipeline
from ..types import RoomScaleHint, WallImageInput

router = APIRouter()


@router.post("/room/four-walls")
async def build_room_from_four_walls(
    job_id: str = Form(...),
    scale_mode: str = Form("door_width"),
    door_width_m: float = Form(0.90),
    reference_wall: str | None = Form(None),
    reference_wall_length_m: float | None = Form(None),
    fallback_room_width_m: float | None = Form(None),
    fallback_room_depth_m: float | None = Form(None),
    front: UploadFile = File(...),
    right: UploadFile = File(...),
    back: UploadFile = File(...),
    left: UploadFile = File(...),
):
    wall_inputs = [
        WallImageInput(wall="front", image_bytes=await front.read(), image_name=front.filename or "front.jpg"),
        WallImageInput(wall="right", image_bytes=await right.read(), image_name=right.filename or "right.jpg"),
        WallImageInput(wall="back", image_bytes=await back.read(), image_name=back.filename or "back.jpg"),
        WallImageInput(wall="left", image_bytes=await left.read(), image_name=left.filename or "left.jpg"),
    ]

    scale_hint = RoomScaleHint(
        mode=scale_mode,
        door_width_m=door_width_m,
        reference_wall=reference_wall,
        reference_wall_length_m=reference_wall_length_m,
        fallback_room_width_m=fallback_room_width_m,
        fallback_room_depth_m=fallback_room_depth_m,
    )

    return run_four_wall_pipeline(
        wall_inputs=wall_inputs,
        scale_hint=scale_hint,
        job_id=job_id,
    )