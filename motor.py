
import threading
import logging
import time
from collections import deque
from typing import Optional

# Global komut log tamponu (tüm gönderimler)
_KOMUT_LOG: deque = deque(maxlen=500)  # (timestamp_str, komut_str, ok: bool)

log = logging.getLogger(__name__)

try:
    import serial
    _SERIAL_OK = True
except ImportError:
    _SERIAL_OK = False
    log.warning("pyserial bulunamadı — motor komutları devre dışı. pip install pyserial")

_RECONNECT_ARALIK = 2.0  # saniye - bağlantı kopunca yeniden deneme aralığı


class MotorKontrol:

    _instance: Optional["MotorKontrol"] = None
    _cls_lock = threading.Lock()

    # Singleton
    @classmethod
    def get_instance(cls) -> "MotorKontrol":
        with cls._cls_lock:
            if cls._instance is None:
                import config
                cfg = config.DONANIM
                cls._instance = cls(
                    port=cfg.get("PORT", ""),
                    baud=cfg.get("BAUD_RATE", 115200),
                    protokol=cfg.get("PROTOKOL", "stm32"),
                )
            return cls._instance

    @classmethod
    def port_degistir(cls, yeni_port: str) -> "MotorKontrol":
        with cls._cls_lock:
            if cls._instance is not None:
                cls._instance._durdur_reconnect()
                cls._instance.kapat()
                cls._instance = None
            import config
            config.DONANIM["PORT"] = yeni_port
            cls._instance = cls(
                port=yeni_port,
                baud=config.DONANIM.get("BAUD_RATE", 115200),
                protokol=config.DONANIM.get("PROTOKOL", "stm32"),
            )
            return cls._instance

    # Init
    def __init__(self, port: str, baud: int = 115200,
                 protokol: str = "stm32"):
        self._port = port
        self._baud = baud
        self._protokol = protokol
        self._ser = None
        self._gonder_lock = threading.Lock()
        self._bagli = False
        self._calisiyor = True  # reconnect thread kontrolü

        if port:
            self._baglan()
            if not self._bagli:
                self._basla_reconnect()  # ilk bağlanma başarısız -> arka plan dene

    # Bağlantı
    def _baglan(self) -> None:
        if not _SERIAL_OK or not self._port:
            return
        try:
            if self._ser and self._ser.is_open:
                self._ser.close()
            self._ser = serial.Serial(self._port, self._baud, timeout=0, write_timeout=0)
            self._bagli = True
            log.info("Motor bağlantısı açıldı: %s @ %d baud", self._port, self._baud)
        except Exception as e:
            log.error("Motor bağlantı hatası (%s): %s", self._port, e)
            self._bagli = False

    def baglan(self) -> bool:
        self._baglan()
        if self._bagli:
            self._durdur_reconnect()
        else:
            self._basla_reconnect()
        return self._bagli

    def bagli_mi(self) -> bool:
        return self._bagli and self._ser is not None and self._ser.is_open

    def kapat(self) -> None:
        self._calisiyor = False
        if self._ser and self._ser.is_open:
            try:
                self._ser.close()
            except Exception:
                pass
        self._bagli = False

    # Otomatik yeniden bağlanma
    def _basla_reconnect(self) -> None:
        t = threading.Thread(target=self._reconnect_dongusu,
                             daemon=True, name="MotorReconnect")
        t.start()

    def _durdur_reconnect(self) -> None:
        self._calisiyor = False

    def _reconnect_dongusu(self) -> None:
        deneme = 0
        while self._calisiyor and not self.bagli_mi():
            time.sleep(_RECONNECT_ARALIK)
            if not self._calisiyor:
                break
            if not self.bagli_mi() and self._port:
                deneme += 1
                if deneme == 1 or deneme % 5 == 0:  # ilk ve her 5. denemede log
                    log.warning("Motor yeniden bağlanma denemesi #%d: %s", deneme, self._port)
                self._baglan_sessiz(deneme)
        if self._bagli:
            log.info("Motor yeniden bağlandı: %s", self._port)

    def _baglan_sessiz(self, deneme: int) -> None:
        if not _SERIAL_OK or not self._port:
            return
        try:
            if self._ser and self._ser.is_open:
                self._ser.close()
            self._ser = serial.Serial(self._port, self._baud, timeout=0, write_timeout=0)
            self._bagli = True
        except Exception as e:
            if deneme == 1 or deneme % 5 == 0:
                log.warning("Motor bağlantı hatası #%d (%s): %s", deneme, self._port, e)
            self._bagli = False

    # Komut gönderme
    def _gonder(self, komut: str) -> bool:
        if not self.bagli_mi():
            log.debug("Motor bağlı değil, komut atlandı: %r", komut.strip())
            _KOMUT_LOG.append((time.strftime("%H:%M:%S"), komut.strip(), False))
            return False
        with self._gonder_lock:
            try:
                self._ser.write(komut.encode("ascii"))
                self._ser.flush()  # buffer'ı hemen gönder
                _KOMUT_LOG.append((time.strftime("%H:%M:%S"), komut.strip(), True))
                return True
            except Exception as e:
                log.error("Motor gönderim hatası: %s", e)
                _KOMUT_LOG.append((time.strftime("%H:%M:%S"), komut.strip(), False))
                self._bagli = False
                self._calisiyor = True  # reconnect'e izin ver
                self._basla_reconnect()
                return False

    # Adım hesaplayıcı (eskiden_calisan.py: _hata_to_adim)
    @staticmethod
    def _adim_hesapla(hata_px: float, kp: float, max_adim: int,
                      dead_zone: int = 8) -> int:
        if abs(hata_px) < dead_zone:
            return 0
        isaret = 1 if hata_px >= 0 else -1
        adim = int((hata_px ** 2) * kp / 100 * isaret)
        return max(-max_adim, min(max_adim, adim))

    # Gimbal
    def gimbal_hareket(self, pan: float, tilt: float) -> bool:
        if self._protokol == "stm32":
            import config
            cfg = config.DONANIM
            kp = cfg.get("KP_X", 3.0)
            max_adim = cfg.get("MAX_STEPS_X", 500)
            dz = cfg.get("DEAD_ZONE_PIXEL", 8)
            adim_x = self._adim_hesapla(pan, kp, max_adim, dz)
            adim_y = self._adim_hesapla(tilt, kp, max_adim, dz)
            komut = f"!X{adim_x}Y{adim_y}*\n"
        else:
            komut = f"G:{pan:.2f}:{tilt:.2f}*\n"
        return self._gonder(komut)

    def gimbal_sifirla(self) -> bool:
        if self._protokol == "stm32":
            return self._gonder("!X0Y0*\n")
        return self._gonder("G:0.00:0.00*\n")

    # Ateş
    def ates_komutu(self, hedef_id: int = 1) -> bool:
        log.info("ATES_KOMUTU hedef_id=%d", hedef_id)
        return self._gonder("atis\n")

    # Acil durdur
    def acil_durdur(self) -> bool:
        log.warning("ACİL_DURDUR (3x dur + gimbal reset)")
        if not self.bagli_mi():
            log.warning("ACİL_DURDUR: port bağlı değil")
            return False
        ok = False
        for _ in range(3):
            ok = self._gonder("dur\n")
            time.sleep(0.02)
        self._gimbal_reset_pwm()
        return ok

    def _gimbal_reset_pwm(self) -> None:
        try:
            import config as _cfg
            fmt = _cfg.DONANIM.get("HEDEF_FORMATI", "stm32_xy")
            m = _cfg.DONANIM.get("PWM_MERKEZ", 1500)
            if fmt == "stm32_xy":
                self._gonder(f"!X{m}Y{m}*\n")
            else:
                self._gonder("G:0.00:0.00\n")
        except Exception as e:
            log.warning("Gimbal reset hatası: %s", e)

    # Hedef konum gönder
    def hedef_konum_gonder(self,
                           hata_x: float, hata_y: float,
                           lazer_ox: int = 0, lazer_oy: int = 0) -> bool:
        import config as _cfg
        don = _cfg.DONANIM
        fmt = don.get("HEDEF_FORMATI", "stm32_xy")
        dx = hata_x - lazer_ox
        dy = hata_y - lazer_oy
        if fmt == "stm32_xy":
            olcek = don.get("PAN_OLCEK", 0.1)
            merkez = don.get("PWM_MERKEZ", 1500)
            pmin = don.get("PWM_MIN", 1000)
            pmax = don.get("PWM_MAX", 2000)
            pwm_x = self._pwm_hesapla(dx, olcek, merkez, pmin, pmax)
            pwm_y = self._pwm_hesapla(dy, olcek, merkez, pmin, pmax)
            komut = f"!X{pwm_x}Y{pwm_y}*\n"
        else:
            pan = dx * don.get("PAN_OLCEK", 0.1)
            tilt = dy * don.get("TILT_OLCEK", 0.1)
            komut = f"G:{pan:.2f}:{tilt:.2f}\n"
        return self._gonder(komut)

    # Ping
    def ping(self) -> bool:
        if not self.bagli_mi():
            return False
        self._gonder("PING\n")
        try:
            yanit = self._ser.readline().decode("ascii").strip()
            return yanit == "PONG"
        except Exception:
            return False
