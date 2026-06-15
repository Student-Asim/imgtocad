from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
from shapely.geometry import Polygon

WallName = Literal["front", "right", "back", "left"]


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
class WallImageInput:
    wall: WallName
    image_bytes: bytes
    image_name: str
    known_length_m: float | None = None


@dataclass
class WallOpening:
    wall: WallName
    type: str
    tag: str
    conf: float
    frac: float
    width_frac: float
    center_px: tuple[float, float]
    width_m: float | None = None


@dataclass
class WallFurniture:
    wall: WallName
    tag: str
    type: str
    label: str
    conf: float
    frac: float
    center_px: tuple[float, float]
    size_m: tuple[float, float] | None = None


@dataclass
class WallSection:
    wall: WallName
    width_px: int
    height_px: int
    estimated_length_units: float
    estimated_depth_score: float = 0.0
    openings: list[WallOpening] = field(default_factory=list)
    furniture: list[WallFurniture] = field(default_factory=list)
    scale_m_per_unit: float | None = None
    scale_source: str = "unscaled"


@dataclass
class RoomScaleHint:
    mode: str = "door_width"
    door_width_m: float = 0.90
    reference_wall: WallName | None = None
    reference_wall_length_m: float | None = None
    fallback_room_width_m: float | None = None
    fallback_room_depth_m: float | None = None


@dataclass
class FourWallRoomLayout:
    pts_m: np.ndarray
    n_walls: int
    wall_order: list[WallName]
    wall_lengths_m: dict[WallName, float]
    room_center: np.ndarray
    scale_source: str
    wall_sections: dict[WallName, WallSection]


@dataclass
class PipelineArtifacts:
    floorplan_png: Path
    floorplan_dxf: Path
    debug_dir: Path
    layout_debug_png: Path | None = None
    openings_debug_png: Path | None = None
    furniture_debug_png: Path | None = None


@dataclass
class PipelineResult:
    job_id: str
    walls: int
    openings: list[dict[str, Any]]
    furniture: list[dict[str, Any]]
    room_size_m: dict[str, float]
    wall_lengths_m: dict[str, float]
    artifacts: PipelineArtifacts

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "walls": self.walls,
            "openings": self.openings,
            "furniture": self.furniture,
            "room_size_m": self.room_size_m,
            "wall_lengths_m": self.wall_lengths_m,
            "png_path": str(self.artifacts.floorplan_png),
            "dxf_path": str(self.artifacts.floorplan_dxf),
            "debug_dir": str(self.artifacts.debug_dir),
            "layout_debug_png_path": str(self.artifacts.layout_debug_png) if self.artifacts.layout_debug_png else None,
            "openings_debug_png_path": str(self.artifacts.openings_debug_png) if self.artifacts.openings_debug_png else None,
            "furniture_debug_png_path": str(self.artifacts.furniture_debug_png) if self.artifacts.furniture_debug_png else None,
        }