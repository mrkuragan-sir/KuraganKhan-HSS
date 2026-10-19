from __future__ import annotations
import json
import threading
from pathlib import Path

# Acil Durdur aktifken tüm deteksiyon thread'leri çıkarımı askıya alır.
ACIL_DURDUR_EVENT: threading.Event = threading.Event()

# Varsayılan model yolu
MODEL_NESNE_YOLU = "models/nesne.pt"

# Kamera tanımları
KAMERALAR: list[dict] = [
    {"id": 0, "isim": "Kamera A", "model": "models/balon.pt", "flip": 1, "etkin": False},
    {"id": 1, "isim": "Kamera B", "model": "models/nesne.pt", "flip": 1, "etkin": False},
]

# Ortak deteksiyon ayarları
KAMERA_AYAR: dict = {
    "GUVEN_ESIGI": 0.25,
    "NMS_ESIGI": 0.45,
    "NESNE_SINIFLARI": [],
    "DOST_SINIFLAR": [],  # Dost - gösterilir, hedef alınmaz
    "DUSMAN_SINIFLAR": [],  # Düşman - gösterilir, tehdit sırasına göre hedef alınır
    "TEHDIT_SIRASI": [],  # Tehdit öncelik sırası (düşmanlar içinde)
    "IMHA_SIRASI": [],  # Geriye dönük uyumluluk (TEHDIT_SIRASI ile eş)
    # Motor Komut Ayarları
    "MOTOR_KOMUT_ETKIN": True,  # Bu kamera motor komutu gönderebilir mi?
    "MOTOR_KOMUT_ONCELIK": 0,  # Öncelik (0=en yüksek, büyük=düşük)
    "MOTOR_KOMUT_MIN_GUVEN": 0.25,  # Motor komut için minimum güven skoru
    "MOTOR_KOMUT_SINIF": [],  # Motor komut sınıf filtresi (boş=tüm düşmanlar)
    "TRACKER": False,
    "TRACKER_ALGORITMA": "botsort",
    "KAYIP_KARE_LIMIT": 30,
    "TRACKER_MIN_HITS": 3,
    "IMGSZ": 640,
    "CONTAINMENT_ESIGI": 0.80,
    "MIN_ALAN_ORAN": 0.001,
}


def _ayar_olustur(kamera: dict) -> dict:
    ayar = {k: (list(v) if isinstance(v, list) else v)
            for k, v in KAMERA_AYAR.items()}
    ayar["MODEL_YOLU"] = kamera.get("model", MODEL_NESNE_YOLU)
    ayar["ETKIN"] = kamera.get("etkin", False)
    return ayar


KAMERA_AYARLAR: list[dict] = [_ayar_olustur(k) for k in KAMERALAR]

# Geriye dönük uyumluluk
KAMERA_A_AYAR: dict = KAMERA_AYARLAR[0] if KAMERA_AYARLAR else KAMERA_AYAR
KAMERA_B_AYAR: dict = KAMERA_AYARLAR[1] if len(KAMERA_AYARLAR) > 1 else KAMERA_AYAR

# LiDAR ayarları
LIDAR: dict = {
    "ETKIN" : False,  # True = bağlan ve ölç
    "TIP" : "TFLUNA",  # TFLUNA | TFLUNAP | RPLIDAR | SIM
    "PORT" : "COM6",
    "BAUD" : 115200,
    "MIN_CM" : 10,  # ölçüm alt sınırı - gürültü filtresi
    "MAX_CM" : 3000,  # ölçüm üst sınırı
    "OFFSET_X_M" : 0.0,  # Kamera merkezine göre LiDAR konum ofseti
    "OFFSET_Y_M" : 0.0,
    "OFFSET_Z_M" : 0.0,
}

KAMERA_GEOMETRI: dict = {
    "BASELINE_M" : 0.30,  # Kamera A-B arası mesafe (metre)
    "FOV_H_A" : 90.0,  # Kamera A yatay FOV (derece)
    "FOV_H_B" : 90.0,  # Kamera B yatay FOV (derece)
    "KONUM_A" : [0.0, 0.0, 0.0],  # [x, y, z] metre - referans koordinat
    "KONUM_B" : [0.30, 0.0, 0.0],  # [x, y, z] metre
    "ACHI_A_DEG" : 0.0,  # Kamera A yatay yön açısı (0 = ileri)
    "ACHI_B_DEG" : 0.0,  # Kamera B yatay yön açısı
    "STEREO_ETKIN": False,  # True = triangülasyon hesapla
}

