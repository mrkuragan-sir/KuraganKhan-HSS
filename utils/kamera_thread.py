import threading
import time
import logging
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

import config

log = logging.getLogger(__name__)
cv2.setNumThreads(0)


class FrameBuffer:

    def __init__(self):
        self._frame: np.ndarray | None = None
        self._lock = threading.Lock()
        self._yeni = threading.Event()
        self._wcount = 0  # yazma sayacı

    def yaz(self, frame: np.ndarray) -> None:
        with self._lock:
            self._frame = frame
            self._wcount += 1
        self._yeni.set()

    def oku(self, timeout: float = 0.05) -> np.ndarray | None:
        self._yeni.wait(timeout=timeout)
        self._yeni.clear()
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def son_kare(self) -> np.ndarray | None:
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    @property
    def yazma_sayaci(self) -> int:
        return self._wcount

    @property
    def doluluk_orani(self) -> float:
        return 1.0  # artık kullanılmıyor


class KameraThread(QThread):
    kare_hazir = pyqtSignal(np.ndarray)
    hata = pyqtSignal(str)
    fps_guncellendi = pyqtSignal(float)

    def __init__(self, cam_id: int, buffer: FrameBuffer,
                 genislik: int = 1280, yukseklik: int = 720,
                 fps_limit: int = 30, flip: int = -1,
                 flip_cfg_key: str = "",
                 cam_ayar: dict | None = None,
                 parent=None):
        super().__init__(parent)
        self._cam_id = cam_id
        self._buffer = buffer
        self._genislik = genislik
        self._yukseklik = yukseklik
        self._fps_default = fps_limit
        self._flip_def = flip
        self._flip_key = flip_cfg_key
        self._cam_ayar = cam_ayar or {}
        self._dur_event = threading.Event()

    def run(self) -> None:
        # HighPriority - OS'e daha fazla CPU zamanı iste
        self.setPriority(QThread.Priority.HighPriority)

        cap = None
        sayac = 0
        t_fps0 = time.perf_counter()

        while not self._dur_event.is_set():

            # Kamera kapalı
            if not self._cam_ayar.get("ETKIN", False):
                if cap is not None:
                    cap.release(); cap = None
                    sayac = 0; t_fps0 = time.perf_counter()
                now = time.perf_counter()
                if now - t_fps0 >= 1.0:
                    self.fps_guncellendi.emit(0.0)
                    t_fps0 = now
                self._dur_event.wait(0.1)
                continue

            # Kamera aç
            if cap is None:
                cap = self._cap_ac(self._cam_id)
                if cap is None:
                    self._dur_event.wait(1.0); continue
                sayac = 0; t_fps0 = time.perf_counter()

            ui = config.UI_AYAR
            flip = (ui.get(self._flip_key, self._flip_def)
                      if self._flip_key else self._flip_def)
            t_bas = time.perf_counter()

            try:
                ret, frame = cap.read()
            except Exception as e:
                log.warning("cap.read() hata: %s", e)
                ret, frame = False, None

            if not ret or frame is None or frame.size == 0:
                self.hata.emit(f"Kamera {self._cam_id}: kare okunamadı")
                cap.release(); cap = None
                self._dur_event.wait(1.0)
                sayac = 0; t_fps0 = time.perf_counter()
                continue

            # Kanal normaliz
            if frame.ndim == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.ndim == 3 and frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            if flip >= 0:
                frame = cv2.flip(frame, flip)

            # BGR tampona yaz (deteksiyon için), RGB emit et (UI için)
            self._buffer.yaz(frame)
            self.kare_hazir.emit(frame[:, :, ::-1].copy())

            sayac += 1
            elapsed = time.perf_counter() - t_fps0
            if elapsed >= 1.0:
                self.fps_guncellendi.emit(sayac / elapsed)
                sayac = 0; t_fps0 = time.perf_counter()

            # FPS kısıtlaması (çalışma anında config'dan okunur)
            fps_limit = config.UI_AYAR.get("FPS_LIMIT", self._fps_default)
            if fps_limit and fps_limit > 0:
                hedef = 1.0 / fps_limit
                gecen = time.perf_counter() - t_bas
                bekle = hedef - gecen
                if bekle > 0.001:
                    time.sleep(bekle)

        if cap is not None:
            cap.release()

    def _cap_ac(self, cam_id: int):
        def _konfigure(c):
            c.set(cv2.CAP_PROP_FRAME_WIDTH, self._genislik)
            c.set(cv2.CAP_PROP_FRAME_HEIGHT, self._yukseklik)
            try: c.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception: pass
            try: c.set(cv2.CAP_PROP_FPS, 30)
            except Exception: pass
            try: c.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            except Exception: pass
            try: c.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))
            except Exception: pass
            return c

        def _dene(cid):
            try: c = cv2.VideoCapture(cid)
            except Exception: return None
            if c.isOpened():
                log.info("Kamera açıldı → id=%d", cid)
                return _konfigure(c)
            c.release(); return None

        cap = _dene(cam_id)
        if cap: return cap

        log.warning("Kamera %d başarısız — 0..4 taranıyor", cam_id)
        for alt in range(5):
            if alt == cam_id: continue
            cap = _dene(alt)
            if cap:
                self.hata.emit(f"Kamera {cam_id} → id={alt} kullanıldı")
                self._cam_id = alt
                return cap

        self.hata.emit(f"Kamera {cam_id}: kaynak bulunamadı")
        return None

    def dur(self) -> None:
        self._dur_event.set()
        self.wait(3000)

    def id_degistir(self, yeni_id: int) -> None:
        import threading as _th
        def _bg():
            self._dur_event.set()
            self.wait(3000)
            self._cam_id = yeni_id
            self._dur_event.clear()
            self.start()
        _th.Thread(target=_bg, daemon=True).start()
