import queue
import threading
import logging
import time
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

import config
from donanim import ates_komutu

log = logging.getLogger(__name__)


# Yardımcı fonksiyonlar

def _hata_to_adim(hata_px: int, kp: float, max_adim: int, dead_zone: int = 8) -> int:
    if abs(hata_px) < dead_zone:
        return 0
    isaret = 1 if hata_px >= 0 else -1
    adim = int((hata_px ** 2) * kp / 100 * isaret)
    return max(-max_adim, min(max_adim, adim))


def _gimbal_gonder_ham(mesaj: str) -> None:
    try:
        from motor import MotorKontrol
        m = MotorKontrol.get_instance()
        if m and m.bagli_mi():
            m._gonder(mesaj + "\n")
    except Exception:
        pass


def _oncelik_skoru(sinif: str, guven: float, bbox: tuple,
                   kare_w: int, kare_h: int, sirasi: list) -> float:
    prio = sirasi.index(sinif) if sinif in sirasi else len(sirasi)
    bx, by, bw, bh = bbox
    toplam = kare_w * kare_h if (kare_w > 0 and kare_h > 0) else 1
    alan_orani = (bw * bh) / toplam
    return (1.0 / (prio + 1)) * alan_orani * (guven ** 1.5)


def _iou(b1: tuple, b2: tuple) -> float:
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    xa = max(x1, x2); ya = max(y1, y2)
    xb = min(x1+w1, x2+w2); yb = min(y1+h1, y2+h2)
    inter = max(0, xb-xa) * max(0, yb-ya)
    union = w1*h1 + w2*h2 - inter
    return inter / union if union > 0 else 0.0


# Veri sınıfı

@dataclass
class HedefBilgi:
    id: int
    bbox: tuple  # (x, y, w, h) piksel
    sinif: str
    guven: float
    balon_eslesme: bool = False
    oncelik: float = 0.0  # öncelik skoru (büyük = daha öncelikli)
    dost: bool = False  # True -> ateş edilmez
    uzaklik_m: float = None  # LiDAR/stereo mesafesi (metre, None = bilinmiyor)
    konum_3d: tuple = None  # (x, y, z) dünya koordinatı (metre)
    kamera_idx: int = 0  # Hangi kameradan geldi (0=A, 1=B)


# Ana thread

