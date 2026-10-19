from __future__ import annotations
import math
from typing import Optional, Tuple

import config


def _focal_px(fov_deg: float, img_w: int) -> float:
    if fov_deg <= 0 or img_w <= 0:
        return float(img_w)
    return (img_w / 2.0) / math.tan(math.radians(fov_deg) / 2.0)


def _bearing_rad(u_px: float, img_w: int,
                 fov_deg: float, cam_aci_deg: float) -> float:
    f = _focal_px(fov_deg, img_w)
    rel = math.atan2(u_px - img_w / 2.0, f)
    return math.radians(cam_aci_deg) + rel


def triangulate(
    u_a: float, u_b: float,
    img_w_a: int, img_w_b: int,
) -> Optional[Tuple[float, float, float]]:
    geo = config.KAMERA_GEOMETRI
    if not geo.get("STEREO_ETKIN", False):
        return None

    fov_a = geo.get("FOV_H_A", 90.0)
    fov_b = geo.get("FOV_H_B", 90.0)
    aci_a = geo.get("ACHI_A_DEG", 0.0)
    aci_b = geo.get("ACHI_B_DEG", 0.0)
    ka = geo.get("KONUM_A", [0.0, 0.0, 0.0])
    kb = geo.get("KONUM_B", [0.30, 0.0, 0.0])

    ax, ay = float(ka[0]), float(ka[1])
    bx, by = float(kb[0]), float(kb[1])

    # Bearing vektörleri (2D, yatay düzlem)
    ba = _bearing_rad(u_a, img_w_a, fov_a, aci_a)
    bb = _bearing_rad(u_b, img_w_b, fov_b, aci_b)

    da_x, da_y = math.cos(ba), math.sin(ba)  # A'dan çıkan yön
    db_x, db_y = math.cos(bb), math.sin(bb)  # B'den çıkan yön

    det = da_x * (-db_y) - (-db_x) * da_y
    if abs(det) < 1e-9:
        return None  # Paralel doğrular - çözüm yok

    dx = bx - ax
    dy = by - ay
    t = (dx * (-db_y) - (-db_x) * dy) / det
    s = (da_x * dy - dx * da_y) / det

    if t < 0 or s < 0:
        return None  # Kameraların arkasına işaret ediyor

    # Kavuşma noktası (ortalama)
    tx = ((ax + t * da_x) + (bx + s * db_x)) / 2.0
    ty = ((ay + t * da_y) + (by + s * db_y)) / 2.0

    dist_m = math.sqrt((tx - ax) ** 2 + (ty - ay) ** 2)
    return tx, ty, dist_m


def fuz_uzaklik(stereo_m: Optional[float],
                lidar_m: Optional[float]) -> Optional[float]:
    if lidar_m is not None and stereo_m is not None:
        return 0.75 * lidar_m + 0.25 * stereo_m
    if lidar_m is not None:
        return lidar_m
    if stereo_m is not None:
        return stereo_m
    return None
