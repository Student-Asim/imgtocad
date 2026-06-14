import numpy as np


def ray_wall_intersect(origin, direction, p1, p2):
    wall = p2 - p1
    denom = direction[0] * wall[1] - direction[1] * wall[0]
    if abs(denom) < 1e-9:
        return None
    diff = p1 - origin
    t = (diff[0] * wall[1] - diff[1] * wall[0]) / denom
    u = (diff[0] * direction[1] - diff[1] * direction[0]) / denom
    if t > 1e-6 and 0 <= u <= 1:
        return t, u
    return None


def find_hit_wall(origin, angle, pts_m, n_walls):
    d_vec = np.array([np.cos(angle), np.sin(angle)], dtype=float)
    best = None
    for i in range(n_walls):
        res = ray_wall_intersect(origin, d_vec, pts_m[i], pts_m[(i + 1) % n_walls])
        if res is None:
            continue
        t, u = res
        if best is None or t < best[0]:
            best = (t, u, i)
    return best