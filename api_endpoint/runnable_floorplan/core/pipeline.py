import logging

import numpy as np

from api_endpoint import config as C
from ..detectors.furniture import detect_furniture
from ..detectors.openings import detect_doors_windows
from ..geometry.room_builder import build_room_from_wall_sections
from ..renderers.floorplan_renderer import render_floorplan_from_wall_sections
from ..renderers.debug_renderer import (
    save_furniture_debug_overlay,
    save_layout_debug,
    save_openings_debug_overlay,
)
from ..types import (
    PipelineArtifacts,
    PipelineResult,
    RoomScaleHint,
    WallFurniture,
    WallImageInput,
    WallOpening,
    WallSection,
)
from .io_utils import load_rgb_image
from .registry import ModelRegistry

log = logging.getLogger(__name__)
_registry = ModelRegistry()


def load_models():
    _registry.load()


def build_artifacts(job_id: str) -> PipelineArtifacts:
    output_dir = C.OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    debug_dir = output_dir / f"{job_id}_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    return PipelineArtifacts(
        floorplan_png=output_dir / f"{job_id}_final_cad_image.png",
        floorplan_dxf=output_dir / f"{job_id}_final_cad.dxf",
        debug_dir=debug_dir,
        layout_debug_png=debug_dir / "room_detection.png",
        openings_debug_png=debug_dir / "front_door_window_detection.png",
        furniture_debug_png=debug_dir / "front_furniture_detection.png",
    )


def _polygon_area(pts):
    return 0.5 * abs(
        np.dot(pts[:, 0], np.roll(pts[:, 1], -1))
        - np.dot(pts[:, 1], np.roll(pts[:, 0], -1))
    )


def _make_wall_openings(wall_name, raw_dets, width_px):
    openings = []
    counts = {"door": 0, "window": 0}

    for det in sorted(raw_dets, key=lambda d: (-d.conf, d.type)):
        if det.type not in {"door", "window"}:
            continue

        counts[det.type] += 1
        frac = float(np.clip(det.cx / max(width_px, 1), 0.0, 1.0))
        width_frac = float(np.clip(det.w / max(width_px, 1), 0.0, 1.0))
        tag = f"{'D' if det.type == 'door' else 'W'}{counts[det.type]}_{wall_name}"

        openings.append(
            WallOpening(
                wall=wall_name,
                type=det.type,
                tag=tag,
                conf=det.conf,
                frac=frac,
                width_frac=width_frac,
                center_px=(float(det.cx), float(det.cy)),
                width_m=None,
            )
        )

    return openings


def _make_wall_furniture(wall_name, raw_dets, width_px):
    items = []
    counts = {}

    for det in sorted(raw_dets, key=lambda d: (-d.conf, d.type)):
        cls = det.type
        counts[cls] = counts.get(cls, 0) + 1
        frac = float(np.clip(det.cx / max(width_px, 1), 0.0, 1.0))
        tag = f"{cls[:2].upper()}{counts[cls]}_{wall_name}"

        items.append(
            WallFurniture(
                wall=wall_name,
                tag=tag,
                type=det.type,
                label=det.label,
                conf=det.conf,
                frac=frac,
                center_px=(float(det.cx), float(det.cy)),
                size_m=None,
            )
        )

    return items


def _estimate_wall_section(image_input: WallImageInput, artifacts: PipelineArtifacts) -> WallSection:
    img_pil = load_rgb_image(image_input.image_bytes)
    width_px, height_px = img_pil.size
    img_np = np.array(img_pil)

    opening_dets = detect_doors_windows(img_pil)
    furniture_dets = detect_furniture(_registry, img_pil)

    openings = _make_wall_openings(image_input.wall, opening_dets, width_px)
    furniture = _make_wall_furniture(image_input.wall, furniture_dets, width_px)

    openings_debug_path = artifacts.debug_dir / f"{image_input.wall}_door_window_detection.png"
    furniture_debug_path = artifacts.debug_dir / f"{image_input.wall}_furniture_detection.png"

    openings_debug_path.parent.mkdir(parents=True, exist_ok=True)
    furniture_debug_path.parent.mkdir(parents=True, exist_ok=True)

    save_openings_debug_overlay(img_np, openings, openings_debug_path)
    save_furniture_debug_overlay(img_np, furniture_dets, furniture_debug_path)

    if image_input.wall == "front":
        artifacts.openings_debug_png = openings_debug_path
        artifacts.furniture_debug_png = furniture_debug_path

    return WallSection(
        wall=image_input.wall,
        width_px=width_px,
        height_px=height_px,
        estimated_length_units=1.0,
        openings=openings,
        furniture=furniture,
        scale_source="wall_image_width",
    )


