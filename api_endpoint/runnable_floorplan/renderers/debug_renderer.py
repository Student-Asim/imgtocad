from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np

from ..geometry.angles import pano_x_to_angle


def save_layout_debug(layout, img_w, out_path: Path):
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.add_patch(plt.Polygon(layout.pts_m, closed=True, fill=False, edgecolor="black", linewidth=2.0))
    ax.scatter(layout.pts_m[:, 0], layout.pts_m[:, 1], s=40, c="red", zorder=3)
    ax.scatter(layout.room_center[0], layout.room_center[1], s=50, c="blue", zorder=3)
    for idx, px in enumerate(layout.corner_pixels):
        ang = pano_x_to_angle(px, img_w)
        ray = layout.room_center + np.array([np.cos(ang), np.sin(ang)]) * 1.4
        ax.plot([layout.room_center[0], ray[0]], [layout.room_center[1], ray[1]], "--", color="#b0b0b0", lw=1)
        ax.text(ray[0], ray[1], f"C{idx + 1}", fontsize=8)
    ax.set_aspect("equal")
    ax.set_title("HorizonNet polygon layout")
    ax.grid(True, alpha=0.3)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_openings_debug_overlay(img_np, mapped_openings, out_path: Path):
    vis = img_np.copy()
    h, w = vis.shape[:2]
    colors = {"door": (40, 80, 230), "window": (30, 170, 220)}
    for op in mapped_openings:
        x = int(np.clip(op.pano_xy[0], 0, w - 1))
        y = int(np.clip(op.pano_xy[1], 0, h - 1))
        color = colors.get(op.type, (0, 255, 255))
        cv2.circle(vis, (x, y), 7, color, -1)
        cv2.putText(vis, f"{op.tag} {op.type} -> wall {op.wall_i + 1} {op.frac:.2f}", (max(8, x + 8), max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    cv2.imwrite(str(out_path), vis)


def save_furniture_debug_overlay(img_np, furniture_dets, out_path: Path):
    vis = img_np.copy()
    h, w = vis.shape[:2]
    colors = {"bed": (120, 80, 220), "sofa": (50, 170, 90), "table": (220, 140, 40), "chair": (200, 80, 80)}
    for det in furniture_dets:
        x1 = int(np.clip(det.x1, 0, w - 1))
        y1 = int(np.clip(det.y1, 0, h - 1))
        x2 = int(np.clip(det.x2, 0, w - 1))
        y2 = int(np.clip(det.y2, 0, h - 1))
        color = colors.get(det.type, (180, 180, 80))
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        cv2.circle(vis, (int(det.cx), int(det.cy)), 4, color, -1)
        cv2.putText(vis, f"{det.label} {det.conf:.2f}", (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
    cv2.imwrite(str(out_path), vis)