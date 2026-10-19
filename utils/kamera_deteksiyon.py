from __future__ import annotations
import time
import threading
import logging
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QThread, pyqtSignal

import config

log = logging.getLogger(__name__)


# Veri sınıfı
class KameraHedefi:
    __slots__ = ("id", "bbox", "sinif", "guven", "dost", "onaylandi",
                 "track_id", "hiz", "_ek_oncelik", "uzaklik_m", "konum_3d")

    def __init__(self, id=0, bbox=(0,0,0,0), sinif="", guven=0.0,
                 dost=False, track_id=0):
        self.id = id
        self.bbox = bbox
        self.sinif = sinif
        self.guven = guven
        self.dost = dost
        self.onaylandi = False
        self.track_id = track_id
        self.hiz = (0.0, 0.0)
        self._ek_oncelik = False
        self.uzaklik_m = None  # float | None - LiDAR/stereo mesafesi (metre)
        self.konum_3d = None  # (x, y, z) | None - dünya koordinatı (metre)


# NMS yardımcıları
def _iou(b1, b2):
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    xa = max(x1, x2); ya = max(y1, y2)
    xb = min(x1+w1, x2+w2); yb = min(y1+h1, y2+h2)
    inter = max(0, xb-xa) * max(0, yb-ya)
    union = w1*h1 + w2*h2 - inter
    return inter / union if union > 0 else 0.0


def _containment(b_ic, b_dis):
    x1, y1, w1, h1 = b_ic
    x2, y2, w2, h2 = b_dis
    xa = max(x1, x2); ya = max(y1, y2)
    xb = min(x1+w1, x2+w2); yb = min(y1+h1, y2+h2)
    inter = max(0, xb-xa) * max(0, yb-ya)
    alan_ic = w1 * h1
    return inter / alan_ic if alan_ic > 0 else 0.0


def _gelismis_nms(dets: list, iou_esigi: float = 0.45,
                  containment_esigi: float = 0.80) -> list:
    if len(dets) <= 1:
        return dets
    dets = sorted(dets, key=lambda d: d["guven"], reverse=True)
    alanlara = sorted(dets, key=lambda d: d["bbox"][2] * d["bbox"][3], reverse=True)
    atilacak = set()
    for i, d_b in enumerate(alanlara):
        if id(d_b) in atilacak:
            continue
        for d_k in alanlara[i+1:]:
            if id(d_k) in atilacak:
                continue
            if _containment(d_k["bbox"], d_b["bbox"]) >= containment_esigi:
                atilacak.add(id(d_k))
    dets = [d for d in dets if id(d) not in atilacak]
    out = []
    for d in dets:
        if not any(_iou(d["bbox"], s["bbox"]) >= iou_esigi for s in out):
            out.append(d)
    return out


# track() bir kere patlarsa (ornegin lap paketi yoksa) her karede tekrar denemesin
_track_bozuk = False


# Çıkarım (executor'da çalışır)
def _cikarim(model, kare, conf: float, classes_idx,
             imgsz: int, tracker_ac: bool, tracker_algo: str,
             use_gpu: bool = False) -> list:
    global _track_bozuk
    if tracker_ac and not _track_bozuk:
        try:
            algo = tracker_algo.lower()
            if algo not in ("botsort", "bytetrack"):
                algo = "botsort"
            # Custom YAML: daha yüksek track_buffer + düşük eşikler -> stabil ID
            import pathlib as _pl
            _base = _pl.Path(__file__).parent.parent
            _yaml_map = {"botsort": "botsort_tturks.yaml", "bytetrack": "bytetrack_tturks.yaml"}
            _yaml = str(_base / _yaml_map.get(algo, f"{algo}.yaml"))
            if not _pl.Path(_yaml).exists():
                _yaml = f"{algo}.yaml"  # fallback to default
            _gpu_kw = {"device": 0, "half": True} if use_gpu else {}
            res = model.track(kare, persist=True,
                              conf=conf, classes=classes_idx,
                              imgsz=imgsz, verbose=False,
                              tracker=_yaml, **_gpu_kw)[0]
        except Exception as e:
            log.warning("track() calismadi, takip kapatildi, predict() ile devam: %s", e)
            _track_bozuk = True
            _gpu_kw = {"device": 0, "half": True} if use_gpu else {}
            res = model(kare, conf=conf, classes=classes_idx,
                        imgsz=imgsz, verbose=False, **_gpu_kw)[0]
    else:
        _gpu_kw = {"device": 0, "half": True} if use_gpu else {}
        res = model(kare, conf=conf, classes=classes_idx,
                    imgsz=imgsz, verbose=False, **_gpu_kw)[0]

    tum = []
    for box in res.boxes:
        sinif = res.names[int(box.cls[0])]
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        bw, bh = int(x2 - x1), int(y2 - y1)
        tid = int(box.id[0]) if (hasattr(box, "id") and box.id is not None) else 0
        tum.append({
            "bbox": (int(x1), int(y1), bw, bh),
            "sinif": sinif,
            "guven": float(box.conf[0]),
            "track_id": tid,
        })
    return tum


