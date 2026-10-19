from __future__ import annotations

from PyQt6.QtCore import Qt, QSize, QTimer, QTime
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QToolBar, QLabel, QPushButton, QFrame, QSizePolicy
)

from .styles import C, CAM_A_COLOR, CAM_B_COLOR
from .gorev_paneli import GorevPaneli
from .kamera_yonetici import KameraYonetici
from .acil_durdur import AcilDurdurOverlay
from .asama_ayarlar import AsamaAyarlarPanel, MotorAyarlariPanel, MotorKontrolPanel
from .widgets import LedIndicator

# Araç çubuğu QSS
_TB_QSS = f"""
QToolBar {{
    background    : {C['bg_panel']};
    border-bottom : 1px solid {C['border']};
    spacing       : 0px;
    padding       : 0px 12px;
}}
QFrame#NavGrup {{
    background    : {C['bg_card']};
    border        : 1px solid {C['border']};
    border-radius : 6px;
}}
QPushButton.NavBtn {{
    background    : transparent;
    border        : none;
    color         : {C['text_sec']};
    font-size     : 13px;
    font-weight   : 700;
    letter-spacing: 0.8px;
    padding       : 0 16px;
    min-height    : 44px;
    min-width     : 88px;
    border-radius : 0px;
}}
QPushButton.NavBtn:hover {{
    color      : {C['text_pri']};
    background : {C['bg_overlay']};
}}
QPushButton.NavBtn:checked {{
    color         : {C['accent']};
    background    : #0a1e2e;
    border-bottom : 2px solid {C['accent']};
}}
QPushButton.AuxBtn {{
    background    : {C['bg_card']};
    border        : 1px solid {C['border']};
    border-radius : 5px;
    color         : {C['text_sec']};
    font-size     : 13px;
    font-weight   : 700;
    letter-spacing: 0.8px;
    padding       : 0 14px;
    min-height    : 44px;
    min-width     : 90px;
}}
QPushButton.AuxBtn:hover {{
    color         : {C['accent']};
    border-color  : {C['border_act']};
    background    : {C['bg_overlay']};
}}
QPushButton.AuxBtn:checked {{
    color         : {C['accent']};
    background    : #071828;
    border-color  : {C['accent']};
    border-bottom : 2px solid {C['accent']};
}}
QLabel#DurumBadge {{
    background    : {C['bg_card']};
    border        : 1px solid {C['border']};
    border-left   : 6px solid {C['border']};
    border-radius : 5px;
    color         : {C['text_dim']};
    font-size     : 13px;
    font-weight   : 700;
    letter-spacing: 0.8px;
    padding       : 0 14px 0 12px;
    min-height    : 44px;
    min-width     : 240px;
    font-family   : 'Consolas', 'JetBrains Mono', monospace;
}}
QLabel#SistSaat {{
    color         : {C['text_sec']};
    font-size     : 13px;
    font-weight   : 600;
    letter-spacing: 1px;
    font-family   : 'Consolas', 'JetBrains Mono', monospace;
    background    : transparent;
    padding       : 0 6px;
}}
QPushButton#AcilBtn {{
    background    : #1a0008;
    color         : {C['danger']};
    border        : 1px solid #4a0015;
    border-radius : 5px;
    font-size     : 13px;
    font-weight   : 800;
    letter-spacing: 1px;
    padding       : 0 18px;
    min-height    : 44px;
    min-width     : 180px;
}}
QPushButton#AcilBtn:hover {{
    background    : #2d0010;
    border-color  : {C['danger']};
}}
QPushButton#AcilBtn:pressed {{
    background    : #0d0005;
    border-color  : #ff5577;
}}
"""

# Status durum tablosu
_DURUM = {
    "BEKLE": ("● STANDBY", "#3a5070", "#1e3050"),
    "BEKLEMEDE": ("● STANDBY", "#3a5070", "#1e3050"),
    "TARAMA": ("◉ SCANNING", "#00bcd4", "#00bcd4"),
    "ARAMA": ("◉ SEARCHING", "#00bcd4", "#00bcd4"),
    "TESPIT": ("⊕ TARGET DETECTED", "#ffd700", "#ffd700"),
    "KILIT": ("⊛ LOCKING ON", "#ff8c00", "#ff8c00"),
    "NIŞAN": ("⊕ ON TARGET", "#ff4500", "#ff4500"),
    "NISAN": ("⊕ ON TARGET", "#ff4500", "#ff4500"),
    "MANUEL_ONAY": ("⚠ AWAIT CONFIRM", "#ffab00", "#ffab00"),
    "ONAY_ZAMAN_ASIMI": ("✕ TIMED OUT", "#546e7a", "#37474f"),
    "SIFIRLAMA": ("↺ RESETTING", "#1e88e5", "#1565c0"),
    "ACIL_DURDUR": ("⚠ EMERGENCY STOP", "#ff1744", "#ff1744"),
    "HEDEF_VURULDU":("⦻ TARGET DOWN", "#ff1744", "#ff1744"),
}


