import logging
from pathlib import Path

log = logging.getLogger(__name__)

DESTEKLENEN_FORMATLAR = {".pt", ".onnx", ".engine", ".tflite", ".torchscript"}


def yukle(yol: str):
    from ultralytics import YOLO

    p = Path(yol)
    if not p.exists():
        raise FileNotFoundError(
            "Model dosyasi bulunamadi: {}\n"
            "  -> models/ klasorune .pt veya .onnx dosyanizi koyun".format(yol)
        )
    if p.suffix.lower() not in DESTEKLENEN_FORMATLAR:
        raise ValueError(
            "Desteklenmeyen model formati: {}\n"
            "  -> Desteklenen: {}".format(p.suffix, ', '.join(sorted(DESTEKLENEN_FORMATLAR)))
        )

    fmt = p.suffix.lower()
    log.info("Model yukleniyor: %s (format: %s)", yol, fmt)

    if fmt == ".engine":
        try:
            model = YOLO(yol, task="detect")
        except Exception as e:
            raise RuntimeError("TensorRT engine yuklenemedi: {}\n  -> CUDA ve TensorRT kurulumunu kontrol edin".format(e)) from e
        try:
            import numpy as np
            dummy = np.zeros((640, 640, 3), dtype="uint8")
            model(dummy, verbose=False)
            log.info("Engine isindi: %s", yol)
        except Exception as warm_err:
            log.warning("Engine isinma atlandi: %s", warm_err)

    elif fmt == ".onnx":
        try:
            model = YOLO(yol)
        except (ImportError, OSError, Exception) as e:
            err_str = str(e).lower()
            if "dll" in err_str or "onnxruntime" in err_str or "pybind" in err_str:
                raise RuntimeError(
                    "ONNX Runtime DLL hatasi: {}\n"
                    "  -> 'pip install onnxruntime' veya 'pip install onnxruntime-gpu'\n"
                    "  -> Microsoft Visual C++ Redistributable kurulu mu?\n"
                    "  -> Veya modeli .pt formatina donusturun".format(e)
                ) from e
            raise RuntimeError("ONNX model yuklenemedi: {}".format(e)) from e

    else:
        # .pt, .torchscript, .tflite ve diger formatlar
        try:
            model = YOLO(yol)
        except Exception as e:
            raise RuntimeError("Model yuklenemedi ({}): {}".format(fmt, e)) from e

        if fmt == ".pt":
            # Conv+BN katmanlarini kaynastr -> ~%15 CPU hiz kazanci
            try:
                model.fuse()
                log.info("model.fuse() uygulandi: %s", yol)
            except Exception as fuse_err:
                log.warning("model.fuse() atlandi: %s", fuse_err)

            # Ilk cikarim yavas baslamasin diye isinma (warm-up)
            try:
                import numpy as np
                dummy = np.zeros((640, 640, 3), dtype="uint8")
                model(dummy, verbose=False)
                log.info("Model isindi (.pt): %s", yol)
            except Exception as warm_err:
                log.warning("Model isinma atlandi: %s", warm_err)

    log.info("Model hazir: %s | Sinif sayisi: %d | Siniflar: %s",
             yol, len(model.names), list(model.names.values())[:10])
    return model


def coklu_yukle(modeller_cfg: list) -> list:
    sonuc = []
    for girdi in modeller_cfg:
        if isinstance(girdi, str):
            yol = girdi
            imgsz = 640
            sinif_cfg = {}
        elif isinstance(girdi, dict):
            yol = girdi.get("yol", "")
            imgsz = int(girdi.get("imgsz", 640))
            sinif_cfg = girdi.get("siniflar", {})
        else:
            continue
        if not yol:
            continue
        try:
            m = yukle(yol)
            sonuc.append((m, imgsz, sinif_cfg))
        except Exception as e:
            log.warning("coklu_yukle: model atlandi (%s): %s", yol, e)
    return sonuc


def ek_model_siniflarini_oku(yol: str) -> list:
    try:
        m = yukle(yol)
        return list(m.names.values())
    except Exception as e:
        log.warning("ek_model_siniflarini_oku hatasi (%s): %s", yol, e)
        return []


def kamera_modeli_yukle(kamera_idx: int, tip: str = "nesne"):
    import config

    ayarlar = getattr(config, "KAMERA_AYARLAR", None)
    if ayarlar and kamera_idx < len(ayarlar):
        fallback = config.KAMERALAR[kamera_idx].get("model", config.MODEL_NESNE_YOLU) \
                   if kamera_idx < len(config.KAMERALAR) else config.MODEL_NESNE_YOLU
        yol = ayarlar[kamera_idx].get("MODEL_YOLU", fallback)
    elif kamera_idx < len(config.KAMERALAR):
        yol = config.KAMERALAR[kamera_idx].get("model", config.MODEL_NESNE_YOLU)
    else:
        yol = config.MODEL_NESNE_YOLU

    if not yol:
        raise FileNotFoundError(
            "Kamera {} icin model yolu tanimli degil.\n"
            "  -> config.py KAMERALAR[{}]['model'] yolunu ayarlayin.".format(kamera_idx, kamera_idx))

    return yukle(yol)
