import numpy as np
from scipy.signal import find_peaks
from sklearn.cluster import DBSCAN

from api_endpoint import config as C
from ..types import RoomLayout


def extract_stable_corners(cor_map):
    cor_map = cor_map.astype(np.float32)
    smooth = np.convolve(cor_map, np.ones(7) / 7, mode="same")
    peaks, _ = find_peaks(smooth, height=C.PEAK_THRESH, distance=C.MIN_PEAK_DISTANCE)
    if len(peaks) == 0:
        return np.zeros((0, 2), dtype=np.float32), smooth
    clust = DBSCAN(eps=C.CLUSTER_EPS, min_samples=1).fit(peaks.reshape(-1, 1))
    stable = sorted(int(np.mean(peaks[clust.labels_ == lab])) for lab in np.unique(clust.labels_))
    stable = np.array(stable)
    return np.stack([stable, np.zeros_like(stable)], axis=1).astype(np.float32), smooth


def order_polygon(pts):
    c = pts.mean(0)
    ang = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0])
    return pts[np.argsort(ang)]


def manhattanize(pts):
    pts = pts.copy()
    for i in range(len(pts)):
        p1, p2 = pts[i], pts[(i + 1) % len(pts)]
        d = p2 - p1
        if abs(d[0]) > abs(d[1]):
            p2[1] = p1[1]
        else:
            p2[0] = p1[0]
        pts[(i + 1) % len(pts)] = p2
    return pts


def remove_small_edges(pts):
    cleaned = np.array([
        pts[i] for i in range(len(pts))
        if np.linalg.norm(pts[(i + 1) % len(pts)] - pts[i]) > C.MIN_EDGE_LEN
    ])
    return cleaned if len(cleaned) >= 3 else pts


def build_floorplan_polygon(cor, width):
    corners, smooth = extract_stable_corners(cor)
    if len(corners) < 3:
        raise ValueError("Too few corners detected. Use a clearer panorama.")
    corner_pixels = corners[:, 0]
    corner_angles = (corner_pixels / width) * 2 * np.pi
    raw_pts = np.stack([np.cos(corner_angles), np.sin(corner_angles)], axis=1)
    raw_pts = order_polygon(raw_pts)
    raw_pts = manhattanize(raw_pts)
    raw_pts = remove_small_edges(raw_pts)
    mins = raw_pts.min(axis=0)
    maxs = raw_pts.max(axis=0)
    span = np.maximum(maxs - mins, 1e-9)
    scale = C.ROOM_SCALE / span.max()
    pts_m = (raw_pts - mins) * scale
    return RoomLayout(
        pts_m=pts_m,
        n_walls=len(pts_m),
        room_center=pts_m.mean(0),
        corner_pixels=corner_pixels,
        smooth=smooth,
    )