import logging

import numpy as np

from api_endpoint import config as C
from ..detectors.furniture import detect_furniture
from ..detectors.horizonnet import run_horizonnet
from ..detectors.openings import detect_doors_windows, map_openings
from ..geometry.layout import build_floorplan_polygon
from ..placement.furniture_mapper import map_furniture
from ..renderers.debug_renderer import save_furniture_debug_overlay, save_layout_debug, save_openings_debug_overlay
from ..renderers.floorplan_renderer import render_floorplan
from ..types import PipelineArtifacts, PipelineResult
from .io_utils import load_rgb_image
from .registry import ModelRegistry

log = logging.getLogger("pipeline")
_registry = ModelRegistry()


def load_models():
    _registry.load()


def build_artifacts(job_id: str) -> PipelineArtifacts:
    return PipelineArtifacts(
        floorplan_png=C.OUTPUT_DIR / f"{job_id}_floorplan.png",
        floorplan_dxf=C.OUTPUT_DIR / f"{job_id}_floorplan.dxf",
        layout_debug_png=C.OUTPUT_DIR / f"{job_id}_layout_debug.png",
        openings_debug_png=C.OUTPUT_DIR / f"{job_id}_openings_debug.png",
        furniture_debug_png=C.OUTPUT_DIR / f"{job_id}_furniture_debug.png",
    )


def serialize_openings(mapped_openings):
    return [
        {
            "type": o.type,
            "tag": o.tag,
            "conf": o.conf,
            "wall": o.wall_i,
            "frac": round(float(o.frac), 3),
            "raw_class": o.raw_class,
            "class_id": o.class_id,
            "pano_xy": o.pano_xy,
        }
        for o in mapped_openings
    ]


def serialize_furniture(mapped_furniture):
    return [
        {
            "tag": f.tag,
            "type": f.type,
            "label": f.label,
            "conf": round(float(f.conf), 3),
            "wall": f.wall_i,
            "size_m": [round(float(f.size[0]), 2), round(float(f.size[1]), 2)],
            "pano_xy": [round(float(f.pano_xy[0]), 1), round(float(f.pano_xy[1]), 1)],
        }
        for f in mapped_furniture
    ]


def run_pipeline(image_bytes: bytes, job_id: str) -> dict:
    artifacts = build_artifacts(job_id)
    img_pil = load_rgb_image(image_bytes)
    cor, bon, img_np, img_pil_resized = run_horizonnet(_registry, img_pil)
    width, height = img_pil_resized.size
    layout = build_floorplan_polygon(cor, width)
    dw_dets = detect_doors_windows(img_pil_resized)
    mapped_openings = map_openings(dw_dets, layout, width, height)
    furniture_dets = detect_furniture(_registry, img_pil_resized)
    mapped_furniture = map_furniture(furniture_dets, layout, width, height, mapped_openings)
    log.info("Furniture detections raw: %s", [(d.type, round(d.conf, 3), round(d.cx, 1), round(d.cy, 1)) for d in furniture_dets])
    log.info("Furniture mapped: %s", [(f.type, f.label, [round(x, 2) for x in f.center], [round(s, 2) for s in f.size]) for f in mapped_furniture])
    save_layout_debug(layout, width, artifacts.layout_debug_png)
    save_openings_debug_overlay(img_np, mapped_openings, artifacts.openings_debug_png)
    save_furniture_debug_overlay(img_np, furniture_dets, artifacts.furniture_debug_png)
    render_floorplan(layout, mapped_openings, mapped_furniture, artifacts.floorplan_png, artifacts.floorplan_dxf, C.WALL_THICKNESS, C.DXF_SCALE)
    doors = [o for o in mapped_openings if o.type == "door"]
    windows = [o for o in mapped_openings if o.type == "window"]
    room_size_m = {
        "width": round(float(np.ptp(layout.pts_m[:, 0])), 2),
        "depth": round(float(np.ptp(layout.pts_m[:, 1])), 2),
        "area": round(float(0.5 * abs(np.dot(layout.pts_m[:, 0], np.roll(layout.pts_m[:, 1], -1)) - np.dot(layout.pts_m[:, 1], np.roll(layout.pts_m[:, 0], -1)))), 2),
    }
    result = PipelineResult(
        job_id=job_id,
        walls=layout.n_walls,
        doors=len(doors),
        windows=len(windows),
        openings=serialize_openings(mapped_openings),
        furniture=serialize_furniture(mapped_furniture),
        room_size_m=room_size_m,
        artifacts=artifacts,
    )
    return result.to_dict()