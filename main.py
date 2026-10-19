import sys
import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

import config
from utils.logger import kur as log_kur
from utils.kamera_thread import KameraThread, FrameBuffer
from utils.kamera_deteksiyon import KameraDeteksiyonThread
from asama1.asama1 import Asama1Thread
from utils.lidar_thread import LidarThread
from asama2.asama2 import Asama2Thread
from asama3.asama3 import Asama3Thread
from sistem_fsm import SistemFSM
from ui.styles import GLOBAL_QSS
from ui.hedef_canvas import HedefCanvas
from ui.gorev_paneli import GorevPaneli
from ui.kamera_yonetici import KameraYonetici
from ui.main_window import AnaEkran

log = logging.getLogger(__name__)


def main() -> None:
    log_kur(seviye="INFO")

    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_QSS)

    ui_cfg = config.UI_AYAR
    n_kamera = len(config.KAMERALAR)

    # Frame buffer'lar
    buffers: list[FrameBuffer] = [FrameBuffer() for _ in range(n_kamera)]

    # Kamera thread'leri
    cam_threads: list[KameraThread] = []
    for i, cam_cfg in enumerate(config.KAMERALAR):
        flip_key = f"KAMERA_{i}_FLIP"
        flip_val = ui_cfg.get(flip_key, cam_cfg.get("flip", -1))
        t = KameraThread(
            cam_id=cam_cfg["id"],
            buffer=buffers[i],
            genislik=ui_cfg["KAMERA_GENISLIK"],
            yukseklik=ui_cfg["KAMERA_YUKSEKLIK"],
            fps_limit=ui_cfg["FPS_LIMIT"],
            flip=flip_val,
            flip_cfg_key=flip_key,
            cam_ayar=config.KAMERA_AYARLAR[i],
        )
        cam_threads.append(t)

    # Modelleri ön-yükle
    models: list = [None] * n_kamera
    try:
        from utils.model_yukleyici import yukle as _yukle
        for i, cam_cfg in enumerate(config.KAMERALAR):
            yol = config.KAMERA_AYARLAR[i].get("MODEL_YOLU",
                  cam_cfg.get("model", config.MODEL_NESNE_YOLU))
            try:
                models[i] = _yukle(yol)
                log.info("Model yüklendi — Kamera %d → %s", i, yol)
            except Exception as _e:
                log.error("Kamera %d model yüklenemedi: %s", i, _e)
    except Exception as _e:
        log.error("Model ön-yükleme başarısız: %s", _e)

    # Deteksiyon thread'leri
    det_threads: list[KameraDeteksiyonThread] = [
        KameraDeteksiyonThread(buffers[i], config.KAMERA_AYARLAR[i], model=models[i])
        for i in range(n_kamera)
    ]

    # Aşama thread'leri
    buf_a = buffers[0]
    buf_b = buffers[1] if n_kamera > 1 else buffers[0]
    a1 = Asama1Thread(buf_a, buf_b)
    a2 = Asama2Thread(buf_a, buf_b)
    a3 = Asama3Thread(buf_a, buf_b)

    # LiDAR thread
    lidar = LidarThread()

    # Sistem FSM
    fsm = SistemFSM(a1, a2, a3=a3, det_threads=det_threads)

    # UI
    canvases: list[HedefCanvas] = [HedefCanvas() for _ in range(n_kamera)]
    gp = GorevPaneli(imha_sirasi=config.ASAMA_1["IMHA_SIRASI"])
    km = KameraYonetici()
    pencere = AnaEkran(canvases=canvases, gorev_paneli=gp, kamera_yonetici=km)

    _baglantilari_kur(cam_threads, det_threads, a1, a2, a3, fsm, canvases, gp, km, pencere, lidar)

    # Pencereyi önce göster - event loop başlamadan thread start etme
    pencere.show()
    log.info("Uygulama başlatıldı (%d kamera).", n_kamera)

    # Cam thread'leri: 150ms sonra başlat (kameralar ETKIN=False -> idle döngü)
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(150, lambda: [t.start() for t in cam_threads])

    # Det thread'leri: 600ms sonra - UI tamamen render olsun, model yüklemesi arka plana taşınsın
    def _det_basla():
        for t in det_threads:
            t.start()
        if config.LIDAR.get("ETKIN", False):
            lidar.start()
    QTimer.singleShot(600, _det_basla)

    sys.exit(app.exec())


