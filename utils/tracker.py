import logging
from typing import List, Dict, Optional
import numpy as np

log = logging.getLogger(__name__)

try:
    import supervision as sv
    _SV_OK = True
    log.info("supervision yüklendi (%.1s)", getattr(sv, "__version__", "?"))
except ImportError:
    _SV_OK = False
    log.warning("supervision bulunamadı — ByteTrack fallback (ultralytics.track) aktif. "
                "Kurmak için: pip install supervision")


class Tracker:

    def __init__(self,
                 algorithm: str = "botsort",
                 lost_track_buffer: int = 30,
                 min_hits: int = 3,
                 iou_threshold: float = 0.3):
        self._alg = algorithm.lower()
        self._tracker = None
        self._prev_bboxes: Dict[int, tuple] = {}  # hız hesabı için

        if _SV_OK:
            self._tracker = self._olustur(lost_track_buffer, min_hits, iou_threshold)

    def _olustur(self, lost_buffer: int, min_hits: int, iou_thr: float):
        if self._alg == "botsort":
            try:
                return sv.BotSort(
                    lost_track_buffer=lost_buffer,
                    minimum_consecutive_frames=min_hits,
                )
            except Exception as e:
                log.warning("BotSort oluşturulamadı (%s) → ByteTrack'e geçiliyor", e)
                self._alg = "bytetrack"

        return sv.ByteTrack(
            lost_track_buffer=lost_buffer,
            minimum_consecutive_frames=min_hits,
            minimum_matching_threshold=iou_thr,
        )

    def guncelle(self,
                 result,
                 frame: Optional[np.ndarray] = None,
                 filtre: Optional[List[str]] = None) -> List[Dict]:
        if _SV_OK and self._tracker is not None:
            return self._sv_guncelle(result, filtre)
        else:
            return self._fallback(result, filtre)

    # Supervision yolu
    def _sv_guncelle(self, result, filtre) -> List[Dict]:
        dets = sv.Detections.from_ultralytics(result)

        # Sınıf filtresi
        if filtre and dets.class_id is not None and len(dets) > 0:
            izin = [i for i, cid in enumerate(dets.class_id)
                    if result.names.get(int(cid), "") in filtre]
            if izin:
                dets = dets[np.array(izin)]
            else:
                dets = sv.Detections.empty()

        tracked = self._tracker.update_with_detections(dets)
        return self._to_dict_list(tracked, result.names)

    def _to_dict_list(self, dets, names: dict) -> List[Dict]:
        out = []
        for i in range(len(dets)):
            x1, y1, x2, y2 = dets.xyxy[i].tolist()
            bbox = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
            track_id = int(dets.tracker_id[i]) if dets.tracker_id is not None else i
            sinif = names.get(int(dets.class_id[i]), "?") if dets.class_id is not None else "?"
            guven = float(dets.confidence[i]) if dets.confidence is not None else 0.0

            # Hız (piksel/kare)
            cx = x1 + (x2 - x1) / 2
            cy = y1 + (y2 - y1) / 2
            prev = self._prev_bboxes.get(track_id)
            if prev:
                vx = cx - prev[0]
                vy = cy - prev[1]
            else:
                vx = vy = 0.0
            self._prev_bboxes[track_id] = (cx, cy)

            out.append({
                "track_id": track_id,
                "id": track_id,
                "bbox": bbox,
                "sinif": sinif,
                "guven": guven,
                "hiz": (vx, vy),
            })
        return out

    # Fallback: ultralytics .track()
    def _fallback(self, result, filtre) -> List[Dict]:
        out = []
        for box in result.boxes:
            sinif = result.names.get(int(box.cls[0]), "?")
            if filtre and sinif not in filtre:
                continue
            tid = int(box.id[0]) if box.id is not None else 0
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            bbox = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
            out.append({
                "track_id": tid,
                "id": tid,
                "bbox": bbox,
                "sinif": sinif,
                "guven": float(box.conf[0]),
                "hiz": (0.0, 0.0),
            })
        return out

    def sifirla(self) -> None:
        if _SV_OK and self._tracker is not None:
            try:
                self._tracker.reset()
            except AttributeError:
                pass
        self._prev_bboxes.clear()

    @property
    def algoritma(self) -> str:
        return self._alg if _SV_OK else "fallback-ultralytics"

    @property
    def supervision_aktif(self) -> bool:
        return _SV_OK and self._tracker is not None
