import queue
import threading
import logging
from dataclasses import dataclass, field

from PyQt6.QtCore import QThread, pyqtSignal

import config
from donanim import ates_komutu

log = logging.getLogger(__name__)


# Veri sınıfı

@dataclass
class SuruHedfi:
    track_id: int
    bbox: tuple
    sinif: str
    guven: float
    uzlasma_sayac: int = 0
    balon_guven: float = 0.0
    onaylandi: bool = False
    hiz: tuple = field(default_factory=lambda: (0.0, 0.0))
    dost: bool = False
    uzaklik_m: float = None  # LiDAR/stereo mesafesi (metre, None = bilinmiyor)


# Yardımcı fonksiyonlar

def _iou(b1: tuple, b2: tuple) -> float:
    x1, y1, w1, h1 = b1; x2, y2, w2, h2 = b2
    xa = max(x1, x2); ya = max(y1, y2)
    xb = min(x1+w1, x2+w2); yb = min(y1+h1, y2+h2)
    inter = max(0, xb-xa) * max(0, yb-ya)
    union = w1*h1 + w2*h2 - inter
    return inter / union if union > 0 else 0.0


def _gimbal_gonder_ham(mesaj: str) -> None:
    try:
        from motor import MotorKontrol
        m = MotorKontrol.get_instance()
        if m and m.bagli_mi():
            m._gonder(mesaj + "\n")
    except Exception:
        pass


def _hata_to_adim(hata_px: int, kp: float, max_adim: int, dead_zone: int = 8) -> int:
    if abs(hata_px) < dead_zone:
        return 0
    isaret = 1 if hata_px >= 0 else -1
    adim = int((hata_px ** 2) * kp / 100 * isaret)
    return max(-max_adim, min(max_adim, adim))


# Ana thread

