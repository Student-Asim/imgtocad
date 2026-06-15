import numpy as np

from api_endpoint import config as C
from ..types_old import RawDetection


def detect_furniture(registry, img_pil):
    if registry.furniture_model is None:
        raise RuntimeError("Furniture model not loaded.")
    img_np = np.array(img_pil)
    results = registry.furniture_model.predict(
        source=img_np,
        conf=min(C.FURNITURE_CONF, 0.10),
        imgsz=getattr(C, "FURNITURE_IMGSZ", 1024),
        verbose=False,
    )
    class_conf = getattr(C, "FURNITURE_CLASS_CONF", {
        "bed": 0.18,
        "chair": 0.10,
        "sofa": 0.14,
        "couch": 0.14,
        "dining table": 0.12,
        "bench": 0.12,
        "tv": 0.12,
    })
    dets = []
    for r in results:
        names = r.names
        if r.boxes is None:
            continue
        for b in r.boxes:
            cls_id = int(b.cls.item())
            cls_name = names.get(cls_id, str(cls_id))
            mapped_name = C.FURNITURE_CLASSES.get(cls_name)
            if mapped_name is None:
                continue
            conf = float(b.conf.item())
            min_conf = class_conf.get(cls_name, C.FURNITURE_CONF)
            if conf < min_conf:
                continue
            x1, y1, x2, y2 = b.xyxy[0].cpu().numpy().tolist()
            dets.append(RawDetection(
                type=mapped_name,
                label=mapped_name.title(),
                raw_class=cls_name,
                conf=conf,
                x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2),
                cx=float((x1 + x2) / 2.0), cy=float((y1 + y2) / 2.0),
                w=float(x2 - x1), h=float(y2 - y1),
                area_px=float((x2 - x1) * (y2 - y1)),
            ))
    return sorted(dets, key=lambda d: d.conf, reverse=True)