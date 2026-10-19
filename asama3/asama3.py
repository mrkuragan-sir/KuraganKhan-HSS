from __future__ import annotations

import enum
import queue
import threading
import logging
import time
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

import config
from donanim import ates_komutu

log = logging.getLogger(__name__)

# Renk/sekil modulu (ayni paket icinde)
try:
    from .renk_sekil import AlgilamaHedfi, algi_kareleri
except ImportError:
    AlgilamaHedfi = None
    algi_kareleri = None
    log.warning("[Asama3] renk_sekil modulu yuklenemedi — sadece YOLO modu aktif")


class AramaDurum(enum.Enum):
    BEKLE = "bekle"
    ARAMA = "arama"
    TESPIT = "tespit"
    KILIT = "kilit"
    IMHA = "imha"


@dataclass
class Asama3Hedef:
    id: int
    bbox: tuple  # (x, y, w, h) piksel
    sinif: str
    guven: float
    renk: Optional[str] = None  # Renk tespitinden gelen renk adi
    sekil: Optional[str] = None  # Renk tespitinden gelen sekil adi
    dost: bool = False
    uzaklik_m: Optional[float]= None
    konum_3d: Optional[tuple]= None
    kamera_idx: int = 0
    kilit_sayac: int = 0  # Ard arda kilit frame sayisi


class PIDYonelme:

    def __init__(
        self,
        kp: float = 0.05,
        ki: float = 0.001,
        kd: float = 0.01,
        max_adim: int = 300,
        dead_zone: int = 8,
    ) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_adim = max_adim
        self.dead_zone = dead_zone
        self._hata_sum_x = 0.0
        self._hata_sum_y = 0.0
        self._onceki_hata_x = 0.0
        self._onceki_hata_y = 0.0
        self._son_t = time.perf_counter()

    def hesapla(self, hata_x: float, hata_y: float) -> tuple[int, int]:
        su_an = time.perf_counter()
        dt = max(0.001, su_an - self._son_t)
        self._son_t = su_an

        def _pid(hata, hata_sum, onceki_hata):
            if abs(hata) < self.dead_zone:
                return 0, 0.0, hata
            hata_sum += hata * dt
            hata_sum = max(-500.0, min(500.0, hata_sum))
            d_hata = (hata - onceki_hata) / dt
            cikti = self.kp * hata + self.ki * hata_sum + self.kd * d_hata
            return int(max(-self.max_adim, min(self.max_adim, cikti))), hata_sum, hata

        ax, self._hata_sum_x, self._onceki_hata_x = _pid(
            hata_x, self._hata_sum_x, self._onceki_hata_x)
        ay, self._hata_sum_y, self._onceki_hata_y = _pid(
            hata_y, self._hata_sum_y, self._onceki_hata_y)

        return ax, ay

    def sifirla(self) -> None:
        self._hata_sum_x = 0.0
        self._hata_sum_y = 0.0
        self._onceki_hata_x = 0.0
        self._onceki_hata_y = 0.0
        self._son_t = time.perf_counter()


class KilitYoneticisi:

    def __init__(self) -> None:
        self._sayac = 0
        self._merkez_esigi = config.ASAMA_3.get("KILIT_MERKEZ_ESIGI", 12)
        self._gerek = config.ASAMA_3.get("KILIT_GEREK", 5)

    def guncelle(self, hata_x: float, hata_y: float) -> bool:
        hata = (hata_x ** 2 + hata_y ** 2) ** 0.5
        if hata <= self._merkez_esigi:
            self._sayac += 1
        else:
            self._sayac = 0
        return self._sayac >= self._gerek

    def sifirla(self) -> None:
        self._sayac = 0


