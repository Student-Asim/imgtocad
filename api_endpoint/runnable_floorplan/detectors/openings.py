import io

import requests
from PIL import Image

from api_endpoint import config as C
from ..types import RawDetection


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


def nms(dets, iou_thresh=0.40):
    if not dets:
        return []

    dets = sorted(dets, key=lambda d: d.conf, reverse=True)
    keep = []

    while dets:
        best = dets.pop(0)
        keep.append(best)
        dets = [d for d in dets if box_iou(best, d) < iou_thresh]

    return keep


def _is_plausible_opening(det: RawDetection, img_w: int, img_h: int) -> bool:
    rel_w = det.w / float(max(img_w, 1))
    rel_h = det.h / float(max(img_h, 1))
    rel_y = det.cy / float(max(img_h, 1))
    aspect = det.w / max(det.h, 1e-6)

    if det.type == "door":
        if det.conf < C.DW_CLASS_CONF.get("door", C.CONF_THRESH):
            return False
        if rel_w < 0.03 or rel_w > 0.30:
            return False
        if rel_h < 0.18 or rel_h > 0.95:
            return False
        if aspect < 0.20 or aspect > 1.30:
            return False
        if rel_y < 0.15 or rel_y > 0.95:
            return False

    elif det.type == "window":
        if det.conf < C.DW_CLASS_CONF.get("window", C.CONF_THRESH):
            return False
        if rel_w < 0.04 or rel_w > 0.60:
            return False
        if rel_h < 0.08 or rel_h > 0.70:
            return False
        if aspect < 0.30 or aspect > 5.00:
            return False
        if rel_y < 0.10 or rel_y > 0.85:
            return False

    else:
        return False

    return True


def detect_doors_windows(img_pil: Image.Image):
    if not C.ROBOFLOW_API_KEY:
        raise RuntimeError("ROBOFLOW_API_KEY is not set.")

    img_w, img_h = img_pil.size

    buf = io.BytesIO()
    img_pil.save(buf, format="JPEG", quality=95)
    buf.seek(0)

    resp = requests.post(
        C.ROBOFLOW_URL,
        params={
            "api_key": C.ROBOFLOW_API_KEY,
            "confidence": C.CONF_THRESH,
            "overlap": C.OVERLAP_THR,
            "format": "json",
        },
        files={"file": ("wall.jpg", buf, "image/jpeg")},
        timeout=(C.RF_CONNECT_TIMEOUT, C.RF_READ_TIMEOUT),
    )
    resp.raise_for_status()

    preds = resp.json().get("predictions", [])
    all_raw = []

    for p in preds:
        cls_id, cls_name, raw_class = map_rf_class(p)
        if cls_name not in {"door", "window"}:
            continue

        cx = float(p["x"])
        cy = float(p["y"])
        w = float(p["width"])
        h = float(p["height"])
        conf = float(p["confidence"])
        x1 = cx - w / 2.0
        x2 = cx + w / 2.0
        y1 = cy - h / 2.0
        y2 = cy + h / 2.0

        det = RawDetection(
            type=cls_name,
            label=cls_name.title(),
            conf=conf,
            x1=float(x1),
            y1=float(y1),
            x2=float(x2),
            y2=float(y2),
            cx=float(cx),
            cy=float(cy),
            w=float(w),
            h=float(h),
            raw_class=raw_class,
            class_id=cls_id,
        )

        if not _is_plausible_opening(det, img_w, img_h):
            continue

        all_raw.append(det)

    final = []
    for cls_name in sorted(set(d.type for d in all_raw)):
        cls_dets = [d for d in all_raw if d.type == cls_name]
        final.extend(nms(cls_dets, C.NMS_IOU))

    return sorted(final, key=lambda d: (-d.conf, d.type, d.cx))