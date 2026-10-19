
import logging
import threading
import config

log = logging.getLogger("donanim")

# Aktif "ateş dur" zamanlayıcısı - birden fazla tetikleme üst üste açılmasın
_ates_dur_timer: threading.Timer | None = None
_ates_dur_lock = threading.Lock()


def _motor_al():
    if not config.DONANIM.get("PORT", ""):
        return None
    from motor import MotorKontrol
    return MotorKontrol.get_instance()


def ates_komutu(hedef_id: int, bbox: tuple, sinif: str) -> None:
    global _ates_dur_timer

    log.info("ATES hedef_id=%d sinif=%s bbox=%s", hedef_id, sinif, bbox)
    m = _motor_al()
    if not m:
        return

    # Ateş başlat
    m.ates_komutu(hedef_id)

    # Önceki zamanlayıcıyı iptal et (aksi halde üst üste "dur" gelebilir)
    with _ates_dur_lock:
        if _ates_dur_timer is not None:
            _ates_dur_timer.cancel()

        atis_sure = config.MOTOR_KONTROL.get("ATES_SURE_MS", 500) / 1000.0
        dur_komut = config.MOTOR_KONTROL.get("ATES_DUR_KOMUTU", "atisdur\n")

        def _gonder_dur():
            try:
                _m = _motor_al()
                if _m and _m.bagli_mi():
                    _m._gonder(dur_komut)
                    log.debug("ATES_DUR gönderildi")
            except Exception as _e:
                log.warning("ATES_DUR hatası: %s", _e)

        _ates_dur_timer = threading.Timer(atis_sure, _gonder_dur)
        _ates_dur_timer.daemon = True
        _ates_dur_timer.start()


def gimbal_hareket(dx: float, dy: float) -> None:
    m = _motor_al()
    if m:
        m.gimbal_hareket(dx, dy)


def ates_dur_komutu() -> None:
    global _ates_dur_timer
    with _ates_dur_lock:
        if _ates_dur_timer is not None:
            _ates_dur_timer.cancel()
            _ates_dur_timer = None
    m = _motor_al()
    if not m:
        return
    dur_komut = config.MOTOR_KONTROL.get("ATES_DUR_KOMUTU", "atisdur\n")
    m._gonder(dur_komut)
    log.info("ATES_DUR manuel komutu gönderildi")


def sistem_durdur() -> None:
    log.warning("ACİL_DURDUR komutu")
    m = _motor_al()
    if m:
        m.acil_durdur()
