import io
from collections import defaultdict

import numpy as np
import requests
from PIL import Image

from api_endpoint import config_old as C
from ..geometry.angles import circular_delta, pano_x_to_angle
from ..geometry.raycast import find_hit_wall
from ..types_old import MappedOpening, OpeningCandidate, RawDetection


def map_rf_class(pred):
    cls_id = int(pred.get("class_id", -1))
    raw_class = str(pred.get("class", ""))
    return cls_id, C.RF_CLASS_MAP_ID.get(cls_id, f"class_{cls_id}"), raw_class


def box_iou(a, b):
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    ua = max(0.0, a.x2 - a.x1) * max(0.0, a.y2 - a.y1)
    ub = max(0.0, b.x2 - b.x1) * max(0.0, b.y2 - b.y1)
    return inter / (ua + ub - inter + 1e-6)


def nms(dets, iou_thresh=0.40, pano_w=None):
    if not dets:
        return []

    dets = sorted(dets, key=lambda d: d.conf, reverse=True)
    keep = []

    def variants(d):
        if pano_w is None or not d.wraps:
            return [d]
        a = RawDetection(**{**d.__dict__, "x1": d.x1 % pano_w, "x2": d.x2 % pano_w + pano_w})
        b = d
        c = RawDetection(**{**d.__dict__, "x1": d.x1 + pano_w, "x2": d.x2 + pano_w})
        return [a, b, c]

    def seam_iou(a, b):
        return max(box_iou(va, vb) for va in variants(a) for vb in variants(b))

    while dets:
        best = dets.pop(0)
        keep.append(best)
        dets = [d for d in dets if seam_iou(best, d) < iou_thresh]

    return keep


def normalize_pano_box(global_cx, global_cy, local_w, local_h, pano_w, pano_h):
    half_w = local_w / 2.0
    half_h = local_h / 2.0
    x1 = global_cx - half_w
    x2 = global_cx + half_w
    y1 = max(0.0, global_cy - half_h)
    y2 = min(float(pano_h), global_cy + half_h)
    wraps = (x1 < 0.0) or (x2 > pano_w)
    return x1, y1, x2, y2, wraps


def _is_plausible_opening(det: RawDetection, pano_w: int, pano_h: int) -> bool:
    rel_w = det.w / float(max(pano_w, 1))
    rel_h = det.h / float(max(pano_h, 1))
    rel_y = det.cy / float(max(pano_h, 1))
    aspect = det.w / max(det.h, 1e-6)

    if det.type == "door":
        if det.conf < C.DW_CLASS_CONF.get("door", C.CONF_THRESH):
            return False
        if rel_w < 0.03 or rel_w > 0.22:
            return False
        if rel_h < 0.18 or rel_h > 0.90:
            return False
        if aspect < 0.22 or aspect > 1.20:
            return False
        if rel_y < 0.18 or rel_y > 0.92:
            return False

    elif det.type == "window":
        if det.conf < C.DW_CLASS_CONF.get("window", C.CONF_THRESH):
            return False
        if rel_w < 0.04 or rel_w > 0.50:
            return False
        if rel_h < 0.10 or rel_h > 0.60:
            return False
        if aspect < 0.35 or aspect > 4.50:
            return False
        if rel_y < 0.12 or rel_y > 0.82:
            return False

    else:
        return False

    return True


def _filter_cross_class_conflicts(dets, pano_w):
    if not dets:
        return []

    dets = sorted(dets, key=lambda d: d.conf, reverse=True)
    kept = []

    for det in dets:
        suppress = False
        for prev in kept:
            overlap = box_iou(det, prev)
            if det.wraps or prev.wraps:
                overlap = max(
                    overlap,
                    max(
                        box_iou(a, b)
                        for a in (
                            [det]
                            if not det.wraps
                            else [
                                RawDetection(**{**det.__dict__, "x1": det.x1 % pano_w, "x2": det.x2 % pano_w + pano_w}),
                                det,
                                RawDetection(**{**det.__dict__, "x1": det.x1 + pano_w, "x2": det.x2 + pano_w}),
                            ]
                        )
                        for b in (
                            [prev]
                            if not prev.wraps
                            else [
                                RawDetection(**{**prev.__dict__, "x1": prev.x1 % pano_w, "x2": prev.x2 % pano_w + pano_w}),
                                prev,
                                RawDetection(**{**prev.__dict__, "x1": prev.x1 + pano_w, "x2": prev.x2 + pano_w}),
                            ]
                        )
                    ),
                )

            if overlap >= 0.55 and det.type != prev.type:
                suppress = True
                break

        if not suppress:
            kept.append(det)

    return kept


