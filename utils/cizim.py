from __future__ import annotations
import math
from typing import List, Dict, Tuple, Optional

import cv2
import numpy as np

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (QPainter, QPen, QBrush, QColor,
                           QFont, QFontMetrics)


class Palet:

    # Qt renkleri (Görsel-2 iki-renk şema)
    KUTU_DUSUMAN = QColor( 30, 100, 255)  # mavi - düşman kutu kenarlığı
    BRAKET_DUSUMAN = QColor(220, 30, 30)  # kırmızı - köşe braketleri + çizgi
    KUTU_DOST = QColor( 0, 210, 80)  # yeşil - dost kutu
    BRAKET_DOST = QColor( 0, 210, 80)  # yeşil braket
    KUTU_KILIT = QColor( 0, 255, 120)  # parlak yeşil - kilit/onaylı
    BRAKET_KILIT = QColor( 0, 255, 120)

    # Etiket arka planları (80% opasite)
    BG_DUSUMAN = QColor( 30, 100, 255, 200)
    BG_DOST = QColor( 0, 150, 60, 200)
    BG_KILIT = QColor( 0, 200, 100, 200)
    ETIKET_YAZI = QColor(255, 255, 255)  # beyaz yazı

    # HUD / overlay renkleri
    HATA = QColor(255, 159, 0)  # amber - ErrX/ErrY
    FPS_IYI = QColor( 0, 255, 128)  # parlak yeşil
    FPS_ORT = QColor(255, 165, 0)  # turuncu
    FPS_KOT = QColor(255, 60, 60)  # kırmızı
    CROSSHAIR = QColor(200, 200, 200, 180)

    # Geriye dönük isimler (eski kodlarla uyumluluk)
    ONCELIKLI = QColor(255, 159, 10)
    DUSUMAN = QColor(255, 45, 85)
    DOST = KUTU_DOST
    KILIT = KUTU_KILIT
    BALON = QColor(255, 60, 60)
    HEDEF = DUSUMAN
    KESIK = BALON
    P_A = ONCELIKLI
    P_B = DUSUMAN
    P_C = QColor(0, 210, 255)

    # OpenCV BGR renkleri
    CV_KUTU_DUSUMAN = (220, 80, 20)  # mavi kutu (BGR)
    CV_BRAKET_DUSUMAN = ( 20, 20, 220)  # kırmızı braket (BGR)
    CV_KUTU_DOST = ( 60, 210, 0)  # yeşil kutu (BGR)
    CV_BRAKET_DOST = ( 60, 210, 0)  # yeşil braket (BGR)
    CV_KUTU_KILIT = ( 0, 220, 80)  # kilit kutu
    CV_BRAKET_KILIT = ( 0, 220, 80)
    CV_FPS = ( 0, 220, 255)  # sarı-yeşil - FPS overlay (BGR)
    CV_HATA = ( 50, 50, 255)  # amber hata metni (BGR)
    CV_CROSSHAIR = (200, 200, 200)  # gri-beyaz nişangah

    # eski uyumluluk
    CV_ONCELIK = CV_BRAKET_DUSUMAN
    CV_DUSUMAN = CV_KUTU_DUSUMAN
    CV_DOST = CV_KUTU_DOST
    CV_KILIT = CV_KUTU_KILIT
    CV_BALON = ( 60, 60, 255)
    CV_HEDEF = CV_KUTU_DUSUMAN
    CV_ONCELIKLI = CV_BRAKET_DUSUMAN


# Sabitler
CROSSHAIR_IC_YARI_CAP = 6  # merkez dolu daire yarıçapı (px)
CROSSHAIR_COL_UZUNLUK = 22  # crosshair çizgi yarı-uzunluğu
KILIT_KOSE_KATSAYI = 4
KILIT_KOSE_MIN = 12
KILIT_KALINLIK = 2
FPS_YAZI_X = 12
FPS_YAZI_Y = 28
KP_X = 2.5  # piksel -> adım dönüşüm katsayısı X
KP_Y = 2.5  # piksel -> adım dönüşüm katsayısı Y