class AramaYoneticisi:

    def __init__(self) -> None:
        self._durum = AramaDurum.BEKLE
        self._baslangic_t: float = 0.0
        self._arama_sure = config.ASAMA_3.get("ARAMA_SURE", 10.0)
        self._strateji = config.ASAMA_3.get("ARAMA_STRATEJISI", "spiral")
        self._spiral_adim = config.ASAMA_3.get("SPIRAL_ADIM", 15)
        self._spiral_r = 0
        self._spiral_aci = 0.0

    @property
    def durum(self) -> AramaDurum:
        return self._durum

    def gecis(self, yeni: AramaDurum) -> None:
        if self._durum != yeni:
            log.debug("[AramaFSM] %s -> %s", self._durum.value, yeni.value)
            self._durum = yeni
            self._baslangic_t = time.perf_counter()

    def sure_doldu_mu(self) -> bool:
        return (time.perf_counter() - self._baslangic_t) >= self._arama_sure

    def spiral_adim_hesapla(self) -> tuple[int, int]:
        import math
        if self._strateji == "raster":
            # Basit sol-sag tarama
            adim = self._spiral_adim
            return adim, 0
        # Spiral
        self._spiral_r += 0.5
        self._spiral_aci += 0.3
        dx = int(self._spiral_r * math.cos(self._spiral_aci) * self._spiral_adim / 15)
        dy = int(self._spiral_r * math.sin(self._spiral_aci) * self._spiral_adim / 15)
        return dx, dy

    def sifirla(self) -> None:
        self._durum = AramaDurum.BEKLE
        self._spiral_r = 0
        self._spiral_aci = 0.0