# Donanım (seri port) ayarları
DONANIM: dict = {
    "PORT": "COM8",
    "BAUD_RATE": 115200,
    "PROTOKOL": "stm32",
    "LAZER_OFFSET_X": 0,
    "LAZER_OFFSET_Y": 0,
    "HEDEF_FORMATI": "stm32_xy",
    "KP_X": 1.0,
    "KP_Y": 1.0,
    "MAX_STEPS_X": 400,
    "MAX_STEPS_Y": 400,
    "DEAD_ZONE_PIXEL": 10,
    "PAN_OLCEK": 0.1,
    "TILT_OLCEK": 0.1,
    "GIMBAL_FORMAT": "!X{x}Y{y}*",
    "GIMBAL_DUR_FORMAT": "!X0Y0*",
}

NISANGAH_AYAR: list[dict] = [
    {  # Kamera 0 (CAM A)
        "LAZER_DX_CM": 0.0,  # Lazer X ofseti kameraya göre (cm, sağ pozitif)
        "LAZER_DY_CM": 0.0,  # Lazer Y ofseti kameraya göre (cm, aşağı pozitif)
        "FOV_YATAY_DEG": 62.0,  # Kameranın yatay görüş açısı (derece)
        "FOV_DIKEY_DEG": 47.0,  # Kameranın dikey görüş açısı (derece)
        "COZUNURLUK_W": 1280,  # Referans çözünürlük genişliği
        "COZUNURLUK_H": 720,  # Referans çözünürlük yüksekliği
        "MANUEL_OFSET_X": 0,  # Manuel piksel ofseti X (ince ayar)
        "MANUEL_OFSET_Y": 0,  # Manuel piksel ofseti Y (ince ayar)
        "HEDEF_MESAFE_M": 10.0,  # Varsayılan hedef mesafesi (m, parallax hesabı için)
    },
    {  # Kamera 1 (CAM B)
        "LAZER_DX_CM": 0.0,
        "LAZER_DY_CM": 0.0,
        "FOV_YATAY_DEG": 62.0,
        "FOV_DIKEY_DEG": 47.0,
        "COZUNURLUK_W": 1280,
        "COZUNURLUK_H": 720,
        "MANUEL_OFSET_X": 0,
        "MANUEL_OFSET_Y": 0,
        "HEDEF_MESAFE_M": 10.0,
    },
]

# Motor Manuel Kontrol
MOTOR_KONTROL: dict = {
    # Tuş atamaları (küçük harf tek karakter veya Qt key ismi)
    "TUS_SOL": "a",
    "TUS_SAG": "d",
    "TUS_YUKARI": "w",
    "TUS_ASAGI": "s",
    "TUS_DUR": "space",
    "TUS_ATES": "f",
    "TUS_ATIS_DUR": "g",  # Ateş durdur kısayolu
    "TUS_ACIL_DUR": "escape",  # Acil durdur kısayolu
    "TUS_LAZER": "space",  # Lazer - basılı tut: aktif, bırak: kapat
    "LAZER_KOMUTU": "lazer_ac\n",  # Lazer açma komutu (STM32)
    "LAZER_DUR_KOMUTU": "lazer_kapat\n",  # Lazer kapama komutu (STM32)
    "HAREKET_HZ": 20,  # Basılı tuş gönderim frekansı (kez/sn)
    # Motor hareket komutları
    "KOMUT_SOL": "!X-300Y0*\n",
    "KOMUT_SAG": "!X300Y0*\n",
    "KOMUT_YUKARI": "!X0Y-300*\n",
    "KOMUT_ASAGI": "!X0Y300*\n",
    "KOMUT_DUR": "!X0Y0*\n",
    "MERKEZ_KOMUTU": "!X0Y0*\n",
    # Özel komutlar
    # NOT: "PING\n" STM32'de tanımsız - sessizce yok sayılır (ping yanıtı gelmez)
    "PING_KOMUTU": "PING\n",
    "ATES_KOMUTU": "atis\n",
    "ATES_DUR_KOMUTU": "atisdur\n",
    # DİKKAT: "s\n" STM32'de tanımsız! Doğru acil dur komutu: "dur\n"
    "ACIL_DUR_KOMUTU": "dur\n",
    # Parametre ayarları
    "JOISTIK_OLCEK": 300,
    "JOISTIK_HIZI": 50,
    "ATES_SURE_MS": 500,
}

