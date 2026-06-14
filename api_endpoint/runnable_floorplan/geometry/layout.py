import numpy as np
from scipy.signal import find_peaks
from sklearn.cluster import DBSCAN

from api_endpoint import config_old as C
from ..types_old import RoomLayout


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


def _polygon_area(pts):
    return 0.5 * abs(
        np.dot(pts[:, 0], np.roll(pts[:, 1], -1)) -
        np.dot(pts[:, 1], np.roll(pts[:, 0], -1))
    )


def build_floorplan_polygon(
    cor,
    width,
    room_scale=None,
    use_room_calibration=None,
    target_room_width_m=None,
    target_room_depth_m=None,
    reference_wall_length_m=None,
    reference_wall_index=None,
):
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

    room_scale = C.ROOM_SCALE if room_scale is None else room_scale
    use_room_calibration = C.USE_ROOM_CALIBRATION if use_room_calibration is None else use_room_calibration
    target_room_width_m = C.TARGET_ROOM_WIDTH_M if target_room_width_m is None else target_room_width_m
    target_room_depth_m = C.TARGET_ROOM_DEPTH_M if target_room_depth_m is None else target_room_depth_m
    reference_wall_length_m = C.REFERENCE_WALL_LENGTH_M if reference_wall_length_m is None else reference_wall_length_m
    reference_wall_index = C.REFERENCE_WALL_INDEX if reference_wall_index is None else reference_wall_index

    scale_x = room_scale / span.max()
    scale_y = scale_x

    if use_room_calibration:
        if target_room_width_m > 0 and target_room_depth_m > 0:
            scale_x = target_room_width_m / span[0]
            scale_y = target_room_depth_m / span[1]
        elif reference_wall_length_m > 0:
            temp_scale = room_scale / span.max()
            pts_m_temp = (raw_pts - mins) * temp_scale

            i = int(reference_wall_index) % len(pts_m_temp)
            p1 = pts_m_temp[i]
            p2 = pts_m_temp[(i + 1) % len(pts_m_temp)]
            current_len = np.linalg.norm(p2 - p1)

            if current_len > 1e-6:
                uniform_factor = reference_wall_length_m / current_len
                scale_x = temp_scale * uniform_factor
                scale_y = temp_scale * uniform_factor

    pts_m = raw_pts - mins
    pts_m[:, 0] *= scale_x
    pts_m[:, 1] *= scale_y

    return RoomLayout(
        pts_m=pts_m,
        n_walls=len(pts_m),
        room_center=pts_m.mean(0),
        corner_pixels=corner_pixels,
        smooth=smooth,
    )