def detect_doors_windows(img_pil: Image.Image):
    if not C.ROBOFLOW_API_KEY:
        raise RuntimeError("ROBOFLOW_API_KEY is not set.")

    pano_w, pano_h = img_pil.size
    tile_step = C.TILE_W - C.OVERLAP
    tile_offsets = list(range(0, pano_w, tile_step))
    all_raw = []

    for ox in tile_offsets:
        if ox + C.TILE_W <= pano_w:
            tile_pil = img_pil.crop((ox, 0, ox + C.TILE_W, pano_h))
        else:
            right_part = img_pil.crop((ox, 0, pano_w, pano_h))
            left_w = C.TILE_W - (pano_w - ox)
            left_part = img_pil.crop((0, 0, left_w, pano_h))
            tile_pil = Image.new("RGB", (C.TILE_W, pano_h))
            tile_pil.paste(right_part, (0, 0))
            tile_pil.paste(left_part, (pano_w - ox, 0))

        buf = io.BytesIO()
        tile_pil.save(buf, format="JPEG", quality=95)
        buf.seek(0)

        resp = requests.post(
            C.ROBOFLOW_URL,
            params={
                "api_key": C.ROBOFLOW_API_KEY,
                "confidence": C.CONF_THRESH,
                "overlap": C.OVERLAP_THR,
                "format": "json",
            },
            files={"file": ("tile.jpg", buf, "image/jpeg")},
            timeout=(C.RF_CONNECT_TIMEOUT, C.RF_READ_TIMEOUT),
        )
        resp.raise_for_status()
        preds = resp.json().get("predictions", [])

        for p in preds:
            cls_id, cls_name, raw_class = map_rf_class(p)
            if cls_name not in {"door", "window"}:
                continue

            local_cx = float(p["x"])
            local_cy = float(p["y"])
            local_w = float(p["width"])
            local_h = float(p["height"])
            conf = float(p["confidence"])

            global_cx = (ox + local_cx) % pano_w
            x1, y1, x2, y2, wraps = normalize_pano_box(
                global_cx, local_cy, local_w, local_h, pano_w, pano_h
            )

            det = RawDetection(
                type=cls_name,
                label=cls_name.title(),
                conf=conf,
                x1=float(x1),
                y1=float(y1),
                x2=float(x2),
                y2=float(y2),
                cx=float(global_cx),
                cy=float(local_cy),
                w=float(local_w),
                h=float(local_h),
                raw_class=raw_class,
                class_id=cls_id,
                wraps=bool(wraps),
            )

            if not _is_plausible_opening(det, pano_w, pano_h):
                continue

            all_raw.append(det)

    all_raw = [d for d in all_raw if d.conf >= C.DW_CLASS_CONF.get(d.type, C.CONF_THRESH)]

    final = []
    for cls_name in sorted(set(d.type for d in all_raw)):
        cls_dets = [d for d in all_raw if d.type == cls_name]
        final.extend(nms(cls_dets, C.NMS_IOU, pano_w=pano_w))

    final = _filter_cross_class_conflicts(final, pano_w)
    final = sorted(final, key=lambda d: (-d.conf, d.type, d.cx))
    return final


def extract_layout_opening_candidates(layout, width):
    angles = np.sort((layout.corner_pixels / width) * 2 * np.pi)
    if len(angles) < 2:
        return []

    boundaries = np.r_[angles, angles[0] + 2 * np.pi]
    candidates = []

    for a1, a2 in zip(boundaries[:-1], boundaries[1:]):
        mid = ((a1 + a2) / 2.0) % (2 * np.pi)
        hit = find_hit_wall(layout.room_center, mid, layout.pts_m, layout.n_walls)
        if hit is None:
            continue
        _, frac, wall_i = hit
        candidates.append(OpeningCandidate(angle=mid, wall_i=wall_i, frac=frac))

    return candidates


