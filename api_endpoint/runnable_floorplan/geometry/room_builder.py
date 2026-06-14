import numpy as np

from ..types import FourWallRoomLayout, RoomScaleHint, WallSection


WALL_ORDER = ["front", "right", "back", "left"]


def _mean_positive(values, default=1.0):
    vals = []
    for v in values:
        if v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv > 0:
            vals.append(fv)
    return sum(vals) / len(vals) if vals else float(default)


def _validate_sections(sections: dict[str, WallSection]) -> None:
    missing = [w for w in WALL_ORDER if w not in sections]
    if missing:
        raise ValueError(f"Missing wall sections: {missing}")

    for wall_name in WALL_ORDER:
        sec = sections[wall_name]
        if sec.estimated_length_units is None or float(sec.estimated_length_units) <= 0:
            raise ValueError(f"Invalid estimated_length_units for wall '{wall_name}'")


def estimate_wall_scale(section: WallSection, scale_hint: RoomScaleHint):
    if scale_hint.mode == "known_wall":
        if (
            scale_hint.reference_wall == section.wall
            and scale_hint.reference_wall_length_m is not None
            and float(scale_hint.reference_wall_length_m) > 0
            and float(section.estimated_length_units) > 1e-6
        ):
            scale = float(scale_hint.reference_wall_length_m) / float(section.estimated_length_units)
            return scale, f"known_wall:{section.wall}"

    if scale_hint.mode == "door_width":
        door_candidates = [
            o for o in section.openings
            if o.type == "door" and o.width_frac is not None and float(o.width_frac) > 1e-6
        ]
        if door_candidates:
            best = max(door_candidates, key=lambda o: o.conf)
            est_door_units = float(best.width_frac) * float(section.estimated_length_units)
            if est_door_units > 1e-6 and float(scale_hint.door_width_m) > 0:
                scale = float(scale_hint.door_width_m) / est_door_units
                return scale, f"door_width:{section.wall}:{best.tag}"

    return None, "unscaled"


def _resolve_global_scale(sections: dict[str, WallSection], scale_hint: RoomScaleHint):
    scales = []
    sources = []

    for wall_name in WALL_ORDER:
        sec = sections[wall_name]
        scale, source = estimate_wall_scale(sec, scale_hint)
        if scale is not None and scale > 0:
            sec.scale_m_per_unit = float(scale)
            sec.scale_source = source
            scales.append(float(scale))
            sources.append(source)

    if scales:
        return float(sum(scales) / len(scales)), "avg(" + ",".join(sources) + ")"

    if (
        scale_hint.fallback_room_width_m is not None
        and scale_hint.fallback_room_depth_m is not None
        and float(scale_hint.fallback_room_width_m) > 0
        and float(scale_hint.fallback_room_depth_m) > 0
    ):
        front = sections["front"]
        back = sections["back"]
        right = sections["right"]
        left = sections["left"]

        width_units = _mean_positive(
            [front.estimated_length_units, back.estimated_length_units],
            default=1.0,
        )
        depth_units = _mean_positive(
            [right.estimated_length_units, left.estimated_length_units],
            default=1.0,
        )

        sx = float(scale_hint.fallback_room_width_m) / width_units
        sy = float(scale_hint.fallback_room_depth_m) / depth_units
        return float((sx + sy) / 2.0), "manual_room"

    return 1.0, "unscaled"


def _estimate_room_dimensions(sections: dict[str, WallSection], global_scale: float):
    front = sections["front"]
    back = sections["back"]
    right = sections["right"]
    left = sections["left"]

    width_m = _mean_positive(
        [
            float(front.estimated_length_units) * global_scale,
            float(back.estimated_length_units) * global_scale,
        ],
        default=4.0,
    )

    depth_m = _mean_positive(
        [
            float(right.estimated_length_units) * global_scale,
            float(left.estimated_length_units) * global_scale,
        ],
        default=4.0,
    )

    width_m = max(width_m, 1.5)
    depth_m = max(depth_m, 1.5)
    return float(width_m), float(depth_m)


def _build_rectangle(width_m: float, depth_m: float):
    return np.array(
        [
            [0.0, 0.0],
            [width_m, 0.0],
            [width_m, depth_m],
            [0.0, depth_m],
        ],
        dtype=float,
    )


def build_room_from_wall_sections(
    sections: dict[str, WallSection],
    scale_hint: RoomScaleHint,
) -> FourWallRoomLayout:
    _validate_sections(sections)

    global_scale, scale_source = _resolve_global_scale(sections, scale_hint)
    width_m, depth_m = _estimate_room_dimensions(sections, global_scale)
    pts_m = _build_rectangle(width_m, depth_m)

    wall_lengths_m = {
        "front": width_m,
        "right": depth_m,
        "back": width_m,
        "left": depth_m,
    }

    room_center = pts_m.mean(axis=0)

    return FourWallRoomLayout(
        pts_m=pts_m,
        n_walls=len(pts_m),
        wall_order=WALL_ORDER.copy(),
        wall_lengths_m=wall_lengths_m,
        room_center=room_center,
        scale_source=scale_source,
        wall_sections=sections,
    )