from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from shapely.geometry import Polygon


@dataclass
class RawDetection:
    type: str
    label: str
    conf: float
    x1: float
    y1: float
    x2: float
    y2: float
    cx: float
    cy: float
    w: float
    h: float
    raw_class: str | None = None
    class_id: int | None = None
    area_px: float | None = None
    wraps: bool = False


@dataclass
class OpeningCandidate:
    angle: float
    wall_i: int
    frac: float


@dataclass
class MappedOpening:
    type: str
    tag: str
    conf: float
    center: np.ndarray
    wall_i: int
    frac: float
    wall_dir: np.ndarray
    normal: np.ndarray
    width: float
    wall_len: float
    p1: np.ndarray
    p2: np.ndarray
    raw_class: str | None = None
    class_id: int | None = None
    angle: float | None = None
    pano_xy: list[float] = field(default_factory=list)
    direct_wall: int | None = None
    direct_frac: float | None = None


@dataclass
class MappedFurniture:
    tag: str
    type: str
    label: str
    center: np.ndarray
    angle: float
    size: tuple[float, float]
    conf: float
    wall_i: int
    pano_xy: list[float]
    poly: Polygon


@dataclass
class RoomLayout:
    pts_m: np.ndarray
    n_walls: int
    room_center: np.ndarray
    corner_pixels: np.ndarray
    smooth: np.ndarray
    scale_m_per_unit: float = 1.0
    scale_source: str = "fallback"

@dataclass
class PipelineArtifacts:
    floorplan_png: Path
    floorplan_dxf: Path
    layout_debug_png: Path
    openings_debug_png: Path
    furniture_debug_png: Path


@dataclass
class PipelineResult:
    job_id: str
    walls: int
    doors: int
    windows: int
    openings: list[dict[str, Any]]
    furniture: list[dict[str, Any]]
    room_size_m: dict[str, float]
    artifacts: PipelineArtifacts

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "walls": self.walls,
            "doors": self.doors,
            "windows": self.windows,
            "openings": self.openings,
            "furniture": self.furniture,
            "room_size_m": self.room_size_m,
            "png_path": str(self.artifacts.floorplan_png),
            "dxf_path": str(self.artifacts.floorplan_dxf),
            "layout_debug_png_path": str(self.artifacts.layout_debug_png),
            "openings_debug_png_path": str(self.artifacts.openings_debug_png),
            "furniture_debug_png_path": str(self.artifacts.furniture_debug_png),
        }