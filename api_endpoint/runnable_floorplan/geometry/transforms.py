import numpy as np


def rot_points(points, angle):
    c, s = np.cos(angle), np.sin(angle)
    rot = np.array([[c, -s], [s, c]])
    return points @ rot.T


def rot_rect(center, w, h, angle):
    pts = np.array([
        [-w / 2, -h / 2],
        [w / 2, -h / 2],
        [w / 2, h / 2],
        [-w / 2, h / 2],
    ], dtype=float)
    return rot_points(pts, angle) + np.asarray(center, dtype=float)