def _baglantilari_kur(cam_threads, det_threads, a1, a2, a3, fsm,
                      canvases, gp, km, pencere, lidar=None) -> None:
    n = len(cam_threads)

    # Kamera -> canvas
    for i in range(n):
        cam_threads[i].kare_hazir.connect(canvases[i].kare_guncelle)
        cam_threads[i].fps_guncellendi.connect(canvases[i].fps_guncelle)
        cam_threads[i].hata.connect(
            lambda m, _i=i: pencere.statusBar().showMessage(f"[HATA cam{_i}] {m}"))

    # Deteksiyon -> canvas + toolbar
    _gp_slots = [gp.hedef_listesi_guncelle_a, gp.hedef_listesi_guncelle_b]
    for i in range(n):
        det_threads[i].hedef_listesi.connect(canvases[i].hedefleri_guncelle)
        det_threads[i].yolo_fps.connect(canvases[i].yolo_fps_guncelle)
        det_threads[i].siniflar_hazir.connect(lambda sl, _i=i: pencere.model_siniflari_guncelle_cam(_i, sl))
        det_threads[i].siniflar_hazir.connect(gp.model_siniflari_guncelle)
        det_threads[i].hata.connect(
            lambda m, _i=i: pencere.statusBar().showMessage(
                f"[CAM-{_i} DET HATA] {m}", 0))
        if i < len(_gp_slots):
            det_threads[i].hedef_listesi.connect(_gp_slots[i])
    det_threads[0].hedef_listesi.connect(pencere.hedef_durumu_guncelle)

    # Deteksiyon -> Aşama 1 + 2 + 3 (DirectConnection - sadece queue.put)
    det_threads[0].hedef_listesi.connect(
        a1.hedef_listesi_al, Qt.ConnectionType.DirectConnection)
    det_threads[0].hedef_listesi.connect(
        a2.hedef_listesi_al, Qt.ConnectionType.DirectConnection)
    det_threads[0].hedef_listesi.connect(
        a3.hedef_listesi_al, Qt.ConnectionType.DirectConnection)
    # Kamera B -> dual-queue (Asama 1 / 2 / 3)
    if n > 1:
        det_threads[1].hedef_listesi.connect(
            a1.hedef_listesi_al_b, Qt.ConnectionType.DirectConnection)
        det_threads[1].hedef_listesi.connect(
            a2.hedef_listesi_al_b, Qt.ConnectionType.DirectConnection)
        det_threads[1].hedef_listesi.connect(
            a3.hedef_listesi_al_b, Qt.ConnectionType.DirectConnection)

    # LiDAR -> Asama1, Asama2, Asama3, Canvas'lar
    if lidar is not None:
        lidar.uzaklik_guncellendi.connect(a1.lidar_guncelle)
        lidar.uzaklik_guncellendi.connect(a2.lidar_guncelle)
        lidar.uzaklik_guncellendi.connect(a3.lidar_guncelle)
        for cv in canvases:
            lidar.uzaklik_guncellendi.connect(cv.lidar_guncelle)

    a1.faz_degisti.connect(gp.faz_guncelle)
    a1.faz_degisti.connect(pencere.faz_guncelle)
    # Global faz -> tüm canvas'lar (TARAMA, BAŞLATILDI vb.)
    for _cv in canvases:
        a1.faz_degisti.connect(_cv.faz_guncelle)
    # Per-camera faz -> sadece ilgili canvas (NISAN kameraya özel)
    for _ci, _cv in enumerate(canvases):
        a1.faz_degisti_cam.connect(
            lambda cam_idx, faz, _i=_ci, _c=_cv:
            _c.faz_guncelle(faz) if cam_idx == _i else None)
    a1.imha_komutu.connect(gp.imha_bildir)
    a1.imha_komutu.connect(pencere.imha_bildir_durum)
    a1.hata.connect(lambda m: pencere.statusBar().showMessage(f"[A1 HATA] {m}"))
    a1.siniflar_hazir.connect(pencere.model_siniflari_guncelle)
    a1.siniflar_hazir.connect(gp.model_siniflari_guncelle)

    a2.uzlasma_tamam.connect(canvases[0].hedef_kilitle)
    a2.faz_degisti.connect(gp.faz_guncelle)
    a2.faz_degisti.connect(pencere.faz_guncelle)
    a2.suru_sayisi.connect(gp.suru_sayac_guncelle)
    a2.imha_komutu.connect(gp.imha_bildir)
    a2.imha_komutu.connect(pencere.imha_bildir_durum)
    a2.hata.connect(lambda m: pencere.statusBar().showMessage(f"[A2 HATA] {m}"))
    a2.siniflar_hazir.connect(pencere.model_siniflari_guncelle)
    a2.siniflar_hazir.connect(gp.model_siniflari_guncelle)

    # Aşama 3 -> UI
    a3.faz_degisti.connect(gp.faz_guncelle)
    a3.faz_degisti.connect(pencere.faz_guncelle)
    for _cv in canvases:
        a3.faz_degisti.connect(_cv.faz_guncelle)
    for _ci, _cv in enumerate(canvases):
        a3.faz_degisti_cam.connect(
            lambda cam_idx, faz, _i=_ci, _c=_cv:
            _c.faz_guncelle(faz) if cam_idx == _i else None)
    a3.imha_komutu.connect(gp.imha_bildir)
    a3.imha_komutu.connect(pencere.imha_bildir_durum)
    a3.hata.connect(lambda m: pencere.statusBar().showMessage(f"[A3 HATA] {m}"))
    a3.siniflar_hazir.connect(pencere.model_siniflari_guncelle)
    a3.siniflar_hazir.connect(gp.model_siniflari_guncelle)

    # FSM -> UI
    fsm.asama_degisti.connect(gp.asama_badge_guncelle)
    fsm.acil_durdur_sig.connect(pencere.acil_durdur_overlay_goster)
    fsm.acil_durdur_sig.connect(lambda: pencere.durum_guncelle("ACİL_DURDUR"))

    # UI -> FSM
    gp.baslat.connect(fsm.gecis)
    gp.durdur.connect(lambda: fsm.gecis(None))
    gp.acil_durdur.connect(fsm.acil_durdur)

    for cv in canvases:
        gp.durdur.connect(cv.sifirla)
        gp.acil_durdur.connect(cv.sifirla)

    _asama_map = {1: a1, 2: a2, 3: a3}
    gp.atis_modu_degisti.connect(
        lambda no, mod: _asama_map.get(no, a1).mod_ayarla(mod))

    gp.manuel_onayla.connect(a1.manuel_onayla)
    gp.manuel_onayla.connect(a2.manuel_onayla)
    gp.manuel_onayla.connect(a3.manuel_onayla)

    def _id_degisti(idx: int, vid: int) -> None:
        if idx < len(cam_threads):
            cam_threads[idx].id_degistir(vid)
    km.kamera_id_degisti.connect(_id_degisti)

    for i in range(n):
        cam_threads[i].fps_guncellendi.connect(lambda fps, _i=i: km.fps_guncelle(_i, fps))
        cam_threads[i].fps_guncellendi.connect(
            lambda fps, _i=i: pencere.kamera_fps_guncelle(_i, fps))
        cam_threads[i].hata.connect(lambda _, _i=i: km.durum_guncelle(_i, False))
        km.kamera_etkin_degisti.connect(
            lambda idx, etkin, _i=i, _cv=canvases[i]:
                _cv.kamera_kapandi() if (idx == _i and not etkin) else None)

    def _model_degisti(idx: int, yol: str) -> None:
        log.info("Model degisti -> kamera=%d yol=%s", idx, yol)
        if idx < len(det_threads):
            det_threads[idx].model_yenile(yol)
    km.model_degisti.connect(_model_degisti)


if __name__ == "__main__":
    main()