def _serialize_openings(layout):
    rows = []
    for wall_name, sec in layout.wall_sections.items():
        wall_len = layout.wall_lengths_m[wall_name]
        for o in sec.openings:
            rows.append(
                {
                    "wall": wall_name,
                    "type": o.type,
                    "tag": o.tag,
                    "conf": round(float(o.conf), 3),
                    "frac": round(float(o.frac), 3),
                    "x_m": round(float(o.frac * wall_len), 2),
                    "width_m": round(float(o.width_m or 0.0), 2),
                }
            )
    return rows


def _serialize_furniture(layout):
    rows = []
    for wall_name, sec in layout.wall_sections.items():
        wall_len = layout.wall_lengths_m[wall_name]
        for f in sec.furniture:
            rows.append(
                {
                    "wall": wall_name,
                    "tag": f.tag,
                    "type": f.type,
                    "label": f.label,
                    "conf": round(float(f.conf), 3),
                    "x_m": round(float(f.frac * wall_len), 2),
                }
            )
    return rows


def _fill_opening_widths(layout):
    for wall_name, sec in layout.wall_sections.items():
        wall_len = layout.wall_lengths_m[wall_name]
        for o in sec.openings:
            if o.width_m is None:
                if o.type == "door":
                    o.width_m = min(C.DOOR_WIDTH_M, wall_len * 0.35)
                else:
                    o.width_m = min(C.WINDOW_WIDTH_M, wall_len * 0.45)


def _build_result(job_id: str, layout, artifacts: PipelineArtifacts) -> dict:
    room_size_m = {
        "width": round(float(np.ptp(layout.pts_m[:, 0])), 2),
        "depth": round(float(np.ptp(layout.pts_m[:, 1])), 2),
        "area": round(float(_polygon_area(layout.pts_m)), 2),
        "scale_source": layout.scale_source,
    }

    result = PipelineResult(
        job_id=job_id,
        walls=4,
        openings=_serialize_openings(layout),
        furniture=_serialize_furniture(layout),
        room_size_m=room_size_m,
        wall_lengths_m={k: round(float(v), 2) for k, v in layout.wall_lengths_m.items()},
        artifacts=artifacts,
    )
    return result.to_dict()


def run_four_wall_pipeline(
    wall_inputs: list[WallImageInput],
    scale_hint: RoomScaleHint,
    job_id: str,
) -> dict:
    artifacts = build_artifacts(job_id)

    sections = {}
    for item in wall_inputs:
        sections[item.wall] = _estimate_wall_section(item, artifacts)

    missing = {"front", "right", "back", "left"} - set(sections.keys())
    if missing:
        raise ValueError(f"Missing wall images: {sorted(missing)}")

    layout = build_room_from_wall_sections(sections, scale_hint)

    sample_img_w = next(iter(sections.values())).width_px
    room_debug_path = artifacts.layout_debug_png
    room_debug_path.parent.mkdir(parents=True, exist_ok=True)
    save_layout_debug(layout, img_w=sample_img_w, out_path=room_debug_path)

    _fill_opening_widths(layout)

    render_floorplan_from_wall_sections(
        layout=layout,
        out_png=artifacts.floorplan_png,
        out_dxf=artifacts.floorplan_dxf,
        wall_thickness=C.WALL_THICKNESS,
        dxf_scale=C.DXF_SCALE,
    )

    return _build_result(job_id=job_id, layout=layout, artifacts=artifacts)