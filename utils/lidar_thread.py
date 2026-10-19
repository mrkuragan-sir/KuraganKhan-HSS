from __future__ import annotations
import math
import logging
import time

from PyQt6.QtCore import QThread, pyqtSignal

import config

log = logging.getLogger(__name__)


class LidarThread(QThread):

    uzaklik_guncellendi = pyqtSignal(float)  # metre
    lidar_hatasi = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dur = False
        self._port = None
        self._uz_m = 0.0  # son geçerli ölçüm (metre)

    # Dış kontrol
    def dur(self) -> None:
        self._dur = True
        if self._port:
            try:
                self._port.close()
            except Exception:
                pass
        self.wait(3000)

    @property
    def son_uzaklik_m(self) -> float:
        return self._uz_m

    # Ana döngü
    def run(self) -> None:
        cfg = config.LIDAR
        if not cfg.get("ETKIN", False):
            log.info("LidarThread devre dışı (LIDAR.ETKIN=False).")
            return

        tip = cfg.get("TIP", "TFLUNA").upper()

        if tip == "SIM":
            self._sim_loop()
        elif tip in ("TFLUNA", "TFLUNAP"):
            self._tfluna_loop(cfg)
        elif tip == "RPLIDAR":
            self._rplidar_loop(cfg)
        else:
            self.lidar_hatasi.emit(f"Bilinmeyen LiDAR tipi: {tip}")

    # TF-Luna protokolü
    def _tfluna_loop(self, cfg: dict) -> None:
        try:
            import serial
        except ImportError:
            self.lidar_hatasi.emit("pyserial kurulu değil — pip install pyserial")
            return

        port_adi = cfg.get("PORT", "COM6")
        baud = cfg.get("BAUD", 115200)
        min_cm = cfg.get("MIN_CM", 10)
        max_cm = cfg.get("MAX_CM", 3000)

        try:
            self._port = serial.Serial(port_adi, baud, timeout=1.0)
            log.info("TF-Luna bağlandı: %s @ %d", port_adi, baud)
        except Exception as e:
            self.lidar_hatasi.emit(f"TF-Luna bağlantı hatası: {e}")
            return

        buf = bytearray()
        while not self._dur:
            try:
                buf += self._port.read(9)
            except Exception as e:
                if not self._dur:
                    self.lidar_hatasi.emit(f"TF-Luna okuma hatası: {e}")
                break

            # Frame senkronizasyon: 0x59 0x59 arayışı
            while len(buf) >= 9:
                if buf[0] == 0x59 and buf[1] == 0x59:
                    frame = buf[:9]
                    buf = buf[9:]
                    # Checksum doğrulama
                    csum = sum(frame[:8]) & 0xFF
                    if csum != frame[8]:
                        continue
                    dist_cm = frame[2] | (frame[3] << 8)
                    if min_cm <= dist_cm <= max_cm:
                        self._uz_m = dist_cm / 100.0
                        self.uzaklik_guncellendi.emit(self._uz_m)
                else:
                    buf = buf[1:]  # senkronizasyon kayıpsa kaydır

        if self._port and self._port.is_open:
            self._port.close()
        log.info("LidarThread (TF-Luna) durdu.")

    # RP-LiDAR A1/A2
    def _rplidar_loop(self, cfg: dict) -> None:
        try:
            from rplidar import RPLidar
        except ImportError:
            self.lidar_hatasi.emit("rplidar kütüphanesi yok — pip install rplidar-roboticia")
            return

        port_adi = cfg.get("PORT", "COM6")
        try:
            lidar = RPLidar(port_adi)
            lidar.start_motor()
            log.info("RP-LiDAR başlatıldı: %s", port_adi)
        except Exception as e:
            self.lidar_hatasi.emit(f"RP-LiDAR bağlantı hatası: {e}")
            return

        min_cm = cfg.get("MIN_CM", 10)
        max_cm = cfg.get("MAX_CM", 3000)

        try:
            for scan in lidar.iter_scans():
                if self._dur:
                    break
                # 0° ±15° aralığındaki ölçümlerin medyanı
                readings = [
                    dist for (q, ang, dist) in scan
                    if (ang <= 15 or ang >= 345) and min_cm <= dist / 10 <= max_cm
                ]
                if readings:
                    readings.sort()
                    med_cm = readings[len(readings) // 2] / 10.0  # mm->cm
                    self._uz_m = med_cm / 100.0
                    self.uzaklik_guncellendi.emit(self._uz_m)
        except Exception as e:
            if not self._dur:
                self.lidar_hatasi.emit(f"RP-LiDAR scan hatası: {e}")
        finally:
            try:
                lidar.stop()
                lidar.stop_motor()
                lidar.disconnect()
            except Exception:
                pass
        log.info("LidarThread (RP-LiDAR) durdu.")

    # Simülasyon modu
    def _sim_loop(self) -> None:
        log.info("LidarThread SIM modu başladı.")
        t = 0.0
        while not self._dur:
            dist_m = 27.5 + 22.5 * math.sin(t)  # 5..50 m
            self._uz_m = round(dist_m, 2)
            self.uzaklik_guncellendi.emit(self._uz_m)
            t += 0.628  # ~10 Hz, tam tur ≈ 10 saniye
            time.sleep(0.1)
        log.info("LidarThread SIM modu durdu.")
