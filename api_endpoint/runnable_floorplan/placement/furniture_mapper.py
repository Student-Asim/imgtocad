import logging

import numpy as np
from shapely.geometry import Point, Polygon

from api_endpoint import config_old as C
from ..geometry.angles import pano_x_to_angle
from ..geometry.raycast import find_hit_wall
from ..geometry.transforms import rot_rect
from ..types_old import MappedFurniture

log = logging.getLogger("pipeline")


def furniture_size_m(furn_type, room_w, room_h):
    base = {
        "bed": (1.55, 1.15),
        "sofa": (1.15, 0.65),
        "table": (0.85, 0.55),
        "chair": (0.40, 0.40),
    }.get(furn_type, (0.60, 0.50))
    max_w = room_w * 0.35
    max_h = room_h * 0.26
    w = min(base[0], max_w)
    h = min(base[1], max_h)
    if furn_type == "chair":
        w = min(w, room_w * 0.12)
        h = min(h, room_h * 0.12)
    elif furn_type == "table":
        w = min(w, room_w * 0.22)
        h = min(h, room_h * 0.18)
    elif furn_type == "sofa":
        w = min(w, room_w * 0.28)
        h = min(h, room_h * 0.18)
    elif furn_type == "bed":
        w = min(w, room_w * 0.32)
        h = min(h, room_h * 0.24)
    return (max(w, 0.28), max(h, 0.28))


def opening_rect(op, pad=0.04):
    cp = np.asarray(op.center, dtype=float)
    w = float(op.width) + pad
    h = max(C.WALL_THICKNESS * 1.35, 0.18)
    ang = float(np.arctan2(op.wall_dir[1], op.wall_dir[0]))
    return rot_rect(cp, w, h, ang)


def furniture_polygon(center, size, angle):
    return Polygon(rot_rect(center, size[0], size[1], angle))


def inside_room(center, size, angle, room_poly, wall_gap=0.04):
    poly = furniture_polygon(center, size, angle)
    inner = room_poly.buffer(-wall_gap)
    if inner.is_empty:
        inner = room_poly
    return inner.covers(poly)


def overlaps_existing(center, size, angle, placed_furniture, opening_polys, gap=0.03):
    poly = furniture_polygon(center, size, angle).buffer(gap)
    for fp in placed_furniture:
        if poly.intersects(fp.poly.buffer(gap)):
            return True
    for op in opening_polys:
        if poly.intersects(op.buffer(gap)):
            return True
    return False


def find_valid_furniture_placement(base_center, size, angle, room_poly, placed_furniture, opening_polys):
    scales = [1.00, 0.90, 0.80, 0.70, 0.60, 0.50]
    offsets = [
        (0.0, 0.0), (0.10, 0.0), (-0.10, 0.0), (0.0, 0.10), (0.0, -0.10),
        (0.18, 0.0), (-0.18, 0.0), (0.0, 0.18), (0.0, -0.18),
        (0.25, 0.0), (-0.25, 0.0), (0.0, 0.25), (0.0, -0.25),
        (0.15, 0.15), (-0.15, 0.15), (0.15, -0.15), (-0.15, -0.15),
        (0.30, 0.15), (-0.30, 0.15), (0.30, -0.15), (-0.30, -0.15),
    ]
    for scale in scales:
        test_size = (size[0] * scale, size[1] * scale)
        for dx, dy in offsets:
            center = np.array([base_center[0] + dx, base_center[1] + dy], dtype=float)
            if not inside_room(center, test_size, angle, room_poly):
                continue
            if overlaps_existing(center, test_size, angle, placed_furniture, opening_polys):
                continue
            return center, test_size
    return None, None


def map_furniture(furniture_dets, layout, img_w, img_h, mapped_openings):
    mapped = []
    room_poly = Polygon(layout.pts_m)
    opening_polys = [Polygon(opening_rect(op)) for op in mapped_openings]
    room_w = float(np.ptp(layout.pts_m[:, 0]))
    room_h = float(np.ptp(layout.pts_m[:, 1]))
    for i, det in enumerate(sorted(furniture_dets, key=lambda d: -d.conf), start=1):
        angle = pano_x_to_angle(det.cx, img_w)
        hit = find_hit_wall(layout.room_center, angle, layout.pts_m, layout.n_walls)
        if hit is None:
            log.info("skip furniture %s: no wall hit", det.label)
            continue
        _, frac, wall_i = hit
        p1 = layout.pts_m[wall_i]
        p2 = layout.pts_m[(wall_i + 1) % layout.n_walls]
        wall_vec = p2 - p1
        wall_len = np.linalg.norm(wall_vec)
        if wall_len < 1e-6:
            log.info("skip furniture %s: tiny wall", det.label)
            continue
        frac = float(np.clip(frac, 0.12, 0.88))
        wall_dir = wall_vec / wall_len
        normal = np.array([-wall_dir[1], wall_dir[0]], dtype=float)
        probe = p1 + frac * wall_vec + normal * 0.30
        if not room_poly.covers(Point(probe[0], probe[1])):
            normal = -normal
        size = furniture_size_m(det.type, room_w, room_h)
        rel_y = np.clip(det.cy / float(img_h), 0.05, 0.98)
        inward_offset = 0.35 + (1.0 - rel_y) * 0.55
        if det.type == "chair":
            inward_offset *= 0.75
        elif det.type == "table":
            inward_offset *= 0.85
        elif det.type == "bed":
            inward_offset *= 1.05
        base_center = p1 + frac * wall_vec + normal * inward_offset
        furn_angle = float(np.arctan2(wall_dir[1], wall_dir[0]))
        center, final_size = find_valid_furniture_placement(base_center, size, furn_angle, room_poly, mapped, opening_polys)
        if center is None:
            log.info("skip furniture %s: no valid placement, conf=%.3f", det.label, det.conf)
            continue
        poly = furniture_polygon(center, final_size, furn_angle)
        mapped.append(MappedFurniture(
            tag=f"F{i}",
            type=det.type,
            label=det.label,
            center=center,
            angle=furn_angle,
            size=final_size,
            conf=float(det.conf),
            wall_i=int(wall_i),
            pano_xy=[float(det.cx), float(det.cy)],
            poly=poly,
        ))
    return mapped