# Per-camera toolbar strip
class _CamStatusStrip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self._fps = {0: 0.0, 1: 0.0}
        self._etkin = {0: False, 1: False}
        self._leds: dict[int, LedIndicator] = {}
        self._lbls: dict[int, QLabel] = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(3)

        for idx, (label, color) in enumerate(
                [("CAM A", CAM_A_COLOR), ("CAM B", CAM_B_COLOR)]):
            row = QHBoxLayout()
            row.setSpacing(5)
            row.setContentsMargins(0, 0, 0, 0)

            led = LedIndicator(C["text_dim"], size=7)
            self._leds[idx] = led
            row.addWidget(led)

            lbl = QLabel(label)
            lbl.setFixedWidth(40)
            lbl.setStyleSheet(
                f"color:{color};font-size:10px;font-weight:700;"
                f"letter-spacing:0.8px;font-family:Consolas;background:transparent;")
            self._lbls[idx] = lbl
            row.addWidget(lbl)

            fps_lbl = QLabel("—")
            fps_lbl.setFixedWidth(32)
            fps_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            fps_lbl.setStyleSheet(
                f"color:{C['text_dim']};font-size:10px;font-family:Consolas;"
                f"background:transparent;")
            setattr(self, f"_fps_lbl_{idx}", fps_lbl)
            row.addWidget(fps_lbl)

            lay.addLayout(row)

    def update_fps(self, cam_idx: int, fps: float) -> None:
        self._fps[cam_idx] = fps
        self._etkin[cam_idx] = fps > 0
        lbl = getattr(self, f"_fps_lbl_{cam_idx}", None)
        if lbl:
            if fps > 0:
                from .styles import fps_color
                col = fps_color(fps)
                lbl.setText(f"{fps:.0f}")
                lbl.setStyleSheet(
                    f"color:{col};font-size:10px;font-family:Consolas;"
                    f"background:transparent;")
            else:
                lbl.setText("—")
                lbl.setStyleSheet(
                    f"color:{C['text_dim']};font-size:10px;font-family:Consolas;"
                    f"background:transparent;")
        if cam_idx in self._leds:
            if fps >= 1:
                self._leds[cam_idx].set_state("active")
            elif self._etkin.get(cam_idx, False):
                self._leds[cam_idx].set_state("warn")
            else:
                self._leds[cam_idx].set_state("idle")


