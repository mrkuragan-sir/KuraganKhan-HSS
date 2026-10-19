import logging
from enum import Enum, auto

from PyQt6.QtCore import QObject, pyqtSignal

from donanim import sistem_durdur

log = logging.getLogger(__name__)


class SistemAsama(Enum):
    DURDURULDU = auto()
    ASAMA_1 = auto()
    ASAMA_2 = auto()
    ASAMA_3 = auto()


class SistemFSM(QObject):
    asama_degisti = pyqtSignal(str)
    acil_durdur_sig = pyqtSignal()

    def __init__(self, a1, a2, a3=None, det_threads=None, parent=None):
        super().__init__(parent)
        self._threads = {
            SistemAsama.ASAMA_1: a1,
            SistemAsama.ASAMA_2: a2,
        }
        if a3 is not None:
            self._threads[SistemAsama.ASAMA_3] = a3
        self._det_threads = det_threads or []  # KameraDeteksiyonThread listesi
        self._aktif = SistemAsama.DURDURULDU

    # Per-phase kamera config propagasyonu
    def _kamera_cfg_uygula(self, hedef: SistemAsama) -> None:
        import config
        _faz_map = {
            SistemAsama.ASAMA_1: config.ASAMA_1,
            SistemAsama.ASAMA_2: config.ASAMA_2,
            SistemAsama.ASAMA_3: config.ASAMA_3,
        }
        faz_cfg = _faz_map.get(hedef)
        if faz_cfg is None:
            return  # DURDURULDU -> değişiklik yok

        _cam_keys = [
            ("KAMERA_A_DOST", "KAMERA_A_IMHA", "KAMERA_A_MODEL", 0),
            ("KAMERA_B_DOST", "KAMERA_B_IMHA", "KAMERA_B_MODEL", 1),
        ]
        for dost_key, imha_key, model_key, cam_idx in _cam_keys:
            if cam_idx >= len(self._det_threads):
                continue
            ayar = self._det_threads[cam_idx]._ayar  # canlı dict referansı

            # Dost sınıfları - per-phase override, boşsa global
            dost_list = faz_cfg.get(dost_key) or config.KAMERA_AYARLAR[cam_idx].get("DOST_SINIFLAR", [])
            ayar["DOST_SINIFLAR"] = list(dost_list)

            # İmha sırası - per-phase override, boşsa global
            imha_list = faz_cfg.get(imha_key) or config.KAMERA_AYARLAR[cam_idx].get("IMHA_SIRASI", [])
            ayar["IMHA_SIRASI"] = list(imha_list)

            # Model yolu - per-phase override, boşsa global kamera modeli
            model_ov = faz_cfg.get(model_key, "").strip()
            if model_ov:
                ayar["MODEL_YOLU"] = model_ov
                log.info("Faz %s → Kamera %d model override: %s",
                         hedef.name, cam_idx, model_ov)

        log.info("Faz %s kamera config'leri uygulandı.", hedef.name)

    def gecis(self, hedef: SistemAsama | int | None) -> None:
        if isinstance(hedef, int):
            mapping = {
                1: SistemAsama.ASAMA_1,
                2: SistemAsama.ASAMA_2,
                3: SistemAsama.ASAMA_3,
            }
            hedef = mapping.get(hedef, SistemAsama.DURDURULDU)
        if hedef is None:
            hedef = SistemAsama.DURDURULDU

        if self._aktif in self._threads:
            try:
                self._threads[self._aktif].dur()
            except Exception as e:
                log.warning("Thread durdurma hatası: %s", e)

        self._aktif = hedef
        if hedef in self._threads:
            self._kamera_cfg_uygula(hedef)  # detection thread ayarlarını güncelle
            self._threads[hedef].baslat()
            log.info("Sistem geçiş: %s", hedef.name)
        self.asama_degisti.emit(hedef.name)

    def acil_durdur(self) -> None:
        for t in self._threads.values():
            try:
                t.dur()
            except Exception:
                pass
        self._aktif = SistemAsama.DURDURULDU
        sistem_durdur()
        self.acil_durdur_sig.emit()
        log.warning("ACIL DURDUR tetiklendi.")

    @property
    def aktif(self) -> SistemAsama:
        return self._aktif