class Asama2Thread(QThread):
    hedef_listesi = pyqtSignal(list)  # list[SuruHedfi]
    uzlasma_tamam = pyqtSignal(dict)  # {id, bbox, sinif, guven}
    imha_komutu = pyqtSignal(dict)
    faz_degisti = pyqtSignal(str)
    suru_sayisi = pyqtSignal(int)
    siniflar_hazir = pyqtSignal(list)  # geriye dönük uyumluluk
    hata = pyqtSignal(str)

    def __init__(self, buf_a, buf_b, parent=None):
        super().__init__(parent)
        self._buf_a = buf_a  # geriye dönük compat - kullanılmıyor
        self._buf_b = buf_b  # geriye dönük compat - kullanılmıyor
        self._dur_event = threading.Event()
        self._onay_event = threading.Event()
        self._atis_mod = config.ASAMA_2["ATIS_MODU"]
        self._aktif: dict[int, SuruHedfi] = {}
        self._son_gimbal = ""
        self._id_sayac = 0  # track_id=0 durumunda dahili ID üretimi

        # Dual kuyruk mimarisi: Kamera A ve Kamera B ayrı kuyruklar
        self._queue_a: queue.Queue = queue.Queue(maxsize=4)
        self._queue_b: queue.Queue = queue.Queue(maxsize=4)
        self._queue = self._queue_a  # geriye dönük uyumluluk
        self._lidar_m: float | None = None  # Son LiDAR mesafesi (metre)

    # Başlatma / Durdurma
    def baslat(self) -> None:
        self._dur_event.clear()
        self._aktif.clear()
        self._id_sayac = 0
        self.start()

    def dur(self) -> None:
        self._dur_event.set()
        self.wait(5000)

    # Dış kontrol
    def mod_ayarla(self, mod: str) -> None:
        self._atis_mod = mod

    def manuel_onayla(self) -> None:
        self._onay_event.set()

    # Det-thread'ten hedef al (DirectConnection)
    def _queue_koy(self, q: queue.Queue, hedefler: list) -> None:
        while not q.empty():
            try: q.get_nowait()
            except queue.Empty: break
        try: q.put_nowait(hedefler)
        except queue.Full: pass

    def hedef_listesi_al(self, hedefler: list) -> None:
        self._queue_koy(self._queue_a, hedefler)

    def hedef_listesi_al_b(self, hedefler: list) -> None:
        self._queue_koy(self._queue_b, hedefler)

    def lidar_guncelle(self, mesafe_m: float) -> None:
        self._lidar_m = mesafe_m

    # Ana döngü
    def run(self) -> None:
        cfg = config.ASAMA_2
        cam_cfg = config.KAMERA_A_AYAR
        self.faz_degisti.emit("TARAMA")
        log.info("Asama2Thread başladı (det_thread queue modu).")

        while not self._dur_event.is_set():
            try:
                kh_listesi = self._queue_a.get(timeout=0.1)
            except queue.Empty:
                continue

            # Kamera B'den ek hedefler (non-blocking)
            # suru takibi tek kamerada (A), B kuyrugu dolmasin diye bosaltiliyor
            try:
                self._queue_b.get_nowait()
            except queue.Empty:
                pass

            if config.ACIL_DURDUR_EVENT.is_set():
                continue

            kare_w = config.UI_AYAR.get("KAMERA_GENISLIK", 1280)
            kare_h = config.UI_AYAR.get("KAMERA_YUKSEKLIK", 720)

            dost_siniflar = set(cam_cfg.get("DOST_SINIFLAR", []))
            nesne_filtre = cam_cfg.get("NESNE_SINIFLARI", [])
            uzlasma_gerek = cfg.get("UZLASMA_GEREK", 2)
            kayip_limit = cfg.get("HEDEF_KAYIP_LIMIT", 5)
            max_suru = cfg.get("MAX_SURU_BOYUTU", 20)

            # Mevcut aktif track'lerin "yaşını" azalt (kaybolan tespit)
            for h in self._aktif.values():
                h._kacik = getattr(h, "_kacik", 0) + 1

            aktif_ids: set[int] = set()

            for kh in kh_listesi:
                sinif = kh.sinif
                if nesne_filtre and sinif not in nesne_filtre:
                    continue

                is_dost = kh.dost or (sinif in dost_siniflar)

                # Track ID eşleştirme
                tid = kh.track_id if kh.track_id and kh.track_id != 0 else 0

                if tid == 0:
                    # Tracking yok: IoU ile en yakın mevcut track'i bul
                    en_iyi_tid = None
                    en_iyi_iou = 0.3
                    for mev_tid, mev_h in self._aktif.items():
                        ov = _iou(kh.bbox, mev_h.bbox)
                        if ov > en_iyi_iou:
                            en_iyi_iou = ov
                            en_iyi_tid = mev_tid
                    if en_iyi_tid is not None:
                        tid = en_iyi_tid
                    else:
                        # Yeni track oluştur
                        self._id_sayac += 1
                        tid = self._id_sayac

                h = self._aktif.setdefault(
                    tid, SuruHedfi(tid, kh.bbox, sinif, kh.guven))
                h.bbox = kh.bbox
                h.guven = kh.guven
                h.sinif = sinif
                h.dost = is_dost
                h._kacik = 0  # aktif -> sıfırla
                aktif_ids.add(tid)

                # Uzlaşma sayacı
                h.uzlasma_sayac = min(h.uzlasma_sayac + 1, uzlasma_gerek + 2)
                h.balon_guven = kh.guven
                h.uzaklik_m = self._lidar_m  # LiDAR mesafesini hedefle esle

                if h.uzlasma_sayac >= uzlasma_gerek and not h.onaylandi:
                    h.onaylandi = True
                    self.uzlasma_tamam.emit(
                        {"id": tid, "bbox": kh.bbox,
                         "sinif": sinif, "guven": h.balon_guven})
                    if not h.dost:
                        self._imha_et(h)

            # Kaybolan / eski track'leri temizle
            for tid in [t for t, h in list(self._aktif.items())
                        if getattr(h, "_kacik", 0) > kayip_limit]:
                del self._aktif[tid]

            # Sürü boyutu sınırı
            if len(self._aktif) > max_suru:
                tum = sorted(self._aktif.items(),
                             key=lambda x: x[1].guven, reverse=True)
                self._aktif = dict(tum[:max_suru])

            # Gimbal takip (en güvenilir düşman hedefe)
            don_cfg = config.DONANIM
            lox = don_cfg.get("LAZER_OFFSET_X", 0)
            loy = don_cfg.get("LAZER_OFFSET_Y", 0)
            frame_cx = kare_w // 2
            frame_cy = kare_h // 2

            dusmanlar = [h for h in self._aktif.values() if not h.dost]
            gimbal_h = max(dusmanlar, key=lambda h: h.guven, default=None)

            if gimbal_h:
                bx, by, bw, bh = gimbal_h.bbox
                hx = bx + bw // 2
                hy = by + bh // 2
                error_x = (hx - frame_cx) - lox
                error_y = (hy - frame_cy) - loy
                kp = don_cfg.get("KP_X", 3.0)
                max_adim = don_cfg.get("MAX_STEPS_X", 500)
                dz = don_cfg.get("DEAD_ZONE_PIXEL", 8)
                ax = _hata_to_adim(error_x, kp, max_adim, dz)
                ay = _hata_to_adim(error_y, kp, max_adim, dz)
                gimbal_fmt = config.DONANIM.get("GIMBAL_FORMAT", "!X{x}Y{y}*")
                yeni_gimbal = gimbal_fmt.format(x=ax, y=ay)
            else:
                yeni_gimbal = config.DONANIM.get("GIMBAL_DUR_FORMAT", "!X0Y0*")

            if yeni_gimbal != self._son_gimbal:
                _gimbal_gonder_ham(yeni_gimbal)
                self._son_gimbal = yeni_gimbal

            if self._atis_mod != "OTONOM" and self._onay_event.is_set():
                self._onay_event.clear()
                if gimbal_h and gimbal_h.onaylandi:
                    self._ates_ver(gimbal_h)

            self.hedef_listesi.emit(list(self._aktif.values()))
            self.suru_sayisi.emit(len(self._aktif))

        log.info("Asama2Thread durdu.")

    # Yardımcı metodlar
    def _imha_et(self, h: SuruHedfi) -> None:
        if self._atis_mod == "OTONOM":
            self._ates_ver(h)
        else:
            self.faz_degisti.emit("NISAN")
            # MANUEL modda da imha_komutu sinyali gonder (UI onay badge'i icin)
            self.imha_komutu.emit({
                "id": h.track_id,
                "bbox": h.bbox,
                "sinif": h.sinif,
                "uzaklik_m": self._lidar_m,
            })

    def _ates_ver(self, h: SuruHedfi) -> None:
        # Hedefe ozgu mesafe varsa onu kullan, yoksa anlik LiDAR degerini al
        uzaklik = h.uzaklik_m if h.uzaklik_m is not None else self._lidar_m
        self.imha_komutu.emit({
            "id": h.track_id,
            "bbox": h.bbox,
            "sinif": h.sinif,
            "uzaklik_m": uzaklik,
        })
        ates_komutu(h.track_id, h.bbox, h.sinif)
        log.info("[Asama2] ATES EDILDI: id=%d sinif=%s uzaklik=%.1fm",
                 h.track_id, h.sinif, uzaklik if uzaklik is not None else -1)
