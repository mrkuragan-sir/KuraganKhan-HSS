from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

import cv2
import numpy as np

import config

# Veri yapisi

@dataclass
class AlgilamaHedfi:
    renk: str  # 'kirmizi', 'mavi', vb.
    sekil: str  # 'daire', 'ucgen', 'dikdortgen', 'bilinmiyor'
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2) piksel
    alan: float  # Kontur alani (piksel^2)
    guven: float  # 0-1 arasinda renk/sekil esleme kalitesi
    merkez: tuple[int, int] = field(init=False)

    def __post_init__(self) -> None:
        x1, y1, x2, y2 = self.bbox
        self.merkez = ((x1 + x2) // 2, (y1 + y2) // 2)

    @property
    def genislik(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def yukseklik(self) -> int:
        return self.bbox[3] - self.bbox[1]


# Yardimci fonksiyonlar

def _cembersellik(kontur) -> float:
    alan = cv2.contourArea(kontur)
    if alan < 1:
        return 0.0
    cevre = cv2.arcLength(kontur, True)
    if cevre < 1:
        return 0.0
    return min(1.0, (4.0 * math.pi * alan) / (cevre ** 2))


def _kose_sayisi(kontur) -> int:
    cevre = cv2.arcLength(kontur, True)
    eps = 0.03 * cevre
    approx = cv2.approxPolyDP(kontur, eps, True)
    return len(approx)


# Ana fonksiyonlar

def renk_maskesi(
    frame_bgr: np.ndarray,
    renk_adi: str,
    profiller: Optional[dict] = None,
) -> np.ndarray:
    if profiller is None:
        profiller = config.ASAMA_3.get("RENK_PROFILLERI", {})

    araliklar = profiller.get(renk_adi, [])
    if not araliklar:
        return np.zeros(frame_bgr.shape[:2], dtype=np.uint8)

    # Hafif Gaussian bulaniklik gurultu azaltir
    kucuk = cv2.resize(frame_bgr, (320, 180), interpolation=cv2.INTER_AREA)
    blurred = cv2.GaussianBlur(kucuk, (5, 5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    maske = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for alt, ust in araliklar:
        alt_arr = np.array(alt, dtype=np.uint8)
        ust_arr = np.array(ust, dtype=np.uint8)
        maske |= cv2.inRange(hsv, alt_arr, ust_arr)

    # Morfologik acma/kapama ile gurultu temizle
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    maske = cv2.morphologyEx(maske, cv2.MORPH_OPEN, kernel, iterations=1)
    maske = cv2.morphologyEx(maske, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Orijinal boyuta geri getir
    maske_tam = cv2.resize(maske, (frame_bgr.shape[1], frame_bgr.shape[0]),
                           interpolation=cv2.INTER_NEAREST)
    return maske_tam


def sekil_siniflandir(kontur) -> tuple[str, float]:
    esikler = config.ASAMA_3.get("SEKIL_ESIK", {})

    cember = _cembersellik(kontur)
    esik_daire = esikler.get("daire", 0.80)

    if cember >= esik_daire:
        return "daire", cember

    kose = _kose_sayisi(kontur)
    esik_uc = esikler.get("ucgen", 3)
    esik_drt = esikler.get("dikdortgen", 4)

    if kose == esik_uc:
        # Ucgen guven: ne kadar 3'e yakin olduguna gore
        guven = max(0.0, 1.0 - abs(kose - esik_uc) * 0.1)
        return "ucgen", guven

    if kose == esik_drt:
        # Dikdortgen guven: en-boy orani duzgunlugu ile takviye
        x, y, w, h = cv2.boundingRect(kontur)
        oran = min(w, h) / max(w, h) if max(w, h) > 0 else 0
        guven = 0.5 + 0.5 * oran
        return "dikdortgen", guven

    return "bilinmiyor", max(0.0, 1.0 - abs(kose - 4) * 0.05)


def algi_kareleri(
    frame_bgr: np.ndarray,
    hedef_renkler: Optional[Sequence[str]] = None,
    min_alan: int = 300,
    max_alan: int = 200_000,
) -> list[AlgilamaHedfi]:
    profiller = config.ASAMA_3.get("RENK_PROFILLERI", {})
    if hedef_renkler is None:
        hedef_renkler = list(profiller.keys())

    sonuclar: list[AlgilamaHedfi] = []

    for renk in hedef_renkler:
        maske = renk_maskesi(frame_bgr, renk, profiller)
        konturler, _ = cv2.findContours(
            maske, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for k in konturler:
            alan = cv2.contourArea(k)
            if not (min_alan <= alan <= max_alan):
                continue

            sekil, guven = sekil_siniflandir(k)
            rx, ry, rw, rh = cv2.boundingRect(k)
            bbox = (rx, ry, rx + rw, ry + rh)

            sonuclar.append(AlgilamaHedfi(
                renk=renk,
                sekil=sekil,
                bbox=bbox,
                alan=alan,
                guven=guven,
            ))

    # Alana gore azalan sira (buyuk hedef once)
    sonuclar.sort(key=lambda h: h.alan, reverse=True)
    return sonuclar


# Debug / gorsellestime

def ciz_tespitler(
    frame_bgr: np.ndarray,
    tespitler: list[AlgilamaHedfi],
    renk_haritasi: Optional[dict[str, tuple[int, int, int]]] = None,
) -> np.ndarray:
    if renk_haritasi is None:
        renk_haritasi = {
            "kirmizi" : (0, 0, 220),
            "mavi" : (220, 100, 0 ),
            "sari" : (0, 220, 220),
            "yesil" : (0, 200, 0 ),
            "turuncu" : (0, 140, 255),
            "mor" : (180, 0, 180),
        }

    cikti = frame_bgr.copy()
    for h in tespitler:
        renk_bgr = renk_haritasi.get(h.renk, (128, 128, 128))
        x1, y1, x2, y2 = h.bbox
        cv2.rectangle(cikti, (x1, y1), (x2, y2), renk_bgr, 2)
        etiket = f"{h.renk}/{h.sekil} {h.guven:.2f}"
        cv2.putText(cikti, etiket, (x1, max(y1 - 6, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, renk_bgr, 1, cv2.LINE_AA)
    return cikti
