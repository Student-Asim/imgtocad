from pathlib import Path

import ezdxf
import numpy as np

from ..geometry.transforms import rot_rect


def export_dxf(
    layout,
    mapped_openings,
    mapped_furniture,
    out_dxf: Path,
    wall_thickness: float,
    dxf_scale: float,
):
    doc = ezdxf.new(dxfversion="R2010")

    layer_specs = [
        ("WALLS", 2, 50),
        ("DOORS", 1, 25),
        ("WINDOWS", 5, 25),
        ("LABELS", 4, 13),
        ("DIMS", 8, 13),
        ("FURNITURE", 7, 13),
    ]
    for name, color, lw in layer_specs:
        if name not in doc.layers:
            doc.layers.new(name, dxfattribs={"color": color, "lineweight": lw})

    msp = doc.modelspace()
    scale = dxf_scale
    n_walls = len(layout.pts_m)

    for furn in mapped_furniture:
        cp = np.asarray(furn.center, dtype=float) * scale
        w = float(furn.size[0]) * scale
        h = float(furn.size[1]) * scale

        if furn.type == "chair":
            msp.add_circle(
                (float(cp[0]), float(cp[1])),
                radius=float(min(w, h) * 0.33),
                dxfattribs={"layer": "FURNITURE"},
            )
        else:
            pts = rot_rect(np.array([0.0, 0.0]), w, h, float(furn.angle)) + cp
            pts = [(float(p[0]), float(p[1])) for p in pts]
            msp.add_lwpolyline(pts + [pts[0]], dxfattribs={"layer": "FURNITURE"})

        msp.add_text(
            str(furn.label),
            dxfattribs={"layer": "LABELS", "height": scale * 0.10},
        ).set_placement(
            (float(cp[0]), float(cp[1])),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER,
        )

    for i in range(n_walls):
        p1 = np.asarray(layout.pts_m[i], dtype=float) * scale
        p2 = np.asarray(layout.pts_m[(i + 1) % n_walls], dtype=float) * scale
        msp.add_line(
            (float(p1[0]), float(p1[1])),
            (float(p2[0]), float(p2[1])),
            dxfattribs={"layer": "WALLS", "lineweight": 50},
        )

    room_center = np.asarray(layout.room_center, dtype=float) * scale

    for i in range(n_walls):
        p1 = np.asarray(layout.pts_m[i], dtype=float) * scale
        p2 = np.asarray(layout.pts_m[(i + 1) % n_walls], dtype=float) * scale
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

        msp.add_line(
            (float(q1[0]), float(q1[1])),
            (float(q2[0]), float(q2[1])),
            dxfattribs={"layer": "DIMS"},
        )

    for op in mapped_openings:
        cp = np.asarray(op.center, dtype=float) * scale
        wall_dir = np.asarray(op.wall_dir, dtype=float)
        normal = np.asarray(op.normal, dtype=float)
        open_width = float(op.width) * scale
        half_width = open_width / 2.0
        open_start = cp - wall_dir * half_width
        open_end = cp + wall_dir * half_width

        if op.type == "door":
            msp.add_line(
                (float(open_start[0]), float(open_start[1])),
                (
                    float(open_start[0] + normal[0] * open_width),
                    float(open_start[1] + normal[1] * open_width),
                ),
                dxfattribs={"layer": "DOORS"},
            )

            ang0 = float(np.degrees(np.arctan2(wall_dir[1], wall_dir[0])))
            msp.add_arc(
                center=(float(open_start[0]), float(open_start[1]), 0.0),
                radius=float(open_width),
                start_angle=ang0,
                end_angle=float(ang0 + 90.0),
                dxfattribs={"layer": "DOORS"},
            )
        else:
            thickness = max(wall_thickness * scale, 0.18 * scale)
            for off in (-thickness / 2.0, 0.0, thickness / 2.0):
                msp.add_line(
                    (
                        float(open_start[0] + normal[0] * off),
                        float(open_start[1] + normal[1] * off),
                    ),
                    (
                        float(open_end[0] + normal[0] * off),
                        float(open_end[1] + normal[1] * off),
                    ),
                    dxfattribs={"layer": "WINDOWS"},
                )

        msp.add_text(
            str(op.tag),
            dxfattribs={"layer": "LABELS", "height": scale * 0.12},
        ).set_placement(
            (float(cp[0]), float(cp[1])),
            align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER,
        )

    doc.saveas(out_dxf)