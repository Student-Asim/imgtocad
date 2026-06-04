from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ..exporters.dxf_exporter import export_dxf
from ..geometry.transforms import rot_points, rot_rect


def draw_wall_segment(ax, p1, p2, openings, wall_thickness):
    vec = p2 - p1
    length = np.linalg.norm(vec)
    if length < 1e-6:
        return
    wall_dir = vec / length
    normal = np.array([-wall_dir[1], wall_dir[0]], dtype=float)
    cuts = sorted((np.clip(op.frac - op.width / 2 / length, 0.0, 1.0), np.clip(op.frac + op.width / 2 / length, 0.0, 1.0)) for op in openings)
    segments = []
    prev = 0.0
    for cut_start, cut_end in cuts:
        if cut_start > prev:
            segments.append((prev, cut_start))
        prev = max(prev, cut_end)
    if prev < 1.0:
        segments.append((prev, 1.0))
    for start, end in segments:
        if end - start < 1e-3:
            continue
        sp = p1 + start * vec
        ep = p1 + end * vec
        poly = np.array([sp + normal * wall_thickness / 2, ep + normal * wall_thickness / 2, ep - normal * wall_thickness / 2, sp - normal * wall_thickness / 2])
        ax.add_patch(plt.Polygon(poly, closed=True, fc="black", ec="black", lw=0.5, joinstyle="miter", zorder=3))


def draw_door(ax, op):
    cut_start = np.clip(op.frac - op.width / 2 / op.wall_len, 0.0, 1.0)
    cut_end = np.clip(op.frac + op.width / 2 / op.wall_len, 0.0, 1.0)
    open_start = op.p1 + cut_start * (op.p2 - op.p1)
    open_end = op.p1 + cut_end * (op.p2 - op.p1)
    open_width = np.linalg.norm(open_end - open_start)
    if open_width < 1e-6:
        return
    hinge = open_start
    closed_tip = open_end
    open_tip = hinge + op.normal * open_width
    ax.plot([hinge[0], closed_tip[0]], [hinge[1], closed_tip[1]], color="#b8b8b8", lw=0.9, ls="-", zorder=5)
    ax.plot([hinge[0], open_tip[0]], [hinge[1], open_tip[1]], color="#2d2d2d", lw=1.5, solid_capstyle="round", zorder=7)
    ax.scatter([hinge[0]], [hinge[1]], s=10, c="#2d2d2d", zorder=8)
    base = np.arctan2(op.wall_dir[1], op.wall_dir[0])
    theta = np.linspace(0, np.pi / 2, 80)
    arc = np.c_[hinge[0] + np.cos(base + theta) * open_width, hinge[1] + np.sin(base + theta) * open_width]
    ax.plot(arc[:, 0], arc[:, 1], color="#6f6f6f", lw=1.0, ls="-", zorder=6)


def draw_window(ax, op, wall_thickness):
    cut_start = np.clip(op.frac - op.width / 2 / op.wall_len, 0.0, 1.0)
    cut_end = np.clip(op.frac + op.width / 2 / op.wall_len, 0.0, 1.0)
    open_start = op.p1 + cut_start * (op.p2 - op.p1)
    open_end = op.p1 + cut_end * (op.p2 - op.p1)
    depth = wall_thickness * 0.42
    cap = wall_thickness * 0.18
    for off in (-depth, depth):
        wx1 = open_start + op.normal * off
        wx2 = open_end + op.normal * off
        ax.plot([wx1[0], wx2[0]], [wx1[1], wx2[1]], color="white", lw=2.1, solid_capstyle="butt", zorder=6)
    ax.plot([open_start[0], open_end[0]], [open_start[1], open_end[1]], color="#222222", lw=0.9, solid_capstyle="butt", zorder=7)
    for pt in (open_start, open_end):
        c1 = pt - op.normal * cap
        c2 = pt + op.normal * cap
        ax.plot([c1[0], c2[0]], [c1[1], c2[1]], color="#222222", lw=0.9, zorder=7)


def draw_furniture(ax, furn):
    t = furn.type
    center = np.asarray(furn.center, dtype=float)
    angle = furn.angle
    w, h = furn.size
    label = furn.label.lower()
    edge = "#8a8a8a"
    edge_dark = "#666666"
    fill_mid = "#dddddd"
    if t == "bed":
        frame = rot_rect(center, w, h, angle)
        ax.add_patch(plt.Polygon(frame, closed=True, fc="#f3f3f3", ec=edge_dark, lw=0.9, zorder=2))
        mattress_center = rot_points(np.array([[0.0, -h * 0.01]]), angle)[0] + center
        mattress = rot_rect(mattress_center, w * 0.90, h * 0.88, angle)
        ax.add_patch(plt.Polygon(mattress, closed=True, fc="#fbfbfb", ec=edge, lw=0.5, zorder=3))
    elif t == "chair":
        seat_w = w * 0.62
        seat_h = h * 0.62
        seat = rot_rect(center, seat_w, seat_h, angle)
        ax.add_patch(plt.Polygon(seat, closed=True, fc="#f8f8f8", ec=edge_dark, lw=0.75, zorder=3))
    elif t == "table":
        rect = rot_rect(center, w, h, angle)
        ax.add_patch(plt.Polygon(rect, closed=True, fc="#f4f4f4", ec=edge_dark, lw=0.9, zorder=2))
    else:
        rect = rot_rect(center, w, h, angle)
        ax.add_patch(plt.Polygon(rect, closed=True, fc=fill_mid, ec=edge_dark, lw=0.9, zorder=2))
    ax.text(center[0], center[1] - max(h, w) * 0.42, label, fontsize=7, color="#303030", ha="center", va="top", zorder=8, bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="none", alpha=0.80))