# Aşama 1
ASAMA_1: dict = {
    "NESNE_SINIFLARI": [],
    "ATIS_ARALIK": 1.5,
    "GUVEN_ESIGI": 0.55,
    "IMHA_SIRASI": [],
    "DOST_SINIFLAR": [],
    "DEAD_ZONE_PIXEL": 8,
    "NMS_ESIGI": 0.45,
    "ATIS_MODU": "MANUEL",
    "MANUEL_ONAY_TIMEOUT": 5.0,
    # Per-phase kamera ataması
    "KAMERA_A_IDX" : 0,  # Birincil kamera fiziksel index
    "KAMERA_B_IDX" : 1,  # İkincil kamera fiziksel index
    "KAMERA_A_MODEL" : "",  # Bu aşama için kamera A model yolu (boş = global)
    "KAMERA_B_MODEL" : "",  # Bu aşama için kamera B model yolu (boş = global)
    "KAMERA_A_DOST" : [],  # Kamera A dost sınıfları
    "KAMERA_B_DOST" : [],  # Kamera B dost sınıfları
    "KAMERA_A_IMHA" : [],  # Kamera A öncelik/imha sırası
    "KAMERA_B_IMHA" : [],  # Kamera B öncelik/imha sırası
}

# Aşama 2
ASAMA_2: dict = {
    "NESNE_SINIFLARI": [],
    "DOST_SINIFLAR": [],
    "GUVEN_ESIGI": 0.50,
    "UZLASMA_ESIGI": 0.55,
    "GUVEN_CARPAN": 0.60,
    "UZLASMA_GEREK": 2,
    "HEDEF_KAYIP_LIMIT": 5,
    "MAX_SURU_BOYUTU": 20,
    "TRACKER_ALGORITMA": "botsort",
    "TRACKER_MIN_HITS": 3,
    "KAYIP_KARE_LIMIT": 30,
    "NMS_ESIGI": 0.45,
    "ATIS_MODU": "MANUEL",
    "MANUEL_ONAY_TIMEOUT": 5.0,
    # Per-phase kamera ataması
    "KAMERA_A_IDX" : 0,
    "KAMERA_B_IDX" : 1,
    "KAMERA_A_MODEL" : "",
    "KAMERA_B_MODEL" : "",
    "KAMERA_A_DOST" : [],
    "KAMERA_B_DOST" : [],
    "KAMERA_A_IMHA" : [],
    "KAMERA_B_IMHA" : [],
}

# Aşama 3 (Yüksek Güven / Hızlı İmha)
ASAMA_3: dict = {
    "NESNE_SINIFLARI": [],
    "DOST_SINIFLAR": [],
    "GUVEN_ESIGI": 0.65,
    "UZLASMA_ESIGI": 0.70,
    "GUVEN_CARPAN": 0.75,
    "UZLASMA_GEREK": 3,
    "HEDEF_KAYIP_LIMIT": 3,
    "MAX_SURU_BOYUTU": 10,
    "TRACKER_ALGORITMA": "botsort",
    "TRACKER_MIN_HITS": 3,
    "KAYIP_KARE_LIMIT": 20,
    "DEAD_ZONE_PIXEL": 6,
    "NMS_ESIGI": 0.50,
    "ATIS_MODU": "MANUEL",
    "MANUEL_ONAY_TIMEOUT": 3.0,
    # Per-phase kamera ataması
    "KAMERA_A_IDX" : 0,
    "KAMERA_B_IDX" : 1,
    "KAMERA_A_MODEL" : "",
    "KAMERA_B_MODEL" : "",
    "KAMERA_A_DOST" : [],
    "KAMERA_B_DOST" : [],
    "KAMERA_A_IMHA" : [],
    "KAMERA_B_IMHA" : [],
    "RENK_PROFILLERI": {
        "kirmizi": [
            ([0, 50, 50], [10, 255, 255]),  # Kırmızı düşük ton
            ([170, 50, 50], [180, 255, 255]),  # Kırmızı yüksek ton
        ],
        "mavi": [
            ([100, 80, 50], [130, 255, 255]),
        ],
        "sari": [
            ([25, 80, 80], [35, 255, 255]),
        ],
        "yesil": [
            ([40, 60, 50], [80, 255, 255]),
        ],
        "turuncu": [
            ([11, 80, 80], [24, 255, 255]),
        ],
        "mor": [
            ([130, 50, 50], [160, 255, 255]),
        ],
    },
    # Şekil eşikleri
    "SEKIL_ESIK": {
        "daire" : 0.80,  # Çembersellik (4πA/P²) eşiği
        "ucgen" : 3,  # Köşe sayısı
        "dikdortgen" : 4,  # Köşe sayısı
    },
    # Arama & kilit parametreleri
    "ARAMA_SURE" : 10.0,  # Arama FSM maksimum süre (saniye)
    "ARAMA_STRATEJISI" : "spiral",  # spiral | raster
    "SPIRAL_ADIM" : 15,  # Spiral adım büyüklüğü (piksel)
    "KILIT_MERKEZ_ESIGI" : 12,  # Kilit için merkez hatası eşiği (piksel)
    "KILIT_GEREK" : 5,  # Ard arda kilit sayısı
    "IMHA_GUVEN_ESIGI" : 0.65,  # Otonom imha için güven eşiği
}