# Ana deteksiyon thread'i
class KameraDeteksiyonThread(QThread):
    hedef_listesi = pyqtSignal(list)
    siniflar_hazir = pyqtSignal(list)
    yolo_fps = pyqtSignal(float)
    hata = pyqtSignal(str)

    def __init__(self, buffer, ayar: dict, model=None, parent=None):
        super().__init__(parent)
        self._buffer = buffer
        self._ayar = ayar
        self._model = model
        self._dur_event = threading.Event()
        self._sinif_idx: dict[str, int] = {}
        self._executor: ThreadPoolExecutor | None = None
        # ID normalizasyonu - orijinal tracker ID -> compact session-local ID (1,2,3...)
        self._id_harita: dict[int, int] = {}  # orig -> norm
        self._id_ttl: dict[int, int] = {}  # orig -> frames_since_last_seen
        self._id_sayac: int = 0
        # Model yenileme - concurrent çıkarımlara karşı guard
        self._model_yukleme_lock = threading.Lock()
        self._model_yukleniyor = False

    def dur(self) -> None:
        self._dur_event.set()
        self.wait(6000)
        if self._executor:
            self._executor.shutdown(wait=False)

    def model_yenile(self, yol: str) -> None:
        if self._model_yukleniyor:
            log.warning("Model yüklemesi zaten devam ediyor, istek yoksayıldı: %s", yol)
            return
        import threading as _th
        _th.Thread(target=self._model_yenile_bg, args=(yol,), daemon=True).start()

    def _model_yenile_bg(self, yol: str) -> None:
        with self._model_yukleme_lock:
            self._model_yukleniyor = True
            log.info("Model yenileniyor (arka plan) → %s", yol)
            eski_model = self._model
            eski_sinif_idx = dict(self._sinif_idx)
            try:
                if self.isRunning():
                    self._dur_event.set()
                    self.wait(5000)
                    if self._executor:
                        self._executor.shutdown(wait=False)
                    self._executor = None
                self._id_harita.clear()
                self._id_ttl.clear()
                self._id_sayac = 0
                from utils.model_yukleyici import yukle as _yukle
                yeni_model = _yukle(yol)
                siniflari = list(yeni_model.names.values())
                sinif_idx = {v: k for k, v in yeni_model.names.items()}
                self._model = yeni_model
                self._sinif_idx = sinif_idx
                self._ayar["_MODEL_SINIFLARI"] = siniflari
                self.siniflar_hazir.emit(siniflari)
                log.info("Model yüklendi → %s", yol)
                self._dur_event.clear()
                self.start()
            except Exception as e:
                self._model = eski_model
                self._sinif_idx = eski_sinif_idx
                self.hata.emit(f"Model yüklenemedi ({yol}): {e}")
                log.error("Model yüklenemedi, eski model devrede: %s", e)
                if eski_model is not None:
                    self._dur_event.clear()
                    self.start()
            finally:
                self._model_yukleniyor = False

    def _filtre_idx(self, filtre: list) -> list | None:
        if not filtre:
            return None
        idxler = [self._sinif_idx[s] for s in filtre if s in self._sinif_idx]
        return idxler if idxler else None

    def run(self) -> None:
        # Model yukle
        if self._model is None:
            yol = self._ayar.get("MODEL_YOLU", config.MODEL_NESNE_YOLU)
            try:
                from utils.model_yukleyici import yukle as _yukle
                self._model = _yukle(yol)
                log.info("KameraDeteksiyonThread: model -> %s", yol)
            except Exception as e:
                msg = f"Model yuklenemedi ({yol}): {e}"
                log.error(msg)
                self.hata.emit(msg)
                return

        try:
            self._sinif_idx = {v: k for k, v in self._model.names.items()}
        except Exception:
            pass

        siniflari = list(self._model.names.values()) if self._model else []
        self._ayar["_MODEL_SINIFLARI"] = siniflari
        self.siniflar_hazir.emit(siniflari)

        # GPU kontrolu (bir kez yapilir)
        _use_gpu = False
        try:
            import torch
            _use_gpu = torch.cuda.is_available()
            log.info("GPU=%s (CUDA: %s)", _use_gpu,
                     torch.version.cuda if _use_gpu else "yok")
        except Exception:
            log.info("torch import hatasi — CPU inferans")

        _fps_kare = 0
        _fps_t0 = time.perf_counter()
        _son_kare_no = -1
        _was_etkin = False
        _filtre_onceki = None  # filtre indeksi cache
        _classes_idx = None

        log.info("KameraDeteksiyonThread: dongu basliyor (executor'suz, GPU=%s)", _use_gpu)

        while not self._dur_event.is_set():

            # FPS emit
            _now = time.perf_counter()
            if _now - _fps_t0 >= 1.0:
                fps_val = _fps_kare / (_now - _fps_t0) if _fps_kare > 0 else 0.0
                self.yolo_fps.emit(fps_val)
                _fps_kare = 0
                _fps_t0 = _now

            # Kamera kapali / Acil Durdur
            etkin_su = self._ayar.get("ETKIN", False) and not config.ACIL_DURDUR_EVENT.is_set()
            if not etkin_su:
                if _was_etkin:
                    self.hedef_listesi.emit([])
                    _son_kare_no = -1
                    self._id_harita.clear()
                    self._id_ttl.clear()
                    self._id_sayac = 0
                _was_etkin = False
                self._dur_event.wait(0.05)
                continue
            _was_etkin = True

            # Yeni kare bekle (dusuk CPU)
            mevcut_no = self._buffer.yazma_sayaci
            if mevcut_no == _son_kare_no:
                self._dur_event.wait(0.003)
                continue

            kare = self._buffer.son_kare()
            if kare is None:
                continue
            _son_kare_no = mevcut_no

            kare_h, kare_w = kare.shape[:2]
            kare_alani = max(kare_w * kare_h, 1)

            # Ayarlari oku
            guven = float(self._ayar.get("GUVEN_ESIGI", 0.25))
            filtre = list(self._ayar.get("NESNE_SINIFLARI", []))
            imgsz = int(self._ayar.get("IMGSZ", 640))
            tracker_ac = bool(self._ayar.get("TRACKER", False))
            tracker_algo = str(self._ayar.get("TRACKER_ALGORITMA", "botsort"))

            # Filtre indeksleri - degismediginde cache'den al
            if filtre != _filtre_onceki:
                _classes_idx = self._filtre_idx(filtre)
                _filtre_onceki = filtre

            # Dogrudan cikarim (executor overhead yok)
            try:
                tum_dets: list[dict] = _cikarim(
                    self._model, kare, guven, _classes_idx,
                    imgsz, tracker_ac, tracker_algo, _use_gpu)
            except Exception as e:
                log.warning("Cikarim hatasi: %s", e)
                continue

            # Post filtre
            filtre_set = set(filtre)
            if filtre_set:
                tum_dets = [d for d in tum_dets if d["sinif"] in filtre_set]

            min_alan = kare_alani * float(self._ayar.get("MIN_ALAN_ORAN", 0.001))
            tum_dets = [d for d in tum_dets
                        if d["bbox"][2] * d["bbox"][3] >= min_alan]
            tum_dets = _gelismis_nms(
                tum_dets,
                float(self._ayar.get("NMS_ESIGI", 0.45)),
                float(self._ayar.get("CONTAINMENT_ESIGI", 0.80)))

            # 3-katmanli siniflandirma
            dost_s = set(self._ayar.get("DOST_SINIFLAR", []))
            dusman_s = set(self._ayar.get("DUSMAN_SINIFLAR", []))
            tehdit_s = (list(self._ayar.get("TEHDIT_SIRASI", []))
                        or list(self._ayar.get("IMHA_SIRASI", [])))

            hedefler: list[KameraHedefi] = []
            for det in tum_dets:
                sinif = det["sinif"]
                if sinif in dost_s:
                    tip = "dost"
                elif dusman_s and sinif not in dusman_s:
                    continue  # filtre disi
                else:
                    tip = "dusman"

                orig_id = det.get("track_id", 0)
                if orig_id > 0:
                    if orig_id not in self._id_harita:
                        self._id_sayac += 1
                        self._id_harita[orig_id] = self._id_sayac
                    self._id_ttl[orig_id] = 0
                    norm_id = self._id_harita[orig_id]
                else:
                    norm_id = 0

                h = KameraHedefi(
                    bbox=det["bbox"],
                    sinif=sinif,
                    guven=det["guven"],
                    dost=(tip == "dost"),
                    track_id=norm_id,
                )
                hedefler.append(h)

            # Tehdit sirasina gore sirala
            def _sira(h: KameraHedefi):
                prio = tehdit_s.index(h.sinif) if h.sinif in tehdit_s else len(tehdit_s)
                return (
                    h.dost,
                    prio,
                    -(h.bbox[2] * h.bbox[3] / kare_alani) * (h.guven ** 1.5),
                )

            hedefler.sort(key=_sira)
            rank = 1
            for h in hedefler:
                if not h.dost:
                    h.id = rank; rank += 1

            # Stale ID haritasi - TTL temizle
            aktif_orig = {det.get("track_id", 0) for det in tum_dets
                          if det.get("track_id", 0) > 0}
            for oid in list(self._id_harita):
                if oid in aktif_orig:
                    self._id_ttl[oid] = 0
                else:
                    self._id_ttl[oid] = self._id_ttl.get(oid, 0) + 1
                    if self._id_ttl[oid] > 90:
                        del self._id_harita[oid]
                        del self._id_ttl[oid]

            self.hedef_listesi.emit(hedefler)
            _fps_kare += 1