class Asama3Thread(QThread):

    # Sinyaller
    hedef_listesi = pyqtSignal(list)  # list[Asama3Hedef]
    siniflar_hazir = pyqtSignal(list)  # geriye donuk uyumluluk
    imha_komutu = pyqtSignal(dict)  # {id, bbox, sinif, renk, sekil, uzaklik_m}
    faz_degisti = pyqtSignal(str)  # global faz
    faz_degisti_cam = pyqtSignal(int, str)  # per-camera faz
    hata = pyqtSignal(str)
    fsm_durum = pyqtSignal(str)  # AramaDurum string (UI icin)

    def __init__(self, buf_a, buf_b, parent=None):
        super().__init__(parent)
        self._buf_a = buf_a
        self._buf_b = buf_b
        self._dur_event = threading.Event()
        self._onay_event = threading.Event()
        self._onay_bas_t: Optional[float] = None
        self._atis_mod = config.ASAMA_3.get("ATIS_MODU", "MANUEL")
        self._lidar_m: Optional[float] = None
        self._son_gimbal = ""
        self._son_atis_t = 0.0
        self._son_faz_cam: dict[int, str] = {}
        self._kare_sayaci: dict[int, int] = {}  # kamera_idx -> frame count

        # Dual kuyruk
        self._queue_a: queue.Queue = queue.Queue(maxsize=4)
        self._queue_b: queue.Queue = queue.Queue(maxsize=4)
        self._queue = self._queue_a  # geriye donuk compat

        # Asama 3 ozgul bilesenler
        self._fsm = AramaYoneticisi()
        self._pid = PIDYonelme(
            kp=0.05, ki=0.001, kd=0.01,
            max_adim=config.DONANIM.get("MAX_STEPS_X", 300),
            dead_zone=config.ASAMA_3.get("DEAD_ZONE_PIXEL", 6),
        )
        self._kilit = KilitYoneticisi()
        self._aktif_hedef: Optional[Asama3Hedef] = None


    def baslat(self) -> None:
        self._dur_event.clear()
        self.start()

    def dur(self) -> None:
        self._dur_event.set()
        self.wait(5000)


    def mod_ayarla(self, mod: str) -> None:
        self._atis_mod = mod

    def manuel_onayla(self) -> None:
        self._onay_event.set()


    def _queue_koy(self, q: queue.Queue, hedefler: list) -> None:
        while not q.empty():
            try:
                q.get_nowait()
            except queue.Empty:
                break
        try:
            q.put_nowait(hedefler)
        except queue.Full:
            pass

    def hedef_listesi_al(self, hedefler: list) -> None:
        self._queue_koy(self._queue_a, hedefler)

    def hedef_listesi_al_b(self, hedefler: list) -> None:
        self._queue_koy(self._queue_b, hedefler)

    def lidar_guncelle(self, mesafe_m: float) -> None:
        self._lidar_m = mesafe_m


    def _gimbal_gonder(self, ax: int, ay: int) -> None:
        fmt = config.DONANIM.get("GIMBAL_FORMAT", "!X{x}Y{y}*")
        mesaj = fmt.format(x=ax, y=ay)
        if mesaj == self._son_gimbal:
            return
        self._son_gimbal = mesaj
        try:
            from motor import MotorKontrol
            m = MotorKontrol.get_instance()
            if m and m.bagli_mi():
                m._gonder(mesaj + "\n")
        except Exception:
            pass

    def _gimbal_dur(self) -> None:
        dur_fmt = config.DONANIM.get("GIMBAL_DUR_FORMAT", "!X0Y0*")
        try:
            from motor import MotorKontrol
            m = MotorKontrol.get_instance()
            if m and m.bagli_mi():
                m._gonder(dur_fmt + "\n")
        except Exception:
            pass
        self._son_gimbal = ""


    def _donustur(
        self,
        kh_listesi: list,
        dost_set: set,
        nesne_filtre: list,
        kamera_idx: int,
    ) -> list[Asama3Hedef]:
        hedefler: list[Asama3Hedef] = []
        guven_esigi = config.ASAMA_3.get("GUVEN_ESIGI", 0.65)
        imha_sirasi = (
            config.ASAMA_3.get("KAMERA_A_IMHA", []) if kamera_idx == 0
            else config.ASAMA_3.get("KAMERA_B_IMHA", [])
        )

        for kh in kh_listesi:
            sinif = kh.sinif
            if nesne_filtre and sinif not in nesne_filtre:
                continue
            if kh.guven < guven_esigi:
                continue

            is_dost = kh.dost or (sinif in dost_set)
            uz_m = getattr(kh, "uzaklik_m", None)
            if uz_m is None:
                uz_m = self._lidar_m

            h = Asama3Hedef(
                id=getattr(kh, "id", 0),
                bbox=kh.bbox,
                sinif=sinif,
                guven=kh.guven,
                dost=is_dost,
                uzaklik_m=uz_m,
                kamera_idx=kamera_idx,
            )
            hedefler.append(h)

        if imha_sirasi:
            son = len(imha_sirasi)
            hedefler.sort(key=lambda h: imha_sirasi.index(h.sinif) if h.sinif in imha_sirasi else son)
        return hedefler


    def _renk_tarama_uygula(
        self,
        hedefler: list[Asama3Hedef],
        frame_bgr,
    ) -> list[Asama3Hedef]:
        if algi_kareleri is None or frame_bgr is None:
            return hedefler

        try:
            tespitler = algi_kareleri(frame_bgr)
        except Exception as e:
            log.debug("[Asama3] renk algilama hatasi: %s", e)
            return hedefler

        # Mevcut YOLO hedeflerine renk bilgisi esle
        imha_esigi = config.ASAMA_3.get("IMHA_GUVEN_ESIGI", 0.65)
        for h in hedefler:
            bx, by, bw, bh = h.bbox
            hcx = bx + bw // 2
            hcy = by + bh // 2
            for t in tespitler:
                tx1, ty1, tx2, ty2 = t.bbox
                if tx1 <= hcx <= tx2 and ty1 <= hcy <= ty2:
                    h.renk = t.renk
                    h.sekil = t.sekil
                    # Guven artisi: renk/sekil onayladiysa
                    if t.guven >= imha_esigi:
                        h.guven = min(1.0, h.guven * 1.1)
                    break

        # Ek: sadece renk/sekil ile bulunan ama YOLO'nin gormediği hedefler
        # (kucuk veya hizli hareket eden, modelin kacirdigi) - opsiyonel
        mevcut_merkezler = set()
        for h in hedefler:
            bx, by, bw, bh = h.bbox
            mevcut_merkezler.add((bx + bw // 2, by + bh // 2))

        imha_esigi_guven = config.ASAMA_3.get("IMHA_GUVEN_ESIGI", 0.65)
        for t in tespitler:
            if t.guven < imha_esigi_guven:
                continue
            tx1, ty1, tx2, ty2 = t.bbox
            tcx = (tx1 + tx2) // 2
            tcy = (ty1 + ty2) // 2
            # Mevcut bir YOLO hedefine cok yakinsa atla
            cakisma = any(
                abs(tcx - mcx) < 40 and abs(tcy - mcy) < 40
                for mcx, mcy in mevcut_merkezler
            )
            if not cakisma:
                tw = tx2 - tx1
                th = ty2 - ty1
                h_yeni = Asama3Hedef(
                    id=-(len(hedefler) + 1),  # Negatif ID = saf renk tespiti
                    bbox=(tx1, ty1, tw, th),
                    sinif=f"{t.renk}_{t.sekil}",
                    guven=t.guven,
                    renk=t.renk,
                    sekil=t.sekil,
                    dost=False,
                    uzaklik_m=self._lidar_m,
                )
                hedefler.append(h_yeni)

        return hedefler


    def _fsm_isle(
        self,
        hedefler: list[Asama3Hedef],
        kare_w: int,
        kare_h: int,
    ) -> None:
        durum = self._fsm.durum

        if durum == AramaDurum.BEKLE:
            # Herhangi bir dusmanhedef varsa ARAMA'ya gec
            dusman_var = any(not h.dost for h in hedefler)
            if dusman_var:
                self._fsm.gecis(AramaDurum.ARAMA)
                self._pid.sifirla()
                self._kilit.sifirla()
            return

        if durum == AramaDurum.ARAMA:
            # Hedef bulunduysa TESPIT'e gec
            aday = next((h for h in hedefler if not h.dost), None)
            if aday:
                self._aktif_hedef = aday
                self._fsm.gecis(AramaDurum.TESPIT)
                return
            # Sure dolduysa BEKLE'ye geri don
            if self._fsm.sure_doldu_mu():
                log.debug("[Asama3] Arama suresi doldu, BEKLE'ye donuluyor")
                self._fsm.gecis(AramaDurum.BEKLE)
                self._gimbal_dur()
                return
            # Arama hareketi
            dx, dy = self._fsm.spiral_adim_hesapla()
            self._gimbal_gonder(dx, dy)
            return

        if durum == AramaDurum.TESPIT:
            # Aktif hedef hala goruluyorsa KILIT'e gecmeye calis
            if not hedefler:
                self._fsm.gecis(AramaDurum.ARAMA)
                return
            aday = next((h for h in hedefler if not h.dost), None)
            if aday is None:
                self._fsm.gecis(AramaDurum.ARAMA)
                return
            self._aktif_hedef = aday
            # Gimbal hizala
            bx, by, bw, bh = aday.bbox
            merkez_x = bx + bw // 2
            merkez_y = by + bh // 2
            hata_x = merkez_x - kare_w // 2
            hata_y = merkez_y - kare_h // 2
            ax, ay = self._pid.hesapla(hata_x, hata_y)
            self._gimbal_gonder(ax, ay)
            # Kilit kontrolu
            kilit_saglandı = self._kilit.guncelle(hata_x, hata_y)
            if kilit_saglandı:
                self._fsm.gecis(AramaDurum.KILIT)
            return

        if durum == AramaDurum.KILIT:
            if not hedefler:
                self._fsm.gecis(AramaDurum.ARAMA)
                self._kilit.sifirla()
                return
            aday = next((h for h in hedefler if not h.dost), None)
            if aday is None:
                self._fsm.gecis(AramaDurum.ARAMA)
                self._kilit.sifirla()
                return
            self._aktif_hedef = aday
            # Gimbal ince ayar
            bx, by, bw, bh = aday.bbox
            hata_x = (bx + bw // 2) - kare_w // 2
            hata_y = (by + bh // 2) - kare_h // 2
            ax, ay = self._pid.hesapla(hata_x, hata_y)
            self._gimbal_gonder(ax, ay)
            # Kilit hala saglaniyor mu?
            if not self._kilit.guncelle(hata_x, hata_y):
                self._fsm.gecis(AramaDurum.TESPIT)
                return
            # IMHA'ya gec
            self._fsm.gecis(AramaDurum.IMHA)
            return

        if durum == AramaDurum.IMHA:
            h = self._aktif_hedef
            if h is None:
                self._fsm.gecis(AramaDurum.BEKLE)
                return

            guven_esigi = config.ASAMA_3.get("IMHA_GUVEN_ESIGI", 0.65)
            imha_onay = h.guven >= guven_esigi

            if self._atis_mod == "OTONOM" and imha_onay:
                self._ates_et(h)
            elif self._atis_mod == "MANUEL":
                # Onay sinyali bekle (zaman asimi: MANUEL_ONAY_TIMEOUT)
                timeout = config.ASAMA_3.get("MANUEL_ONAY_TIMEOUT", 3.0)
                simdi = time.perf_counter()
                if self._onay_bas_t is not None:
                    if self._onay_event.is_set():
                        self._onay_event.clear()
                        self._onay_bas_t = None
                        self._ates_et(h)
                    elif simdi - self._onay_bas_t > timeout:
                        log.info("[Asama3] manuel onay zaman asimi, tekrar sorulacak: id=%s", h.id)
                        self._onay_bas_t = None
                else:
                    self._onay_bas_t = simdi
                    self._onay_event.clear()
                    # Onay bekleniyor - imha_komutu sinyali gonder (UI onay icin)
                    self.imha_komutu.emit({
                        "id": h.id,
                        "bbox": h.bbox,
                        "sinif": h.sinif,
                        "renk": h.renk,
                        "sekil": h.sekil,
                        "uzaklik_m": h.uzaklik_m,
                        "onay_bekleniyor": True,
                    })

            # Hedef hala varsa KILIT'e don, yoksa BEKLE
            if any(not hh.dost for hh in hedefler):
                self._fsm.gecis(AramaDurum.KILIT)
                self._kilit.sifirla()
            else:
                self._fsm.gecis(AramaDurum.BEKLE)
                self._aktif_hedef = None

    def _ates_et(self, h: Asama3Hedef) -> None:
        atis_aralik = config.ASAMA_3.get("ATIS_ARALIK", 1.5)
        su_an = time.perf_counter()
        if su_an - self._son_atis_t < atis_aralik:
            return
        self._son_atis_t = su_an
        try:
            ates_komutu(h.id, h.bbox, h.sinif)
        except Exception as e:
            log.warning("[Asama3] ates komutu hatasi: %s", e)
        self.imha_komutu.emit({
            "id": h.id,
            "bbox": h.bbox,
            "sinif": h.sinif,
            "renk": h.renk,
            "sekil": h.sekil,
            "uzaklik_m": h.uzaklik_m,
            "onay_bekleniyor": False,
        })
        log.info("[Asama3] ATES EDILDI: id=%d sinif=%s renk=%s uzaklik=%.1fm",
                 h.id, h.sinif, h.renk, h.uzaklik_m or -1)


    def _isleme_birimi(
        self,
        q: queue.Queue,
        kamera_idx: int,
        kare_w: int,
        kare_h: int,
    ) -> list[Asama3Hedef]:
        kh_listesi = None
        while True:
            try:
                kh_listesi = q.get_nowait()
            except queue.Empty:
                break

        if kh_listesi is None:
            return []

        asama_cfg = config.ASAMA_3
        dost_set = set(
            asama_cfg.get("KAMERA_A_DOST", []) if kamera_idx == 0
            else asama_cfg.get("KAMERA_B_DOST", [])
        )
        nesne_filtre = asama_cfg.get("NESNE_SINIFLARI", [])
        hedefler = self._donustur(kh_listesi, dost_set, nesne_filtre, kamera_idx)

        # Renk/sekil zenginlestirme (frame yoksa atla)
        return hedefler


    def run(self) -> None:
        log.info("[Asama3] Thread baslatildi")
        kare_w = config.UI_AYAR.get("KAMERA_GENISLIK", 1280)
        kare_h = config.UI_AYAR.get("KAMERA_YUKSEKLIK", 720)
        son_fsm_str = ""

        while not self._dur_event.is_set():
            hedefler_a = self._isleme_birimi(self._queue_a, 0, kare_w, kare_h)
            hedefler_b = self._isleme_birimi(self._queue_b, 1, kare_w, kare_h)
            hedefler_birlestik = hedefler_a + hedefler_b

            # FSM adimi
            self._fsm_isle(hedefler_birlestik, kare_w, kare_h)

            # FSM durum sinyali (UI icin)
            fsm_str = self._fsm.durum.value
            if fsm_str != son_fsm_str:
                self.fsm_durum.emit(fsm_str)
                son_fsm_str = fsm_str

            # Hedef listesi sinyali
            if hedefler_birlestik:
                self.hedef_listesi.emit(hedefler_birlestik)

            # Kamera faz sinyali
            for kamera_idx, hedefler in ((0, hedefler_a), (1, hedefler_b)):
                dusman = [h for h in hedefler if not h.dost]
                dost = [h for h in hedefler if h.dost]
                if dusman:
                    faz = "takip"
                elif dost:
                    faz = "dost"
                else:
                    faz = "bosta"
                if self._son_faz_cam.get(kamera_idx) != faz:
                    self._son_faz_cam[kamera_idx] = faz
                    self.faz_degisti_cam.emit(kamera_idx, faz)

            self._dur_event.wait(timeout=0.033)  # ~30 FPS

        self._gimbal_dur()
        log.info("[Asama3] Thread durduruldu")