def draw_dimension(ax, p1, p2, room_center, text):
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)
    room_center = np.asarray(room_center, dtype=float)
    mid = (p1 + p2) / 2.0
    wall_vec = p2 - p1
    wall_len = np.linalg.norm(wall_vec)
    if wall_len < 1e-6:
        return
    wall_dir = wall_vec / wall_len
    normal = np.array([-wall_dir[1], wall_dir[0]], dtype=float)
    if np.dot(normal, mid - room_center) < 0:
        normal = -normal
    offset = 0.22
    tick = 0.08
    dp1 = p1 + normal * offset
    dp2 = p2 + normal * offset
    tm = mid + normal * (offset + 0.02)
    ax.plot([p1[0], dp1[0]], [p1[1], dp1[1]], color="#7a7a7a", lw=0.6, zorder=6)
    ax.plot([p2[0], dp2[0]], [p2[1], dp2[1]], color="#7a7a7a", lw=0.6, zorder=6)
    ax.plot([dp1[0], dp2[0]], [dp1[1], dp2[1]], color="#7a7a7a", lw=0.8, zorder=6)
    t1a = dp1 - wall_dir * tick / 2
    t1b = dp1 + wall_dir * tick / 2
    t2a = dp2 - wall_dir * tick / 2
    t2b = dp2 + wall_dir * tick / 2
    ax.plot([t1a[0], t1b[0]], [t1a[1], t1b[1]], color="#7a7a7a", lw=0.8, zorder=6)
    ax.plot([t2a[0], t2b[0]], [t2a[1], t2b[1]], color="#7a7a7a", lw=0.8, zorder=6)
    ax.text(tm[0], tm[1], text, fontsize=8, color="#444444", ha="center", va="center", zorder=7, bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))


def render_floorplan(layout, mapped_openings, mapped_furniture, out_png: Path, out_dxf: Path, wall_thickness: float, dxf_scale: float):
    pts_m = layout.pts_m
    pad = 0.95
    xlim = (pts_m[:, 0].min() - pad, pts_m[:, 0].max() + pad)
    ylim = (pts_m[:, 1].min() - pad, pts_m[:, 1].max() + pad)
    fig, ax = plt.subplots(figsize=(8.5, 8.5), facecolor="white")
    ax.set_facecolor("white")
    ax.add_patch(plt.Polygon(pts_m, closed=True, fc="#f2f2ef", ec="none", zorder=1))
    for furn in mapped_furniture:
        draw_furniture(ax, furn)
    openings_by_wall = defaultdict(list)
    for op in mapped_openings:
        openings_by_wall[op.wall_i].append(op)
    for i in range(layout.n_walls):
        draw_wall_segment(ax, pts_m[i], pts_m[(i + 1) % layout.n_walls], openings_by_wall[i], wall_thickness)
    ax.add_patch(plt.Polygon(pts_m, closed=True, fill=False, edgecolor="black", linewidth=2.2, joinstyle="miter", zorder=4))
    for op in mapped_openings:
        if op.type == "door":
            draw_door(ax, op)
        else:
            draw_window(ax, op, wall_thickness)
    room_area = 0.5 * abs(np.dot(pts_m[:, 0], np.roll(pts_m[:, 1], -1)) - np.dot(pts_m[:, 1], np.roll(pts_m[:, 0], -1)))
    for i in range(layout.n_walls):
        p1 = pts_m[i]
        p2 = pts_m[(i + 1) % layout.n_walls]
        wall_len = np.linalg.norm(p2 - p1)
        draw_dimension(ax, p1, p2, layout.room_center, f"{wall_len:.2f} m")
    ax.text(layout.room_center[0], layout.room_center[1], f"Room\n{room_area:.2f} sq m", ha="center", va="center", fontsize=11, color="#2b2b2b", zorder=6, bbox=dict(boxstyle="round,pad=0.30", fc=(1, 1, 1, 0.82), ec="none"))
    for op in mapped_openings:
        cp = op.center
        ax.text(cp[0], cp[1], op.tag, fontsize=7, color="#202020", ha="center", va="center", zorder=8, bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.90))
    ax.set_aspect("equal")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.tight_layout()
    fig.savefig(str(out_png), dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    export_dxf(layout, mapped_openings, mapped_furniture, out_dxf, wall_thickness, dxf_scale)