# UI ayarları
UI_AYAR: dict = {
    "KAMERA_GENISLIK": 1280,
    "KAMERA_YUKSEKLIK": 720,
    "FPS_LIMIT": 30,
    "CANVAS_MINIMAP": True,
    "CANVAS_TRAIL_LEN": 30,
    "PANEL_GENISLIK": 360,
}

for _i, _k in enumerate(KAMERALAR):
    UI_AYAR[f"KAMERA_{_i}_FLIP"] = _k.get("flip", -1)
UI_AYAR.setdefault("KAMERA_A_FLIP", KAMERALAR[0].get("flip", 1) if KAMERALAR else 1)
UI_AYAR.setdefault("KAMERA_B_FLIP",
                   KAMERALAR[1].get("flip", 1) if len(KAMERALAR) > 1 else 1)


# JSON override
def json_yukle(dosya: str = "config_override.json") -> None:
    path = Path(dosya)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[config] config_override.json parse hatası: {e}")
        return
    bloklar = {
        "MODEL_NESNE_YOLU",
        "KAMERALAR", "KAMERA_AYAR",
        "ASAMA_1", "ASAMA_2", "ASAMA_3", "UI_AYAR", "DONANIM", "MOTOR_KONTROL",
        "KAMERA_A_AYAR", "KAMERA_B_AYAR",
        "LIDAR", "KAMERA_GEOMETRI", "NISANGAH_AYAR",
    }
    g = globals()
    for anahtar, deger in data.items():
        if anahtar not in bloklar:
            continue
        if isinstance(g.get(anahtar), dict) and isinstance(deger, dict):
            g[anahtar].update(deger)
        else:
            g[anahtar] = deger

    global KAMERA_AYARLAR, KAMERA_A_AYAR, KAMERA_B_AYAR
    KAMERA_AYARLAR = [_ayar_olustur(k) for k in KAMERALAR]
    KAMERA_A_AYAR = KAMERA_AYARLAR[0] if KAMERA_AYARLAR else KAMERA_AYAR
    KAMERA_B_AYAR = KAMERA_AYARLAR[1] if len(KAMERA_AYARLAR) > 1 else KAMERA_AYAR


def json_kaydet(dosya: str = "config_override.json") -> bool:
    try:
        import copy, json as _json
        def _temizle(obj):
            if isinstance(obj, dict):
                return {k: _temizle(v) for k, v in obj.items()
                        if not k.startswith("_")}
            if isinstance(obj, list):
                return [_temizle(i) for i in obj]
            if isinstance(obj, (int, float, str, bool, type(None))):
                return obj
            return str(obj)

        veri = {
            "KAMERALAR": _temizle(copy.deepcopy(KAMERALAR)),
            "DONANIM": _temizle(DONANIM),
            "UI_AYAR": _temizle(UI_AYAR),
            "MOTOR_KONTROL": _temizle(MOTOR_KONTROL),
            "NISANGAH_AYAR": _temizle(NISANGAH_AYAR),
            "LIDAR": _temizle(LIDAR),
            "KAMERA_GEOMETRI": _temizle(KAMERA_GEOMETRI),
            "ASAMA_1": _temizle(ASAMA_1),
            "ASAMA_2": _temizle(ASAMA_2),
            "ASAMA_3": _temizle(ASAMA_3),
        }
        Path(dosya).write_text(
            _json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[config] Kayit hatasi: {e}")
        return False


json_yukle()
