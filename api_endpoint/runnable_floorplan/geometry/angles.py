import numpy as np


def pano_x_to_angle(px: float, img_w: int = 1024) -> float:
    return (px / img_w) * 2 * np.pi


def circular_delta(a: float, b: float) -> float:
    return ((a - b + np.pi) % (2 * np.pi)) - np.pi