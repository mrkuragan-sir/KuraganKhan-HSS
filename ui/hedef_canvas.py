import math
import time
from collections import deque
from typing import Dict, List, Optional

import numpy as np
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import (QPainter, QColor, QPen, QImage,
                              QLinearGradient, QRadialGradient, QFont,
                              QPixmap)
from PyQt6.QtWidgets import QWidget

import config
from .styles import C, CAM_COLORS
from utils.cizim import (tum_hedef_cizgileri, fps_overlay_ciz,
                          Palet)

# HUD fontları - L99: büyük ve net
HUD_FONT = QFont("Consolas", 14)
HUD_FONT_LRG = QFont("Consolas", 16, QFont.Weight.Bold)
HUD_FONT_LRG.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
HUD_FONT_SM = QFont("Consolas", 12)
HUD_FONT_XS = QFont("Consolas", 11)

MINIMAP_W, MINIMAP_H, MINIMAP_PAD = 140, 100, 12

RADAR_R = 80
RADAR_PAD = 14
RADAR_RINGS = 4
IZ_SURE = 1.0

LIDAR_RING_MIN_R = 30
LIDAR_RING_MAX_R = 80
LIDAR_DIST_MAX = 50.0


class HedefCanvas(QWidget):
    def __init__(self, kamera_idx: int = 0, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

        self._kamera_idx = kamera_idx
        self._np_kare: Optional[object] = None  # numpy ref (QImage lifetime)
        self._kare: Optional[QImage] = None
        self._hedefler: List[Dict] = []
        self._faz: str = "BEKLEMEDE"
        self._fps: float = 0.0
        self._konum_tarih: Dict[int, deque] = {}
        self._scan_y = 0
        self._lock_t = 0.0
        self._lock_up = True
        self._kilit_alpha = 0.0
        self._radar_aci = 0.0
        self._yolo_fps = 0.0
        self._lidar_m: float | None = None
        self._lidar_pulse = 0.0
        self._lidar_pulse_up = True

        # Performans cache'leri
        self._radar_bg: Optional[QPixmap] = None  # statik radar arkaplanı
        self._radar_bg_size = (0, 0)
        self._scaled: Optional[QImage] = None  # ölçeklenmiş kare
        self._scaled_src_size = (0, 0)
        self._scaled_wgt_size = (0, 0)
        self._dirty = False  # yeni frame/hedef geldi mi

        self._cam_color = QColor(CAM_COLORS.get(kamera_idx, C["accent"]))
        self._cam_label = "CAM A" if kamera_idx == 0 else "CAM B"

        # 30 fps animasyon (radar sweep, scan line, pulse)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._anim_adim)
        self._timer.start(33)

    def set_kamera_idx(self, idx: int) -> None:
        self._kamera_idx = idx
        self._cam_color = QColor(CAM_COLORS.get(idx, C["accent"]))
        self._cam_label = "CAM A" if idx == 0 else "CAM B"
        self._radar_bg = None  # cache geçersiz
        self.update()

    # Slot'lar
    def kare_guncelle(self, kare: np.ndarray) -> None:
        if (self._kamera_idx < len(config.KAMERA_AYARLAR) and
                not config.KAMERA_AYARLAR[self._kamera_idx].get("ETKIN", True)):
            return
        h, w, ch = kare.shape
        # Numpy dizisini sakla - QImage.data pointer'ının geçerliliği için zorunlu
        self._np_kare = kare
        self._kare = QImage(kare.data, w, h, ch * w,
                            QImage.Format.Format_RGB888)
        # Scaled cache'i geçersiz kıl
        self._scaled_src_size = (w, h)
        self._scaled = None
        self._dirty = True
        # update() gereksiz - 33ms timer zaten paintEvent tetikliyor

    def hedefleri_guncelle(self, hedefler) -> None:
        liste: List[Dict] = []
        for h in hedefler:
            if isinstance(h, dict):
                liste.append(h)
            else:
                d: Dict = {}
                for attr in ("id", "bbox", "sinif", "guven",
                             "balon_eslesme", "track_id", "renk",
                             "sekil", "oncelik", "onaylandi", "hiz", "dost"):
                    if hasattr(h, attr):
                        d[attr] = getattr(h, attr)
                if "track_id" in d and "id" not in d:
                    d["id"] = d["track_id"]
                liste.append(d)
        self._hedefler = liste

        simdi = time.time()
        aktif: set = set()
        for h in liste:
            hid = h.get("id", 0)
            x, y, w2, ht = h.get("bbox", (0, 0, 0, 0))
            if hid not in self._konum_tarih:
                self._konum_tarih[hid] = deque(maxlen=300)
            self._konum_tarih[hid].append((x + w2 / 2, y + ht / 2, simdi))
            aktif.add(hid)
        for hid in list(self._konum_tarih.keys()):
            if hid not in aktif:
                del self._konum_tarih[hid]
        self._dirty = True
        self.update()

    def sifirla(self) -> None:
        self._konum_tarih.clear()
        self._hedefler.clear()
        self._kare = None
        self._scaled = None
        self._faz = "BEKLEMEDE"  # DURDUR sonrası faz sıfırla
        self._dirty = True
        self.update()

    def faz_guncelle(self, faz: str) -> None:
        faz_u = faz.upper().strip()
        _map = {
            "BEKLE": "BEKLEMEDE",
            "HAZIR": "BEKLEMEDE",
            "BEKLEME": "BEKLEMEDE",
            "STANDBY": "BEKLEMEDE",
            "TARAMA": "TARANIYOR",
            "ARAMA": "ARANIYOR",
            "TESPIT": "TESPİT EDİLDİ",
            "TESPIT_EDILDI": "TESPİT EDİLDİ",
            "MANUEL_ONAY": "ONAY BEKLENİYOR",
            "ONAY_ZAMAN_ASIMI": "ZAMAN AŞIMI",
            "SIFIRLAMA": "SIFIRLANIYOR",
            "IMHA": "İMHA",
            "IMHA_KOMUTU": "İMHA KOMUTU",
            "TAKIP": "TAKİP",
        }
        if "KILIT" in faz_u or "KİLİT" in faz_u:
            self._faz = "KİLİT " + faz_u.replace("KİLİT","").replace("KILIT","").strip()
        else:
            self._faz = _map.get(faz_u, faz_u)
        self.update()

    def kamera_kapandi(self) -> None:
        self._np_kare = None
        self._kare = None
        self._scaled = None
        self._hedefler.clear()
        self._konum_tarih.clear()
        self._fps = 0.0
        self._yolo_fps = 0.0
        self._faz = "KAPALI"
        self._dirty = True
        self.update()  # anında yeniden çiz - timer'ı bekleme

    def fps_guncelle(self, fps: float) -> None: self._fps = fps
    def yolo_fps_guncelle(self, fps: float) -> None: self._yolo_fps = fps
    def hedef_kilitle(self, bilgi: dict) -> None:
        self._kilit_alpha = 1.0; self.update()
    def lidar_guncelle(self, uzaklik_m: float) -> None:
        self._lidar_m = uzaklik_m

    # Animasyon (33ms / ~30fps)
    def _anim_adim(self) -> None:
        step = 0.04
        self._lock_t += step if self._lock_up else -step
        if self._lock_t >= 1.0: self._lock_up = False
        if self._lock_t <= 0.0: self._lock_up = True

        self._scan_y = (self._scan_y + 2) % max(1, self.height())
        if self._kilit_alpha > 0:
            self._kilit_alpha = max(0.0, self._kilit_alpha - 0.025)
        self._radar_aci = (self._radar_aci + 3.5) % 360.0
        if self._lidar_m is not None:
            s = 0.055
            self._lidar_pulse += s if self._lidar_pulse_up else -s
            if self._lidar_pulse >= 1.0: self._lidar_pulse_up = False
            if self._lidar_pulse <= 0.0: self._lidar_pulse_up = True
        self.update()

    # paintEvent
    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cw, ch = self.width(), self.height()

        # 1. Frame / boş bg
        kare_w = kare_h = 0
        if self._kare is not None:
            kare_w = self._kare.width()
            kare_h = self._kare.height()
            wgt_sz = (cw, ch)
            if self._scaled is None or self._scaled_wgt_size != wgt_sz:
                self._scaled = self._kare.scaled(
                    cw, ch,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.FastTransformation)
                self._scaled_wgt_size = wgt_sz
            p.setOpacity(0.90)
            p.drawImage(0, 0, self._scaled)
            p.setOpacity(1.0)
        else:
            self._ciz_bos_bg(p, cw, ch)

        # 2. CRT tarama (sadece sistem aktifken)
        if self._faz not in ("BEKLEMEDE", "KAPALI"):
            p.setPen(QPen(QColor(0, 212, 255, 8), 1))
            p.drawLine(0, self._scan_y, cw, self._scan_y)

        # 3. Vignette
        self._vignette(p, cw, ch)

        # 4. İz
        kw = kare_w if kare_w > 0 else cw
        kh = kare_h if kare_h > 0 else ch
        self._ciz_izler(p, kw, kh, cw, ch)

        # 5. Hedef kutuları
        tum_hedef_cizgileri(p, self._hedefler,
                             kw, kh, cw, ch, self._lock_t)

        # 6. Nişangah
        self._ciz_nisangah(p, cw, ch)

        # 7. Radar (cache kullan)
        self._ciz_radar_panel(p, cw, ch, kw, kh)

        # 8. Mini-map
        if self._hedefler:
            self._ciz_minimap(p, cw, ch, kw, kh)

        # 9. HUD
        self._ciz_hud(p, cw, ch)

        # 10. Kamera rozet
        self._ciz_kamera_rozet(p, cw, ch)

        # 11. LiDAR
        if self._lidar_m is not None:
            self._ciz_lidar_rozet(p, cw, ch)

        self._dirty = False

    # Yardımcı çizimler
    def _ciz_bos_bg(self, p, w, h):
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(8, 11, 20))
        grad.setColorAt(1, QColor(5, 8, 15))
        p.fillRect(0, 0, w, h, grad)
        r, g, b = self._cam_color.red(), self._cam_color.green(), self._cam_color.blue()
        p.setPen(QPen(QColor(r, g, b, 14), 1))
        for x in range(0, w, 32): p.drawLine(x, 0, x, h)
        for y in range(0, h, 32): p.drawLine(0, y, w, y)
        p.setPen(QPen(QColor(r, g, b, 30), 1))
        p.drawLine(w//2, 0, w//2, h); p.drawLine(0, h//2, w, h//2)
        p.setFont(HUD_FONT_SM)
        p.setPen(QColor(r, g, b, 70))
        msg = f"NO SIGNAL  ·  {self._cam_label}"
        fm = p.fontMetrics()
        p.drawText(w//2 - fm.horizontalAdvance(msg)//2, h//2, msg)

    def _vignette(self, p, w, h):
        grad = QRadialGradient(w/2, h/2, max(w, h)*0.7)
        grad.setColorAt(0, QColor(0, 0, 0, 0))
        grad.setColorAt(1, QColor(0, 0, 0, 120))
        p.fillRect(0, 0, w, h, grad)

    def _ciz_izler(self, p, kw, kh, cw, ch):
        sw = cw/kw if kw > 0 else 1.0
        sh = ch/kh if kh > 0 else 1.0
        simdi = time.time()
        tip_map = {}
        for i, h in enumerate(self._hedefler):
            hid = h.get("id", 0)
            tip_map[hid] = "dost" if h.get("dost") else ("oncelik" if i==0 else "dusuman")
        for hid, tarih in self._konum_tarih.items():
            pts = [(x, y) for x, y, t in tarih if simdi - t <= IZ_SURE]
            if len(pts) < 2: continue
            tip = tip_map.get(hid, "dusuman")
            base = (QColor(255,159,10) if tip=="oncelik"
                    else QColor(0,230,118) if tip=="dost"
                    else QColor(255,45,85))
            n = len(pts)-1
            for i in range(1, n):
                frac = i/n
                a = int(30 + 160*frac)
                w2 = 1 if frac < 0.6 else 2
                p.setPen(QPen(QColor(base.red(),base.green(),base.blue(),a), w2))
                p.drawLine(int(pts[i-1][0]*sw), int(pts[i-1][1]*sh),
                           int(pts[i][0]*sw), int(pts[i][1]*sh))

    def _ciz_nisangah(self, p, cw, ch):
        cx, cy = cw//2, ch//2
        if self._hedefler:
            h0 = self._hedefler[0]
            locked = h0.get("onaylandi", False)
            balon = h0.get("balon_eslesme", False)
            renk = Palet.KILIT if locked else (Palet.BALON if balon else Palet.HEDEF)
            boyut = 24
        else:
            renk = QColor(200, 200, 200, 80); boyut = 18
        p.save()
        p.setPen(QPen(renk, 1.5))
        gap = 9
        p.drawLine(cx-boyut, cy, cx-gap, cy); p.drawLine(cx+gap, cy, cx+boyut, cy)
        p.drawLine(cx, cy-boyut, cx, cy-gap); p.drawLine(cx, cy+gap, cx, cy+boyut)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(cx-gap, cy-gap, gap*2, gap*2)
        dis = QColor(renk); dis.setAlpha(50)
        p.setPen(QPen(dis, 1))
        p.drawEllipse(cx-boyut, cy-boyut, boyut*2, boyut*2)
        p.setPen(QPen(renk, 2))
        tack = 7
        for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
            ox = cx + dx*(boyut-tack); oy = cy + dy*(boyut-tack)
            p.drawLine(ox, oy, ox+dx*tack, oy); p.drawLine(ox, oy, ox, oy+dy*tack)
        p.restore()
        if self._kilit_alpha > 0:
            a = int(self._kilit_alpha * 200)
            p.save(); p.setPen(QPen(QColor(0,255,120,a), 2))
            r = int(boyut*1.7)
            p.drawEllipse(cx-r, cy-r, r*2, r*2); p.restore()

    def _build_radar_bg(self, cw: int, ch: int) -> QPixmap:
        rcx = RADAR_PAD + RADAR_R
        rcy = ch - RADAR_PAD - RADAR_R
        px = QPixmap(cw, ch)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Arka plan daire
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(4, 10, 22, 220))
        p.drawEllipse(rcx-RADAR_R, rcy-RADAR_R, RADAR_R*2, RADAR_R*2)
        # Halkalar
        for i in range(1, RADAR_RINGS+1):
            r2 = int(RADAR_R*i/RADAR_RINGS)
            p.setPen(QPen(QColor(0, 160, 255, 15+i*6), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(rcx-r2, rcy-r2, r2*2, r2*2)
        # 45° çizgiler
        for a in range(0, 360, 45):
            a_r = math.radians(a)
            p.setPen(QPen(QColor(0, 160, 255, 18), 1))
            p.drawLine(rcx, rcy,
                       rcx+int(RADAR_R*math.cos(a_r)),
                       rcy+int(RADAR_R*math.sin(a_r)))
        # Crosshair
        p.setPen(QPen(QColor(0, 180, 255, 35), 1))
        p.drawLine(rcx-RADAR_R, rcy, rcx+RADAR_R, rcy)
        p.drawLine(rcx, rcy-RADAR_R, rcx, rcy+RADAR_R)
        # Dış çerçeve
        p.setPen(QPen(QColor(0, 180, 255, 100), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(rcx-RADAR_R, rcy-RADAR_R, RADAR_R*2, RADAR_R*2)
        # Merkez nokta
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 212, 255, 230))
        p.drawEllipse(rcx-3, rcy-3, 6, 6)
        p.setBrush(QColor(0, 212, 255, 60))
        p.drawEllipse(rcx-6, rcy-6, 12, 12)
        # Etiket
        p.setFont(HUD_FONT_XS)
        p.setPen(QColor(0, 180, 255, 120))
        p.drawText(rcx-RADAR_R, rcy+RADAR_R+15, "RADAR")
        p.end()
        return px

    def _ciz_radar_panel(self, p, cw, ch, kw, kh):
        # Cache kontrol
        if self._radar_bg is None or self._radar_bg_size != (cw, ch):
            self._radar_bg = self._build_radar_bg(cw, ch)
            self._radar_bg_size = (cw, ch)
        # Statik arka planı çiz
        p.drawPixmap(0, 0, self._radar_bg)

        rcx = RADAR_PAD + RADAR_R
        rcy = ch - RADAR_PAD - RADAR_R
        p.save()

        # Sweep fan (dinamik)
        for da in range(0, 70, 3):
            a_r = math.radians(-self._radar_aci + da)
            frac = 1.0 - da/70.0
            alpha = int(65 * frac * frac)
            p.setPen(QPen(QColor(0, 255, 100, alpha), 1))
            p.drawLine(rcx, rcy,
                       rcx+int(RADAR_R*math.cos(a_r)),
                       rcy+int(RADAR_R*math.sin(a_r)))
        # Ana sweep
        a_m = math.radians(-self._radar_aci)
        p.setPen(QPen(QColor(0, 255, 100, 220), 2))
        p.drawLine(rcx, rcy, rcx+int(RADAR_R*math.cos(a_m)), rcy+int(RADAR_R*math.sin(a_m)))

        # Bliplar
        for i, h in enumerate(self._hedefler):
            bbox = h.get("bbox")
            if not bbox: continue
            bx, by, bw, bh = bbox
            nx = ((bx+bw/2)/kw - 0.5)*2.0
            ny = ((by+bh/2)/kh - 0.5)*2.0
            rx = rcx + int(nx*RADAR_R*0.88)
            ry = rcy + int(ny*RADAR_R*0.88)
            dost = bool(h.get("dost")); ok = bool(h.get("onaylandi"))
            bc = (QColor(0,255,120,240) if ok else QColor(0,230,118,210) if dost
                  else QColor(255,159,10,240) if i==0 else QColor(255,45,85,190))
            rb = 5 if (ok or i==0) else 3
            lc = QColor(bc.red(),bc.green(),bc.blue(),45)
            p.setPen(QPen(lc,1)); p.drawLine(rcx,rcy,rx,ry)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(bc.red(),bc.green(),bc.blue(),55))
            p.drawEllipse(rx-rb-2,ry-rb-2,(rb+2)*2,(rb+2)*2)
            p.setBrush(bc); p.drawEllipse(rx-rb,ry-rb,rb*2,rb*2)
            if i==0 and not dost:
                p.setPen(QPen(QColor(bc.red(),bc.green(),bc.blue(),110),1.5))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(rx-rb-4,ry-rb-4,(rb+4)*2,(rb+4)*2)

        p.restore()

    def _ciz_minimap(self, p, cw, ch, kw, kh):
        mx = cw-MINIMAP_W-MINIMAP_PAD; my = ch-MINIMAP_H-MINIMAP_PAD
        p.fillRect(mx,my,MINIMAP_W,MINIMAP_H,QColor(10,16,28,210))
        p.setPen(QPen(QColor(C["border"]),1)); p.drawRect(mx,my,MINIMAP_W,MINIMAP_H)
        mcx=mx+MINIMAP_W//2; mcy=my+MINIMAP_H//2
        p.setPen(QPen(QColor(255,255,255,45),1))
        p.drawLine(mcx-5,mcy,mcx+5,mcy); p.drawLine(mcx,mcy-5,mcx,mcy+5)
        for h in self._hedefler:
            bbox=h.get("bbox");
            if not bbox: continue
            bx,by,bw,bh=bbox
            dx=mx+int((bx+bw/2)/kw*MINIMAP_W); dy=my+int((by+bh/2)/kh*MINIMAP_H)
            col=Palet.BALON if h.get("balon_eslesme") else Palet.HEDEF
            p.setPen(QPen(QColor(col.red(),col.green(),col.blue(),80),1))
            p.drawLine(dx,dy,mcx,mcy)
            p.setPen(QPen(col,3)); p.drawPoint(dx,dy)

    def _ciz_hud(self, p, w, h):
        dusuman_n = sum(1 for hh in self._hedefler if not hh.get("dost"))
        dost_n = sum(1 for hh in self._hedefler if hh.get("dost"))
        fps_overlay_ciz(p, self._fps, yolo_fps=self._yolo_fps,
                        dusuman_n=dusuman_n, dost_n=dost_n, x=12, y=24)

        # Faz - sağ üst (renk faza göre)
        if self._faz not in ("BEKLEMEDE", "KAPALI"):
            p.save()
            p.setFont(HUD_FONT_LRG)
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(self._faz)
            px, py = w-tw-20, 10
            pill = QRectF(px-10, py, tw+20, 30)
            # Renk belirleme
            _faz_u = self._faz.upper()
            if "KİLİT" in _faz_u or "İMHA" in _faz_u:
                _badge_col = QColor(C["danger"])
                _pill_bg = QColor(80, 0, 20, 160)
            elif "NISAN" in _faz_u or "NİŞAN" in _faz_u:
                _badge_col = QColor(C["warning"])
                _pill_bg = QColor(60, 30, 0, 160)
            elif "ONAY" in _faz_u or "TAŞMA" in _faz_u:
                _badge_col = QColor(C["warning"])
                _pill_bg = QColor(50, 25, 0, 160)
            else:
                _badge_col = QColor(C["accent"])
                _pill_bg = QColor(0, 0, 0, 130)
            p.setBrush(_pill_bg)
            p.setPen(QPen(QColor(_badge_col.red(), _badge_col.green(),
                                 _badge_col.blue(), 80), 1))
            p.drawRoundedRect(pill, 5, 5)
            p.setPen(_badge_col)
            p.drawText(px, py+22, self._faz)
            p.restore()

        # Alt orta - hedef özeti
        p.save()
        p.setFont(HUD_FONT_SM)
        if self._hedefler:
            msg = f"TARGETS: {len(self._hedefler)}   HOSTILE: {dusuman_n}"
            col = C["warning"] if dusuman_n > 0 else C["text_sec"]
        else:
            msg = "NO TARGETS IN FOV"
            col = C["text_dim"]
        fm2 = p.fontMetrics()
        tw2 = fm2.horizontalAdvance(msg)
        px2 = w//2 - tw2//2
        p.setBrush(QColor(0,0,0,120))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(px2-10, h-30, tw2+20, 22), 4, 4)
        p.setPen(QColor(col)); p.drawText(px2, h-12, msg)
        p.restore()

    def _ciz_kamera_rozet(self, p, w, h):
        col = self._cam_color; rw, rh = 80, 30; rx, ry = w-rw-12, 46
        p.save()
        p.setBrush(QColor(col.red(),col.green(),col.blue(),28))
        p.setPen(QPen(QColor(col.red(),col.green(),col.blue(),100),1.5))
        p.drawRoundedRect(QRectF(rx,ry,rw,rh),5,5)
        led_a = int(150+80*self._lock_t)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(col.red(),col.green(),col.blue(),led_a))
        p.drawEllipse(rx+9, ry+rh//2-5, 10, 10)
        p.setBrush(QColor(col.red(),col.green(),col.blue(),40))
        p.drawEllipse(rx+6, ry+rh//2-8, 16, 16)
        p.setPen(col)
        font = QFont("Consolas",12,QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,2.0)
        p.setFont(font)
        p.drawText(QRectF(rx+26,ry,rw-26,rh), Qt.AlignmentFlag.AlignVCenter, self._cam_label)
        p.restore()

    def _ciz_lidar_rozet(self, p, w, h):
        dist = self._lidar_m
        rx, ry, rw, rh = 12, 34, 140, 38
        p.save()
        p.setBrush(QColor(0,0,0,130))
        p.setPen(QPen(QColor(255,159,10,100),1))
        p.drawRoundedRect(QRectF(rx,ry,rw,rh),5,5)
        pa = int(80+110*self._lidar_pulse)
        p.setPen(QPen(QColor(255,159,10,pa),1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(rx,ry,rw,rh),5,5)
        cx0=rx+20; cy0=ry+rh//2
        for r_r, a_r in [(11,70),(7,120),(4,180)]:
            a2=int(a_r*(0.55+0.45*self._lidar_pulse))
            p.setPen(QPen(QColor(255,159,10,a2),1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(cx0-r_r,cy0-r_r,r_r*2,r_r*2)
        p.setFont(QFont("Consolas",15,QFont.Weight.Bold))
        p.setPen(QColor(255,159,10))
        p.drawText(QRectF(rx+32,ry+1,72,rh), Qt.AlignmentFlag.AlignVCenter,
                   f"{dist:.1f}")
        p.setFont(HUD_FONT_XS)
        p.setPen(QColor(255,159,10,170))
        p.drawText(QRectF(rx+104,ry+2,32,rh), Qt.AlignmentFlag.AlignVCenter, "m\nLDR")
        p.restore()
        if self._hedefler:
            cx, cy = w//2, h//2
            oran = max(0.1, min(1.0, 1.0 - dist/LIDAR_DIST_MAX))
            ring_r = int(LIDAR_RING_MIN_R + (LIDAR_RING_MAX_R-LIDAR_RING_MIN_R)*oran)
            ring_a = int(80+110*self._lidar_pulse)
            p.save()
            p.setPen(QPen(QColor(255,159,10,ring_a),1.5,Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(cx-ring_r,cy-ring_r,ring_r*2,ring_r*2)
            p.restore()