class AnaEkran(QMainWindow):

    def __init__(self, canvases: list, gorev_paneli: GorevPaneli,
                 kamera_yonetici: KameraYonetici):
        super().__init__()
        self.setWindowTitle("TTURKS — HAVA SAVUNMA SİSTEMİ")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

        from .styles import GLOBAL_QSS
        self.setStyleSheet(GLOBAL_QSS + _TB_QSS)

        self._canvases = canvases
        self._gp = gorev_paneli
        self._km = kamera_yonetici
        self._faz_aktif: bool = False

        self._ui_kur()

        self._overlay = AcilDurdurOverlay(self)
        self._overlay.kapatildi.connect(self._gp.acil_reset)
        self._overlay.kapatildi.connect(self._acil_reset_badge)

        self._f12 = QShortcut(QKeySequence("F12"), self)
        self._f12.activated.connect(self._gp.acil_durdur_tetikle)

        # Saat timer'ı
        self._saat_timer = QTimer(self)
        self._saat_timer.timeout.connect(self._saat_guncelle)
        self._saat_timer.start(1000)
        self._saat_guncelle()

    def _ui_kur(self) -> None:
        tb = QToolBar("Ana")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setFixedHeight(64)
        self.addToolBar(tb)

        # LOGO
        logo_w = QWidget()
        logo_lay = QVBoxLayout(logo_w)
        logo_lay.setContentsMargins(4, 0, 10, 0)
        logo_lay.setSpacing(1)
        logo_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        logo_top = QLabel("⬡  TTURKS")
        logo_top.setStyleSheet(
            f"color:{C['accent']};font-weight:800;font-size:16px;"
            f"letter-spacing:4px;font-family:'Consolas',monospace;"
            f"background:transparent;")

        logo_bot = QLabel("HAVA SAVUNMA")
        logo_bot.setStyleSheet(
            f"color:{C['text_dim']};font-size:9px;font-weight:600;"
            f"letter-spacing:3.5px;font-family:'Consolas',monospace;"
            f"background:transparent;")

        logo_lay.addWidget(logo_top)
        logo_lay.addWidget(logo_bot)
        tb.addWidget(logo_w)

        tb.addWidget(self._vsep())

        # SEGMENTED NAV
        self._tb_asama_btn: dict[int, QPushButton] = {}
        nav_grp = self._segmented_group([
            (1, "AŞAMA  1", "Aşama 1 ayarları"),
            (2, "AŞAMA  2", "Aşama 2 ayarları"),
            (3, "AŞAMA  3", "Aşama 3 ayarları"),
        ], self._tb_asama_btn, self._asama_toggle)
        tb.addWidget(nav_grp)

        tb.addWidget(self._hspace(8))

        # YARDIMCI BUTONLAR
        self._tb_motor_btn = self._aux_btn("⚙  AYARLAR", "Donanım & Kamera Kalibrasyonu")
        self._tb_motor_btn.clicked.connect(self._motor_toggle)
        tb.addWidget(self._tb_motor_btn)

        tb.addWidget(self._hspace(6))

        self._tb_kontrol_btn = self._aux_btn("🕹  KONTROL", "Joystick + yön tuşları + manuel ateş")
        self._tb_kontrol_btn.clicked.connect(self._kontrol_toggle)
        tb.addWidget(self._tb_kontrol_btn)

        tb.addWidget(self._hspace(8))
        tb.addWidget(self._vsep())
        tb.addWidget(self._hspace(8))

        self._cam_strip = _CamStatusStrip()
        self._cam_strip.setFixedWidth(92)
        tb.addWidget(self._cam_strip)

        # ESNEK BOŞLUK
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        mid_w = QWidget()
        mid_lay = QVBoxLayout(mid_w)
        mid_lay.setContentsMargins(0, 0, 0, 0)
        mid_lay.setSpacing(0)
        mid_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sys_lbl = QLabel("T · T · U · R · K · S")
        sys_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sys_lbl.setStyleSheet(
            f"color:{C['accent']};font-weight:900;font-size:15px;"
            f"letter-spacing:6px;font-family:'Consolas','Courier New',monospace;"
            f"background:transparent;")

        sub_lbl = QLabel("HAVA SAVUNMA SİSTEMİ")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setStyleSheet(
            f"color:{C['text_dim']};font-size:9px;font-weight:500;"
            f"letter-spacing:3px;font-family:'Consolas','Courier New',monospace;"
            f"background:transparent;")

        self._saat_lbl = QLabel("--:--:--")
        self._saat_lbl.setObjectName("SistSaat")
        self._saat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        mid_lay.addWidget(sys_lbl)
        mid_lay.addWidget(sub_lbl)
        mid_lay.addWidget(self._saat_lbl)
        tb.addWidget(mid_w)

        # ESNEK BOŞLUK
        spacer2 = QWidget()
        spacer2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer2)

        # DURUM BADGE
        self._durum_badge = QLabel("● STANDBY")
        self._durum_badge.setObjectName("DurumBadge")
        self._durum_badge.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        tb.addWidget(self._durum_badge)

        tb.addWidget(self._hspace(10))
        tb.addWidget(self._vsep())
        tb.addWidget(self._hspace(10))

        # ACİL DURDUR
        acil = QPushButton("⚠  ACİL  [F12]")
        acil.setObjectName("AcilBtn")
        acil.clicked.connect(self._gp.acil_durdur_tetikle)
        tb.addWidget(acil)

        # ANA LAYOUT - SPLITTER
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)

        splitter.addWidget(self._gp)

        orta = QWidget()
        orta.setStyleSheet(f"background:{C['bg_deep']};")
        ov = QVBoxLayout(orta)
        ov.setContentsMargins(0, 0, 0, 0)
        ov.setSpacing(1)
        for idx, cv in enumerate(self._canvases):
            if hasattr(cv, 'set_kamera_idx'):
                cv.set_kamera_idx(idx)
            if idx > 0:
                sep_h = QFrame()
                sep_h.setFrameShape(QFrame.Shape.HLine)
                sep_h.setFixedHeight(2)
                sep_h.setStyleSheet(f"background:{C['border']};")
                ov.addWidget(sep_h)
            ov.addWidget(cv, 1)

        splitter.addWidget(orta)
        splitter.addWidget(self._km)
        splitter.setSizes([320, 940, 200])
        self.setCentralWidget(splitter)

        # Float paneller - önceden oluşturulur (donma/flash önleme)
        self._ayar_panel = None
        self._motor_panel = None
        self._kontrol_panel = None

        sb = self.statusBar()
        sb.setStyleSheet(
            f"QStatusBar{{background:{C['bg_panel']};color:{C['text_dim']};"
            f"border-top:1px solid {C['border']};font-size:13px;padding:0 8px;}}"
            f"QStatusBar QLabel{{color:{C['text_dim']};font-size:13px;padding:0 6px;}}")
        sb.showMessage(
            f"TTURKS  ·  Sistem hazır  ·  F12 → Acil Durdur  ·  "
            f"CAM A={CAM_A_COLOR[:4]}  CAM B={CAM_B_COLOR[:4]}")

    @staticmethod
    def _vsep() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.VLine)
        f.setFixedWidth(1)
        f.setStyleSheet(f"background:{C['border']};margin:10px 0;")
        return f

    @staticmethod
    def _hspace(w: int) -> QWidget:
        sp = QWidget(); sp.setFixedWidth(w)
        return sp

    @staticmethod
    def _aux_btn(metin: str, tip: str) -> QPushButton:
        b = QPushButton(metin)
        b.setProperty("class", "AuxBtn")
        b.setStyleSheet(
            f"QPushButton{{background:{C['bg_card']};color:{C['text_sec']};"
            f"border:1px solid {C['border']};border-radius:5px;"
            f"font-size:13px;font-weight:700;letter-spacing:0.8px;"
            f"padding:0 14px;min-height:44px;min-width:90px;}}"
            f"QPushButton:hover{{color:{C['accent']};border-color:{C['border_act']};"
            f"background:{C['bg_overlay']};}}"
            f"QPushButton:checked{{color:{C['accent']};background:#071828;"
            f"border-color:{C['accent']};border-bottom:2px solid {C['accent']};}}")
        b.setCheckable(True)
        b.setToolTip(tip)
        return b

    @staticmethod
    def _segmented_group(items: list[tuple], btn_dict: dict,
                         on_click) -> QWidget:
        grp = QWidget()
        grp.setObjectName("NavGrup")
        grp.setStyleSheet(
            f"QWidget#NavGrup{{background:{C['bg_card']};"
            f"border:1px solid {C['border']};border-radius:6px;}}"
        )
        lay = QHBoxLayout(grp)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        for i, (key, metin, tip) in enumerate(items):
            btn = QPushButton(metin)
            btn.setCheckable(True)
            btn.setToolTip(tip)
            btn.setFixedHeight(48)

            if len(items) == 1:
                radius = "border-radius:5px;"
            elif i == 0:
                radius = "border-top-left-radius:5px;border-bottom-left-radius:5px;"
            elif i == len(items) - 1:
                radius = "border-top-right-radius:5px;border-bottom-right-radius:5px;"
            else:
                radius = "border-radius:0px;"

            sep_right = (f"border-right:1px solid {C['border']};"
                         if i < len(items) - 1 else "")

            btn.setStyleSheet(
                f"QPushButton{{background:transparent;border:none;{sep_right}"
                f"color:{C['text_sec']};font-size:13px;font-weight:700;"
                f"letter-spacing:0.8px;padding:0 18px;{radius}}}"
                f"QPushButton:hover{{color:{C['text_pri']};background:{C['bg_overlay']};}}"
                f"QPushButton:checked{{color:{C['accent']};background:#0a1e2e;"
                f"border-bottom:2px solid {C['accent']};}}"
            )
            btn.clicked.connect(lambda _, k=key: on_click(k))
            btn_dict[key] = btn
            lay.addWidget(btn)

        return grp

    def _asama_toggle(self, no: int) -> None:
        if self._ayar_panel is None:
            self._ayar_panel = AsamaAyarlarPanel(self)
        for n, b in self._tb_asama_btn.items():
            b.setChecked(False)
        self._gp._asama_sec(no)
        self._tb_asama_btn[no].setChecked(True)
        self._ayar_panel.toggle(no)

    def _motor_toggle(self) -> None:
        if self._motor_panel is None:
            self._motor_panel = MotorAyarlariPanel(self)
            # tus_degisti -> kontrol paneli kısayolları güncelle
            self._motor_panel.tus_degisti.connect(self._tus_guncelle)
        self._motor_panel.toggle()
        self._tb_motor_btn.setChecked(self._motor_panel.isVisible())

    def _kontrol_toggle(self) -> None:
        if self._kontrol_panel is None:
            self._kontrol_panel = MotorKontrolPanel(self)
        self._kontrol_panel.toggle()
        self._tb_kontrol_btn.setChecked(self._kontrol_panel.isVisible())

    def _tus_guncelle(self, key: str, deger: str) -> None:
        if self._kontrol_panel is not None:
            self._kontrol_panel.tus_guncelle(key, deger)


    def _saat_guncelle(self) -> None:
        self._saat_lbl.setText(QTime.currentTime().toString("HH:mm:ss"))

    def _acil_reset_badge(self) -> None:
        self._faz_aktif = False
        self.durum_guncelle("BEKLEMEDE")

    def _badge_stil(self, fg: str, border_col: str) -> str:
        return (
            f"color:{fg};background:{C['bg_card']};"
            f"border:1px solid {C['border']};border-left:6px solid {border_col};"
            f"border-radius:5px;font-size:13px;font-weight:700;"
            f"letter-spacing:0.8px;padding:0 14px 0 12px;"
            f"min-height:44px;min-width:240px;"
            f"font-family:'Consolas','JetBrains Mono',monospace;")

    def durum_guncelle(self, faz: str, kaynak: str = "asama") -> None:
        if kaynak == "det" and self._faz_aktif:
            return
        faz_u = faz.upper().strip()

        if "KILIT" in faz_u or "KİLİT" in faz_u:
            num = faz_u.replace("KILIT","").replace("KİLİT","").strip()
            metin = f"⊛ LOCKING {num}" if num else "⊛ LOCKING ON"
            fg, bc = "#ff8c00", "#ff8c00"
        elif "MANUEL" in faz_u:
            metin, fg, bc = "⚠ AWAIT CONFIRM", "#ffab00", "#ffab00"
        elif "VURULDU" in faz_u or "ATES" in faz_u or "ATEŞ" in faz_u:
            metin, fg, bc = "⦻ TARGET DOWN", "#ff1744", "#ff1744"
        else:
            row = _DURUM.get(faz_u)
            if row:
                metin, fg, bc = row
            else:
                metin, fg, bc = f"● {faz_u}", "#3a5070", "#1e3050"

        self._durum_badge.setText(metin)
        self._durum_badge.setStyleSheet(self._badge_stil(fg, bc))

    def hedef_durumu_guncelle(self, hedefler: list) -> None:
        if self._faz_aktif:
            return
        dusmanlar = [h for h in hedefler if not getattr(h, "dost", False)]
        self.durum_guncelle("TESPIT" if dusmanlar else "TARAMA", kaynak="det")

    def imha_bildir_durum(self, _: dict) -> None:
        self._faz_aktif = True
        self.durum_guncelle("HEDEF_VURULDU")

    def faz_guncelle(self, faz: str) -> None:
        faz_u = faz.upper()
        self._faz_aktif = faz_u not in ("BEKLE", "BEKLEMEDE", "")
        self.durum_guncelle(faz, kaynak="asama")
        self.statusBar().showMessage(f"SYS › {faz}", 3000)

    def model_siniflari_guncelle(self, siniflari: list[str]) -> None:
        if self._ayar_panel is not None:
            self._ayar_panel.model_siniflari_guncelle(siniflari)

    def model_siniflari_guncelle_cam(self, cam_idx: int, siniflari: list[str]) -> None:
        if self._ayar_panel is not None:
            self._ayar_panel.model_siniflari_guncelle(siniflari)
        if self._motor_panel is not None:
            self._motor_panel.model_siniflari_guncelle(cam_idx, siniflari)

    def kamera_fps_guncelle(self, cam_idx: int, fps: float) -> None:
        if hasattr(self, "_cam_strip"):
            self._cam_strip.update_fps(cam_idx, fps)
        # GorevPaneli'nin DualCameraStatus'ını da güncelle
        if hasattr(self._gp, "kamera_fps_guncelle"):
            self._gp.kamera_fps_guncelle(cam_idx, fps)

    def acil_durdur_overlay_goster(self) -> None:
        self._overlay.setGeometry(self.centralWidget().geometry())
        self._overlay.goster()

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        if hasattr(self, "_overlay") and self._overlay.isVisible():
            self._overlay.setGeometry(self.centralWidget().geometry())

    # Proxy - GorevPaneli slot aliases (eski bağlantılar için)
    def hedef_listesi_al_b(self, hedefler) -> None:
        self._gp.hedef_listesi_guncelle(hedefler)