_CV = cv2.FONT_HERSHEY_SIMPLEX

# Qt font tanımları
_F9 = QFont("Consolas", 9)
_F8 = QFont("Consolas", 8)
_F10 = QFont("Consolas", 10)
_F11 = QFont("Consolas", 11, QFont.Weight.Bold)


def crosshair_ciz(p: QPainter,
                  cx: int, cy: int,
                  boyut: int = 12,
                  renk: Optional[QColor] = None) -> None:
    if renk is None:
        renk = Palet.CROSSHAIR
    gap = 5
    p.save()
    p.setPen(QPen(renk, 1))
    p.drawLine(cx - boyut, cy, cx - gap, cy)
    p.drawLine(cx + gap, cy, cx + boyut, cy)
    p.drawLine(cx, cy - boyut, cx, cy - gap)
    p.drawLine(cx, cy + gap, cx, cy + boyut)
    p.setBrush(QBrush(Qt.BrushStyle.NoBrush))
    p.drawEllipse(cx - gap, cy - gap, gap * 2, gap * 2)
    p.restore()


def kilit_braket_ciz(p: QPainter,
                     rx: int, ry: int, rw: int, rh: int,
                     renk: QColor,
                     lock_t: float = 0.0,
                     kalinlik: int = 2,
                     L: int = 14) -> None:
    L = max(8, min(L + int(lock_t * 6), rw // 2, rh // 2))
    p.save()
    p.setPen(QPen(renk, kalinlik))
    p.setBrush(QBrush(Qt.BrushStyle.NoBrush))
    # Sol-üst
    p.drawLine(rx, ry, rx + L, ry)
    p.drawLine(rx, ry, rx, ry + L)
    # Sağ-üst
    p.drawLine(rx+rw-L, ry, rx+rw, ry)
    p.drawLine(rx+rw, ry, rx+rw, ry + L)
    # Sol-alt
    p.drawLine(rx, ry+rh-L, rx, ry+rh)
    p.drawLine(rx, ry+rh, rx + L, ry+rh)
    # Sağ-alt
    p.drawLine(rx+rw-L, ry+rh, rx+rw, ry+rh)
    p.drawLine(rx+rw, ry+rh-L, rx+rw, ry+rh)
    p.restore()


def hata_overlay_ciz(p: QPainter,
                     hata_x: float, hata_y: float,
                     cw: int, ch: int,
                     hud_y: int = 40) -> None:
    if abs(hata_x) < 3 and abs(hata_y) < 3:
        return

    mx, my = cw // 2, ch // 2
    tx = int(mx + hata_x)
    ty = int(my + hata_y)

    # Ok çizgisi (merkez -> hedef)
    p.save()
    renk = Palet.BRAKET_DUSUMAN  # kırmızı
    p.setPen(QPen(renk, 2))
    p.drawLine(mx, my, tx, ty)
    # Ok başı
    aci = math.atan2(hata_y, hata_x)
    for da in (2.4, -2.4):
        ex = tx - int(10 * math.cos(aci + da))
        ey = ty - int(10 * math.sin(aci + da))
        p.drawLine(tx, ty, ex, ey)
    p.restore()

    # Metin üst satırda
    adim_x = int(hata_x * KP_X)
    adim_y = int(hata_y * KP_Y)
    metin = (f"ErrX:{hata_x:+.0f}px -> {adim_x:+d}adim    "
             f"ErrY:{hata_y:+.0f}px -> {adim_y:+d}adim")
    p.save()
    p.setFont(_F9)
    p.setPen(Palet.HATA)
    p.drawText(10, hud_y, metin)
    p.restore()


def hedef_kutu_ciz(p: QPainter,
                   rx: int, ry: int, rw: int, rh: int,
                   sinif: str = "?",
                   guven: float = 0.0,
                   track_id: int = 0,
                   dost: bool = False,
                   onaylandi: bool = False,
                   oncelikli: bool = False,
                   balon: bool = False,
                   lock_t: float = 0.0,
                   uzaklik_m: Optional[float] = None) -> None:
    if dost:
        kutu_renk = Palet.KUTU_DOST
        braket_renk = Palet.BRAKET_DOST
        bg_renk = Palet.BG_DOST
    elif onaylandi:
        kutu_renk = Palet.KUTU_KILIT
        braket_renk = Palet.BRAKET_KILIT
        bg_renk = Palet.BG_KILIT
    else:
        kutu_renk = Palet.KUTU_DUSUMAN
        braket_renk = Palet.BRAKET_DUSUMAN
        bg_renk = Palet.BG_DUSUMAN

    # 1. Solid kutu kenarlığı + dost dolgu
    p.save()
    p.setPen(QPen(kutu_renk, 1))
    if dost:
        # Dost hedef: hafif yeşil dolgu
        p.setBrush(QBrush(QColor(0, 210, 80, 28)))
    else:
        p.setBrush(QBrush(Qt.BrushStyle.NoBrush))
    p.drawRect(rx, ry, rw, rh)
    p.restore()

    # 2. Köşe L-braketleri (KIRMIZI düşman / YEŞİL dost)
    L = 16 if (onaylandi or oncelikli) else 12
    kilit_braket_ciz(p, rx, ry, rw, rh, braket_renk, lock_t,
                     kalinlik=2, L=L)

    # 3. Hedef merkezinde dolu daire
    cx = rx + rw // 2
    cy = ry + rh // 2
    r = 5 if oncelikli else 4
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(braket_renk))
    p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
    p.restore()

    # 4. Etiket - kutunun sol-üst köşesinde, renk arka plan
    prefix = "[F]" if dost else "[E]"
    dist_str = f" {uzaklik_m:.1f}m" if uzaklik_m is not None else ""
    etiket = f"{prefix}{sinif}{dist_str} {int(guven * 100)}% #{track_id}"
    p.save()
    p.setFont(_F9)
    fm = QFontMetrics(_F9)
    tw = fm.horizontalAdvance(etiket) + 8
    th = fm.height() + 2
    p.fillRect(rx, ry, tw, th, bg_renk)
    p.setPen(Palet.ETIKET_YAZI)
    p.drawText(rx + 4, ry + th - 3, etiket)
    p.restore()

    # 4b. Mesafe rozeti - kutunun sağ-üst köşesi (büyük, okunaklı)
    if uzaklik_m is not None:
        dist_label = f"◎ {uzaklik_m:.1f} m"
        p.save()
        p.setFont(_F11)
        fm2 = QFontMetrics(_F11)
        dw = fm2.horizontalAdvance(dist_label) + 10
        dh = fm2.height() + 2
        dx = rx + rw - dw
        dy = ry
        dist_bg = QColor(0, 0, 0, 180)
        p.fillRect(dx, dy, dw, dh, dist_bg)
        # Mesafeye göre renk: <5m kırmızı, <20m amber, >20m yeşil
        if uzaklik_m < 5.0:
            dist_col = QColor(255, 60, 60)
        elif uzaklik_m < 20.0:
            dist_col = QColor(255, 159, 10)
        else:
            dist_col = QColor(0, 210, 80)
        p.setPen(dist_col)
        p.drawText(dx + 5, dy + dh - 3, dist_label)
        p.restore()

    # 5. Dost hedef -> alt-orta "◆ DOST" rozeti
    if dost:
        rozet = "◆ DOST"
        p.save()
        p.setFont(_F9)
        fm2 = QFontMetrics(_F9)
        rw2 = fm2.horizontalAdvance(rozet) + 10
        rh2 = fm2.height() + 2
        rx2 = rx + (rw - rw2) // 2
        ry2 = ry + rh - rh2
        p.fillRect(rx2, ry2, rw2, rh2, QColor(0, 150, 60, 200))
        p.setPen(QColor(180, 255, 200))
        p.drawText(rx2 + 5, ry2 + rh2 - 3, rozet)
        p.restore()


def tum_hedef_cizgileri(p: QPainter,
                        hedefler: List[Dict],
                        kare_w: int, kare_h: int,
                        cw: int, ch: int,
                        lock_t: float = 0.0) -> None:
    if not hedefler or kare_w <= 0 or kare_h <= 0:
        return

    sw = cw / kare_w
    sh = ch / kare_h
    mx, my = cw // 2, ch // 2

    # Merkez -> hedef çizgileri (arka plan, kutunun altında)
    for i, h in enumerate(hedefler):
        bbox = h.get("bbox")
        if not bbox:
            continue
        bx, by, bw, bh = bbox
        hx = int((bx + bw / 2) * sw)
        hy = int((by + bh / 2) * sh)
        dost = bool(h.get("dost", False))
        renk = Palet.BRAKET_DOST if dost else Palet.BRAKET_DUSUMAN
        kalinlik = 2 if i == 0 else 1
        p.save()
        p.setPen(QPen(renk, kalinlik))
        p.drawLine(mx, my, hx, hy)
        p.restore()

    # ErrX/ErrY - ilk düşman hedefin HEMEN ALTINDA
    birinci = next((h for h in hedefler if not h.get("dost", False)), None)
    _err_drawn = False  # kutu çiziminden sonra da kullanılacak
    _err_rx = _err_ry = _err_rh = 0
    _err_metin = ""
    if birinci:
        bbox = birinci.get("bbox")
        if bbox:
            bx, by, bw, bh = bbox
            _err_rx = int(bx * sw)
            _err_ry = int(by * sh)
            _err_rh = int(bh * sh)
            hata_x = (bx + bw / 2) * sw - mx
            hata_y = (by + bh / 2) * sh - my
            if abs(hata_x) >= 3 or abs(hata_y) >= 3:
                _err_drawn = True
                adim_x = int(hata_x * KP_X)
                adim_y = int(hata_y * KP_Y)
                _err_metin = (f"ErrX:{hata_x:+.0f}px->{adim_x:+d}    "
                              f"ErrY:{hata_y:+.0f}px->{adim_y:+d}")

    # Hedef kutuları
    for i, h in enumerate(hedefler):
        bbox = h.get("bbox")
        if not bbox:
            continue
        bx, by, bw, bh = bbox
        rx = int(bx * sw); ry = int(by * sh)
        rw = int(bw * sw); rh = int(bh * sh)

        dost = bool(h.get("dost", False))
        onaylandi = bool(h.get("onaylandi", False))
        balon = bool(h.get("balon_eslesme", False))
        oncelikli = (i == 0) and not dost and not onaylandi
        track_id = h.get("track_id") or h.get("id", 0)

        hedef_kutu_ciz(
            p, rx, ry, rw, rh,
            sinif = h.get("sinif") or h.get("renk", "?"),
            guven = h.get("guven", 0.0),
            track_id = track_id,
            dost = dost,
            onaylandi = onaylandi,
            oncelikli = oncelikli,
            balon = balon,
            lock_t = lock_t,
            uzaklik_m = h.get("uzaklik_m"),
        )

    # ErrX/ErrY - ilk düşman bbox'un hemen altına yaz
    if _err_drawn:
        p.save()
        p.setFont(_F9)
        p.setPen(Palet.HATA)
        ty = min(_err_ry + _err_rh + 14, ch - 8)
        p.drawText(_err_rx, ty, _err_metin)
        p.restore()


def fps_overlay_ciz(p: QPainter,
                    fps: float,
                    yolo_fps: float = 0.0,
                    dusuman_n: int = 0,
                    dost_n: int = 0,
                    x: int = 10,
                    y: int = 20) -> None:
    p.save()
    p.setFont(_F9)

    if fps > 0:
        renk = (Palet.FPS_IYI if fps >= 25
                else Palet.FPS_ORT if fps >= 15
                else Palet.FPS_KOT)
        yolo = yolo_fps if yolo_fps > 0 else fps
        metin = f"CAM {fps:.1f}  YOLO {yolo:.1f}  Dusman:{dusuman_n}  Dost:{dost_n}"
        p.setPen(renk)
        p.drawText(x, y, metin)
    else:
        # Kamera henüz bağlı değil - sadece düşman/dost sayısı göster
        p.setPen(Palet.FPS_KOT)
        p.drawText(x, y, f"CAM ---  Dusman:{dusuman_n}  Dost:{dost_n}")

    p.restore()


# Geriye dönük uyumluluk
def kesik_kutu_ciz(p, rx, ry, rw, rh, renk):
    p.save()
    p.setPen(QPen(renk, 1))
    p.setBrush(QBrush(Qt.BrushStyle.NoBrush))
    p.drawRect(rx, ry, rw, rh)
    p.restore()


def oncelik_badge_ciz(p, etiket, renk, rx, ry):
    pass


def hata_overlay_ciz_eski(p, hata_x, hata_y, cw, ch):
    hata_overlay_ciz(p, hata_x, hata_y, cw, ch)


def cv_crosshair_ciz(kare: np.ndarray,
                     cx: int, cy: int,
                     renk: tuple = None) -> None:
    if renk is None:
        renk = Palet.CV_CROSSHAIR
    cv2.circle(kare, (cx, cy), CROSSHAIR_IC_YARI_CAP, renk, -1)
    L = CROSSHAIR_COL_UZUNLUK
    cv2.line(kare, (cx - L, cy), (cx + L, cy), renk, 1)
    cv2.line(kare, (cx, cy - L), (cx, cy + L), renk, 1)


def cv_kilit_ciz(kare: np.ndarray,
                 cx: int, cy: int,
                 w: int, h: int,
                 renk: tuple = None) -> None:
    if renk is None:
        renk = Palet.CV_BRAKET_DUSUMAN
    kl = max(min(w, h) // KILIT_KOSE_KATSAYI, KILIT_KOSE_MIN)
    kt = KILIT_KALINLIK
    x1 = cx - w // 2; y1 = cy - h // 2
    x2 = cx + w // 2; y2 = cy + h // 2
    # Sol-üst
    cv2.line(kare, (x1, y1), (x1+kl, y1), renk, kt)
    cv2.line(kare, (x1, y1), (x1, y1+kl), renk, kt)
    # Sağ-üst
    cv2.line(kare, (x2-kl, y1), (x2, y1), renk, kt)
    cv2.line(kare, (x2, y1), (x2, y1+kl), renk, kt)
    # Sol-alt
    cv2.line(kare, (x1, y2-kl), (x1, y2), renk, kt)
    cv2.line(kare, (x1, y2), (x1+kl, y2), renk, kt)
    # Sağ-alt
    cv2.line(kare, (x2-kl, y2), (x2, y2), renk, kt)
    cv2.line(kare, (x2, y2-kl), (x2, y2), renk, kt)


def cv_hata_overlay(kare: np.ndarray,
                    hata_x: float,
                    hata_y: float,
                    kp_x: float = KP_X,
                    kp_y: float = KP_Y) -> None:
    if abs(hata_x) < 3 and abs(hata_y) < 3:
        return
    fh, fw = kare.shape[:2]
    mx, my = fw // 2, fh // 2
    tx = int(mx + hata_x)
    ty = int(my + hata_y)
    # Ok çizgisi - hedef zaten üst döngüde çiziliyor, burada küçük ok
    cv2.arrowedLine(kare, (mx, my), (tx, ty),
                    Palet.CV_BRAKET_DUSUMAN, 2, tipLength=0.25)
    adim_x = int(hata_x * kp_x)
    adim_y = int(hata_y * kp_y)
    metin = (f"ErrX:{hata_x:+.0f}px -> {adim_x:+d}adim  "
              f"ErrY:{hata_y:+.0f}px -> {adim_y:+d}adim")
    # Üst satıra yaz (FPS'nin altı)
    cv2.putText(kare, metin, (FPS_YAZI_X, FPS_YAZI_Y + 22),
                _CV, 0.45, (0, 165, 255), 1, cv2.LINE_AA)  # amber BGR


def cv_fps_overlay(kare: np.ndarray,
                   fps_cam: float,
                   fps_yolo: float = 0.0,
                   dusuman_n: int = 0,
                   dost_n: int = 0) -> None:
    metin = (f"CAM {fps_cam:.1f}  YOLO {fps_yolo:.1f}  "
             f"Dusman:{dusuman_n}  Dost:{dost_n}")
    cv2.putText(kare, metin, (FPS_YAZI_X, FPS_YAZI_Y),
                _CV, 0.5, Palet.CV_FPS, 1, cv2.LINE_AA)


def cv_tum_hedefler(kare: np.ndarray,
                    hedefler: List[Dict],
                    fps_cam: float = 0.0,
                    fps_yolo: float = 0.0) -> np.ndarray:
    out = kare.copy()
    fh, fw = out.shape[:2]
    mx, my = fw // 2, fh // 2

    dusuman_n = 0
    dost_n = 0

    for i, hedef in enumerate(hedefler):
        bbox = hedef.get("bbox")
        if not bbox:
            continue

        bx, by, bw, bh = [int(v) for v in bbox]
        hx = bx + bw // 2
        hy = by + bh // 2

        dost = bool(hedef.get("dost", False))
        onaylandi = bool(hedef.get("onaylandi", False))
        oncelikli = (i == 0) and not dost

        sinif = hedef.get("sinif") or hedef.get("renk", "?")
        guven = hedef.get("guven", 0.0)
        tid = hedef.get("track_id") or hedef.get("id", 0)

        # Renk seçimi
        if dost:
            kutu_renk = Palet.CV_KUTU_DOST
            braket_renk = Palet.CV_BRAKET_DOST
            bg_renk = (0, 130, 40)
            dost_n += 1
        elif onaylandi:
            kutu_renk = Palet.CV_KUTU_KILIT
            braket_renk = Palet.CV_BRAKET_KILIT
            bg_renk = (0, 170, 60)
            dusuman_n += 1
        else:
            kutu_renk = Palet.CV_KUTU_DUSUMAN
            braket_renk = Palet.CV_BRAKET_DUSUMAN
            bg_renk = (180, 60, 10)  # mavi-ish BGR arka plan
            dusuman_n += 1

        # 1. Merkez -> hedef çizgisi (kırmızı/yeşil)
        kalinlik = 3 if oncelikli else 2
        cv2.line(out, (mx, my), (hx, hy), braket_renk, kalinlik)

        # 2. Kutu kenarlığı + dost dolgu
        if dost:
            # Hafif yeşil dolgu (alpha overlay)
            overlay = out.copy()
            cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh),
                          (60, 210, 0), -1)
            cv2.addWeighted(overlay, 0.10, out, 0.90, 0, out)
        cv2.rectangle(out, (bx, by), (bx + bw, by + bh), kutu_renk, 1)

        # 3. Köşe L-braketleri (kırmızı/yeşil)
        cv_kilit_ciz(out, hx, hy, bw, bh, braket_renk)

        # 4. Hedef merkezinde dolu daire
        r = 6 if oncelikli else 4
        cv2.circle(out, (hx, hy), r, braket_renk, -1)

        # 5. Etiket - kutunun sol-üst köşesinde, renkli arka plan
        prefix = "[F]" if dost else "[E]"
        uz_m = hedef.get("uzaklik_m")
        dist_s = f" {uz_m:.1f}m" if uz_m is not None else ""
        etiket = f"{prefix}{sinif}{dist_s} {int(guven * 100)}% #{tid}"
        (tw, th), _ = cv2.getTextSize(etiket, _CV, 0.42, 1)
        cv2.rectangle(out, (bx, by), (bx + tw + 6, by + th + 6), bg_renk, -1)
        cv2.putText(out, etiket, (bx + 3, by + th + 3),
                    _CV, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

        # 6. Dost rozeti - kutunun alt ortası
        if dost:
            rozet = "DOST"
            (rw2, rh2), _ = cv2.getTextSize(rozet, _CV, 0.40, 1)
            rx2 = bx + (bw - rw2 - 6) // 2
            ry2 = by + bh - rh2 - 6
            cv2.rectangle(out, (rx2 - 2, ry2 - 2),
                          (rx2 + rw2 + 8, ry2 + rh2 + 4),
                          (0, 130, 40), -1)
            cv2.putText(out, rozet, (rx2 + 3, ry2 + rh2),
                        _CV, 0.40, (180, 255, 200), 1, cv2.LINE_AA)

    # Nişangah merkeze
    cv_crosshair_ciz(out, mx, my)

    # ErrX/ErrY - ilk düşman hedef baz alınır
    if hedefler:
        birinci = next((h for h in hedefler
                        if not h.get("dost", False)), None)
        if birinci:
            bbox = birinci.get("bbox")
            if bbox:
                bx, by, bw, bh = bbox
                cv_hata_overlay(out,
                                (bx + bw / 2) - mx,
                                (by + bh / 2) - my)

    # FPS overlay
    if fps_cam > 0 or fps_yolo > 0:
        cv_fps_overlay(out, fps_cam, fps_yolo, dusuman_n, dost_n)

    return out


# eski API uyumluluğu
def cv_hedef_ciz(kare: np.ndarray,
                 bbox: Tuple[int, int, int, int],
                 sinif: str = "?",
                 guven: float = 0.0,
                 track_id: int = 0,
                 dost: bool = False,
                 onaylandi: bool = False,
                 oncelikli: bool = False,
                 balon: bool = False) -> None:
    hedef: Dict = {
        "bbox": bbox, "sinif": sinif, "guven": guven,
        "track_id": track_id, "dost": dost,
        "onaylandi": onaylandi, "balon_eslesme": balon,
    }
    cv_tum_hedefler(kare, [hedef])


try:
    import supervision as sv
    _SV_ANN_OK = True
except ImportError:
    _SV_ANN_OK = False


class SupervisionAnnotator:

    def __init__(self, iz_uzunlugu: int = 30):
        self._hazir = False
        if not _SV_ANN_OK:
            return
        try:
            self._iz_ann = sv.TraceAnnotator(
                trace_length=iz_uzunlugu,
                thickness=1,
            )
            self._hazir = True
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "SupervisionAnnotator oluşturulamadı: %s", e)

    def annotate(self,
                 kare: np.ndarray,
                 hedefler: List[Dict],
                 fps_cam: float = 0.0,
                 fps_yolo: float = 0.0) -> np.ndarray:
        is_rgb = (kare.ndim == 3 and kare.shape[2] == 3)
        bgr = cv2.cvtColor(kare, cv2.COLOR_RGB2BGR) if is_rgb else kare.copy()

        if self._hazir and hedefler:
            dets = self._hedefler_to_dets(hedefler)
            if dets is not None:
                try:
                    bgr = self._iz_ann.annotate(bgr, dets)
                except Exception:
                    pass

        bgr = cv_tum_hedefler(bgr, hedefler, fps_cam, fps_yolo)
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB) if is_rgb else bgr

    def _hedefler_to_dets(self, hedefler: List[Dict]):
        if not _SV_ANN_OK:
            return None
        xyxy, class_ids, confidences, track_ids = [], [], [], []
        for h in hedefler:
            bbox = h.get("bbox")
            if not bbox:
                continue
            bx, by, bw, bh = bbox
            xyxy.append([bx, by, bx + bw, by + bh])
            class_ids.append(0)
            confidences.append(h.get("guven", 0.0))
            tid = h.get("track_id") or h.get("id", 0)
            track_ids.append(tid if tid else 0)
        if not xyxy:
            return None
        try:
            return sv.Detections(
                xyxy = np.array(xyxy, dtype=np.float32),
                class_id = np.array(class_ids, dtype=int),
                confidence = np.array(confidences, dtype=float),
                tracker_id = np.array(track_ids, dtype=int),
            )
        except Exception:
            return None

    @property
    def aktif(self) -> bool:
        return self._hazir