def _estimate_opening_width_m(det, wall_len, cls, pano_w):
    rel_w = det.w / float(max(pano_w, 1))

    if cls == "door":
        base = max(0.70, min(1.20, rel_w * 6.0))
        base = max(base, C.DOOR_WIDTH_M * 0.85)
        base = min(base, C.DOOR_WIDTH_M * 1.25)
    else:
        base = max(0.60, min(2.40, rel_w * 8.0))
        base = max(base, C.WINDOW_WIDTH_M * 0.60)
        base = min(base, C.WINDOW_WIDTH_M * 1.60)

    return min(base, max(0.25, wall_len * 0.7))


def _is_geometry_plausible(det, cls, wall_len, best_frac):
    if not (0.02 <= best_frac <= 0.98):
        return False

    if cls == "door" and wall_len < 1.2:
        return False
    if cls == "window" and wall_len < 0.9:
        return False

    return True


def map_openings(dw_dets, layout, width, height):
    layout_candidates = extract_layout_opening_candidates(layout, width)
    mapped = []
    counts = defaultdict(int)
    wall_class_counts = defaultdict(int)
    neighborhood = np.radians(C.ALIGN_NEIGHBORHOOD_DEG)

    for det in sorted(dw_dets, key=lambda d: (-d.conf, d.type)):
        cls = det.type.lower()
        if cls not in {"door", "window"}:
            continue

        angle = pano_x_to_angle(det.cx, width)
        direct_hit = find_hit_wall(layout.room_center, angle, layout.pts_m, layout.n_walls)
        if direct_hit is None:
            continue

        _, direct_frac, direct_wall = direct_hit
        best_score = 1e9
        best_wall = direct_wall
        best_frac = direct_frac

        for cand in layout_candidates:
            delta = abs(circular_delta(angle, cand.angle))
            if delta > neighborhood:
                continue

            same_wall_penalty = 0.0 if cand.wall_i == direct_wall else 0.35
            vertical_penalty = (
                1.0 - min(max(det.cy / float(height), 0.0), 1.0)
            ) * C.ALIGN_VERTICAL_WEIGHT
            center_penalty = abs(cand.frac - direct_frac) * C.ALIGN_CENTER_PULL
            score = delta + same_wall_penalty + vertical_penalty + center_penalty

            if score < best_score:
                best_score = score
                best_wall = cand.wall_i
                best_frac = cand.frac

        p1 = layout.pts_m[best_wall]
        p2 = layout.pts_m[(best_wall + 1) % layout.n_walls]
        wall_vec = p2 - p1
        wall_len = np.linalg.norm(wall_vec)
        if wall_len < 1e-6:
            continue

        if not _is_geometry_plausible(det, cls, wall_len, best_frac):
            continue

        if cls == "door" and wall_class_counts[(best_wall, "door")] >= C.MAX_DOORS_PER_WALL:
            continue
        if cls == "window" and wall_class_counts[(best_wall, "window")] >= C.MAX_WINDOWS_PER_WALL:
            continue

        margin = min(C.OPENING_MIN_WALL_MARGIN, wall_len * 0.2)
        frac_margin = margin / wall_len
        best_frac = float(np.clip(best_frac, frac_margin, 1.0 - frac_margin))

        center_pt = p1 + best_frac * wall_vec
        wall_dir = wall_vec / wall_len
        normal = np.array([-wall_dir[1], wall_dir[0]])

        counts[cls] += 1
        wall_class_counts[(best_wall, cls)] += 1

        width_m = _estimate_opening_width_m(det, wall_len, cls, width)
        tag = f"{'D' if cls == 'door' else 'W'}{counts[cls]}"

        mapped.append(
            MappedOpening(
                type=cls,
                tag=tag,
                conf=det.conf,
                center=center_pt,
                wall_i=best_wall,
                frac=best_frac,
                wall_dir=wall_dir,
                normal=normal,
                width=width_m,
                wall_len=wall_len,
                p1=p1,
                p2=p2,
                raw_class=det.raw_class,
                class_id=det.class_id,
                angle=angle,
                pano_xy=[float(det.cx), float(det.cy)],
                direct_wall=direct_wall,
                direct_frac=float(direct_frac),
            )
        )

    return mapped