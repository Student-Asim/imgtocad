from pathlib import Path

import ezdxf
import numpy as np

from ..geometry.transforms import rot_rect


def export_dxf(layout, mapped_openings, mapped_furniture, out_dxf: Path, wall_thickness: float, dxf_scale: float):
    doc = ezdxf.new(dxfversion="R2010")
    for name, color, lw in [("WALLS", 2, 50), ("DOORS", 1, 25), ("WINDOWS", 5, 25), ("LABELS", 4, 13), ("DIMS", 8, 13), ("FURNITURE", 7, 13)]:
        if name not in doc.layers:
            doc.layers.new(name, dxfattribs={"color": color, "lineweight": lw})
    msp = doc.modelspace()
    scale = dxf_scale
    for furn in mapped_furniture:
        cp = np.asarray(furn.center) * scale
        w, h = furn.size[0] * scale, furn.size[1] * scale
        if furn.type == "chair":
            msp.add_circle((cp[0], cp[1]), radius=min(w, h) * 0.33, dxfattribs={"layer": "FURNITURE"})
        else:
            pts = rot_rect(np.array([0.0, 0.0]), w, h, furn.angle) + cp
            pts = [(float(p[0]), float(p[1])) for p in pts]
            msp.add_lwpolyline(pts + [pts[0]], dxfattribs={"layer": "FURNITURE"})
        msp.add_text(furn.label, dxfattribs={"layer": "LABELS", "height": scale * 0.10}).set_placement((cp[0], cp[1]), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    for i in range(layout.n_walls):
        p1 = layout.pts_m[i] * scale
        p2 = layout.pts_m[(i + 1) % layout.n_walls] * scale
        msp.add_line((p1[0], p1[1]), (p2[0], p2[1]), dxfattribs={"layer": "WALLS", "lineweight": 50})
    room_center = layout.room_center * scale
    for i in range(layout.n_walls):
        p1 = layout.pts_m[i] * scale
        p2 = layout.pts_m[(i + 1) % layout.n_walls] * scale
        vec = p2 - p1
        wall_len = np.linalg.norm(vec)
        if wall_len < 1e-6:
            continue
        wall_dir = vec / wall_len
        normal = np.array([-wall_dir[1], wall_dir[0]], dtype=float)
        mid = (p1 + p2) / 2.0
        if np.dot(normal, room_center - mid) > 0:
            normal = -normal
        offset = 0.28 * scale
        q1 = p1 + normal * offset
        q2 = p2 + normal * offset
        msp.add_line((q1[0], q1[1]), (q2[0], q2[1]), dxfattribs={"layer": "DIMS"})
    for op in mapped_openings:
        cp = op.center * scale
        wall_dir = op.wall_dir
        normal = op.normal
        open_width = op.width * scale
        half_width = open_width / 2.0
        open_start = cp - wall_dir * half_width
        open_end = cp + wall_dir * half_width
        if op.type == "door":
            msp.add_line((open_start[0], open_start[1]), (open_start[0] + normal[0] * open_width, open_start[1] + normal[1] * open_width), dxfattribs={"layer": "DOORS"})
            ang0 = np.degrees(np.arctan2(wall_dir[1], wall_dir[0]))
            msp.add_arc((open_start[0], open_start[1], 0), open_width, ang0, ang0 + 90, dxfattribs={"layer": "DOORS"})
        else:
            thickness = max(wall_thickness * scale, 0.18 * scale)
            for off in (-thickness / 2.0, 0.0, thickness / 2.0):
                msp.add_line((open_start[0] + normal[0] * off, open_start[1] + normal[1] * off), (open_end[0] + normal[0] * off, open_end[1] + normal[1] * off), dxfattribs={"layer": "WINDOWS"})
        msp.add_text(op.tag, dxfattribs={"layer": "LABELS", "height": scale * 0.12}).set_placement((cp[0], cp[1]), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    doc.saveas(str(out_dxf))