class Asama1Thread(QThread):
    hedef_listesi = pyqtSignal(list)  # list[HedefBilgi]
    siniflar_hazir = pyqtSignal(list)  # geriye dönük uyumluluk (det_thread sağlar)
    imha_komutu = pyqtSignal(dict)  # {id, bbox, sinif, uzaklik_m}
    faz_degisti = pyqtSignal(str)  # global faz (tüm canvas)
    faz_degisti_cam = pyqtSignal(int, str)  # per-camera faz (0=CAM A, 1=CAM B)
    hata = pyqtSignal(str)

    def __init__(self, buf_a, buf_b, parent=None):
        super().__init__(parent)
        self._buf_a = buf_a  # geriye dönük compat - artık kullanılmıyor
        self._buf_b = buf_b  # geriye dönük compat - artık kullanılmıyor
        self._dur_event = threading.Event()
        self._onay_event = threading.Event()
        self._atis_mod = config.ASAMA_1["ATIS_MODU"]
        self._son_gimbal = ""  # son gimbal komutu (gereksiz tekrar önler)
        self._son_atis_t = 0.0  # son ateş zamanı (perf_counter saniye)
        self._son_faz_cam = {}  # {cam_idx: faz_str} - gereksiz emit önler
        self._lidar_m: float | None = None  # Son LiDAR ölçümü

        # İki kamera için ayrı kuyruklar (kamera A ve kamera B)
        self._queue_a: queue.Queue = queue.Queue(maxsize=4)
        self._queue_b: queue.Queue = queue.Queue(maxsize=4)
        # Geriye dönük uyumluluk: eski tekil queue (kamera A kuyruğuna yönlendir)
        self._queue = self._queue_a

    # Başlatma / Durdurma
    def baslat(self) -> None:
        self._dur_event.clear()
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

    # KameraHedefi listesi -> HedefBilgi listesi dönüşümü
    def _donustur(self, kh_listesi: list, cfg: dict,
                  imha_sirasi: list, dost_set: set,
                  nesne_filtre: list, kare_w: int, kare_h: int,
                  kamera_idx: int,
                  lidar_m: float | None) -> list[HedefBilgi]:
        hedefler: list[HedefBilgi] = []
        _renk_profil = set(config.ASAMA_3.get("RENK_PROFILLERI", {}).keys())

        for kh in kh_listesi:
            sinif = kh.sinif
            if nesne_filtre and sinif not in nesne_filtre:
                if sinif not in _renk_profil:
                    continue
            if sinif in _renk_profil:
                if kh.guven < cfg.get("BALON_MIN_GUVEN", 0.08):
                    continue
                if kh.bbox[2] * kh.bbox[3] < cfg.get("BALON_MIN_ALAN", 150):
                    continue

            is_dost = kh.dost or (sinif in dost_set)
            uz_m = getattr(kh, "uzaklik_m", None)  # det_thread'den gelen mesafe
            h = HedefBilgi(
                id=0, bbox=kh.bbox, sinif=sinif,
                guven=kh.guven, dost=is_dost,
                uzaklik_m=uz_m, kamera_idx=kamera_idx,
            )
            h.oncelik = _oncelik_skoru(sinif, kh.guven, kh.bbox,
                                       kare_w, kare_h, imha_sirasi)
            hedefler.append(h)

        # Birincil hedefe LiDAR mesafesi ata (sadece aynı kameradan geliyorsa)
        if lidar_m is not None and hedefler:
            birinci = next((x for x in hedefler if not x.dost), None)
            if birinci and birinci.uzaklik_m is None:
                birinci.uzaklik_m = lidar_m

        return hedefler

    # Ana döngü
    def run(self) -> None:
        from utils.stereo_konum import triangulate, fuz_uzaklik

        cfg = config.ASAMA_1
        self.faz_degisti.emit("TARAMA")
        log.info("Asama1Thread başladı (çift kuyruk, per-phase kamera).")

        kh_b_son: list = []  # Kamera B'nin son kare verisi

        while not self._dur_event.is_set():
            # Kamera A kuyruğunu bekle (0.1 s timeout)
            try:
                kh_a_listesi = self._queue_a.get(timeout=0.1)
            except queue.Empty:
                continue

            if config.ACIL_DURDUR_EVENT.is_set():
                continue

            # Kamera B - mevcut en güncel veri (bloklamaz)
            try:
                kh_b_son = self._queue_b.get_nowait()
            except queue.Empty:
                pass  # önceki kare kullanılmaya devam eder

            kare_w = config.UI_AYAR.get("KAMERA_GENISLIK", 1280)
            kare_h = config.UI_AYAR.get("KAMERA_YUKSEKLIK", 720)

            # Per-phase kamera konfigürasyonu
            # Kamera A öncelik/dost listesi
            imha_a = cfg.get("KAMERA_A_IMHA") or cfg.get("IMHA_SIRASI", [])
            dost_a = set(cfg.get("KAMERA_A_DOST") or cfg.get("DOST_SINIFLAR", []))
            filtre_a = cfg.get("NESNE_SINIFLARI", [])

            # Kamera B - kendi öncelik/dost listesi (A'dan bağımsız)
            imha_b = cfg.get("KAMERA_B_IMHA") or cfg.get("IMHA_SIRASI", [])
            dost_b = set(cfg.get("KAMERA_B_DOST") or cfg.get("DOST_SINIFLAR", []))

            lidar_su = self._lidar_m  # anlık LiDAR ölçümü (thread-safe kopyası)

            # Her iki kameranın verilerini ayrı ayrı dönüştür
            h_a = self._donustur(kh_a_listesi, cfg, imha_a, dost_a,
                                 filtre_a, kare_w, kare_h, 0, lidar_su)
            h_b = self._donustur(kh_b_son, cfg, imha_b, dost_b,
                                 filtre_a, kare_w, kare_h, 1, None)

            # Stereo triangülasyon: eşleşen hedefler için 3D konum
            if config.KAMERA_GEOMETRI.get("STEREO_ETKIN", False) and h_a and h_b:
                for ha in h_a:
                    if ha.dost or ha.uzaklik_m is not None:
                        continue
                    bx, by, bw, bh = ha.bbox
                    u_a = bx + bw / 2.0
                    # En yakın eşleşen kamera B hedefini bul (sınıf adı eşleşmesi)
                    eslesme = next(
                        (hb for hb in h_b
                         if hb.sinif == ha.sinif and not hb.dost), None)
                    if eslesme:
                        bx2, by2, bw2, bh2 = eslesme.bbox
                        u_b = bx2 + bw2 / 2.0
                        sonuc = triangulate(u_a, u_b, kare_w, kare_w)
                        if sonuc:
                            tx, ty, dist_m = sonuc
                            ha.konum_3d = (tx, ty, 0.0)
                            ha.uzaklik_m = fuz_uzaklik(dist_m, lidar_su
                                                       if ha is h_a[0] else None)

            sinifler_a = {(h.sinif, h.kamera_idx) for h in h_a}
            for hb in h_b:
                if (hb.sinif, 0) not in sinifler_a:
                    h_a.append(hb)

            hedefler = h_a
            hedefler.sort(key=lambda x: x.oncelik, reverse=True)
            for rank, h in enumerate(hedefler, start=1):
                h.id = rank

            self.hedef_listesi.emit(hedefler)

            # Per-camera motor komut filtresi
            frame_cx = kare_w // 2
            frame_cy = kare_h // 2
            don_cfg = config.DONANIM
            lox = don_cfg.get("LAZER_OFFSET_X", 0)
            loy = don_cfg.get("LAZER_OFFSET_Y", 0)

            # Her kamera için izin verilen hedefleri filtrele
            def _motor_izinli(h: HedefBilgi) -> bool:
                if h.dost:
                    return False
                cam = config.KAMERA_AYARLAR[h.kamera_idx] if h.kamera_idx < len(config.KAMERA_AYARLAR) else {}
                if not cam.get("MOTOR_KOMUT_ETKIN", True):
                    return False
                min_g = cam.get("MOTOR_KOMUT_MIN_GUVEN", 0.25)
                if h.guven < min_g:
                    return False
                sinif_f = cam.get("MOTOR_KOMUT_SINIF", [])
                if sinif_f and h.sinif not in sinif_f:
                    return False
                return True

            # İzin verilen adayları önceliğe göre sırala
            # (düşük MOTOR_KOMUT_ONCELIK = önce)
            motor_adaylar = [h for h in hedefler if _motor_izinli(h)]
            motor_adaylar.sort(key=lambda h: (
                config.KAMERA_AYARLAR[h.kamera_idx].get("MOTOR_KOMUT_ONCELIK", 0)
                if h.kamera_idx < len(config.KAMERA_AYARLAR) else 0,
                -h.oncelik
            ))
            gimbal_hedef = motor_adaylar[0] if motor_adaylar else None

            if gimbal_hedef:
                bx, by, bw, bh = gimbal_hedef.bbox
                hx = bx + bw // 2
                hy = by + bh // 2
                error_x = (hx - frame_cx) - lox
                error_y = (hy - frame_cy) - loy
                kp = don_cfg.get("KP_X", 3.0)
                max_adim = don_cfg.get("MAX_STEPS_X", 500)
                dz = don_cfg.get("DEAD_ZONE_PIXEL", 8)
                ax = _hata_to_adim(error_x, kp, max_adim, dz)
                ay = _hata_to_adim(error_y, kp, max_adim, dz)
                # Format config'den okunur - runtime'da değiştirilebilir
                _fmt = don_cfg.get("GIMBAL_FORMAT", "!X{x}Y{y}*")
                yeni_gimbal = _fmt.format(x=ax, y=ay)
            else:
                yeni_gimbal = don_cfg.get("GIMBAL_DUR_FORMAT", "!X0Y0*")

            if yeni_gimbal != self._son_gimbal:
                _gimbal_gonder_ham(yeni_gimbal)
                self._son_gimbal = yeni_gimbal

            # Per-camera faz güncelle
            if gimbal_hedef:
                # Hedef olan kamera NISAN/TAKİP - diğerleri TARAMA
                for _ci in range(len(config.KAMERALAR)):
                    _yeni_faz = "NISAN" if _ci == gimbal_hedef.kamera_idx else "TARAMA"
                    if self._son_faz_cam.get(_ci) != _yeni_faz:
                        self._son_faz_cam[_ci] = _yeni_faz
                        self.faz_degisti_cam.emit(_ci, _yeni_faz)
            else:
                # Hedef yok - tüm kameralar TARAMA
                for _ci in range(len(config.KAMERALAR)):
                    if self._son_faz_cam.get(_ci) != "TARAMA":
                        self._son_faz_cam[_ci] = "TARAMA"
                        self.faz_degisti_cam.emit(_ci, "TARAMA")

            # Ateş kararı
            if gimbal_hedef:
                self._imha_et(gimbal_hedef)
            else:
                self._onay_event.clear()

        log.info("Asama1Thread durdu.")

    # Yardımcı metodlar
    def _imha_et(self, h: HedefBilgi) -> None:
        if self._atis_mod == "OTONOM":
            self._ates_ver(h)
        elif self._onay_event.is_set():
            # manuel modda operator onay butonuna bastiysa bir kere ates
            self._onay_event.clear()
            self._ates_ver(h)

    def _ates_ver(self, h: HedefBilgi) -> None:
        # Ateş hızı sınırı - STM32'yi flood'dan koru, motor kilitlenmesini önle
        now = time.perf_counter()
        aralik = float(config.ASAMA_1.get("ATIS_ARALIK", 1.5))
        if now - self._son_atis_t < aralik:
            return
        self._son_atis_t = now
        self.imha_komutu.emit({
            "id": h.id, "bbox": h.bbox, "sinif": h.sinif,
            "uzaklik_m": h.uzaklik_m, "kamera_idx": h.kamera_idx,
        })
        ates_komutu(h.id, h.bbox, h.sinif)
