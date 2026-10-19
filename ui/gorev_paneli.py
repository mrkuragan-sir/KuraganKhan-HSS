import time
import logging
from pathlib import Path

import config
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QListWidget, QListWidgetItem, QFrame,
    QScrollArea, QStackedWidget, QTextEdit
)

from .styles import C, CAM_A_COLOR, CAM_B_COLOR
from .widgets import (LedIndicator, PhaseBadge, DualCameraStatus,
                      ThreatCountBadge, MiniTelRow)

log = logging.getLogger(__name__)


# Yardımcılar
def _divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(
        f"background:{C['border']};max-height:1px;margin:2px 0;border:none;")
    return f


def _sec(title: str, accent: str = None) -> QLabel:
    clr = accent or C["accent"]
    lbl = QLabel(title)
    lbl.setStyleSheet(
        f"color:{clr};font-size:10px;font-weight:700;"
        f"letter-spacing:1.8px;background:transparent;")
    return lbl


# Kompakt Aşama Seçici
class _AsamaWidget(QWidget):
    mod_degisti = pyqtSignal(int, str)
    onayla_clicked = pyqtSignal()
    asama_secildi = pyqtSignal(int)

    _RENK = {
        1: C["accent"],
        2: "#7b68ee",
        3: "#ff8c00",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self._secili = 1
        self._sistem_aktif = 1
        self._mod = {1: "OTONOM", 2: "OTONOM", 3: "OTONOM"}
        self._cfg_labels: dict[int, dict[str, QLabel]] = {1: {}, 2: {}, 3: {}}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # Seçici satır
        sel_frame = QWidget()
        sel_frame.setStyleSheet(
            f"background:{C['bg_panel']};border:1px solid {C['border']};"
            f"border-radius:6px;")
        sf_lay = QHBoxLayout(sel_frame)
        sf_lay.setContentsMargins(3, 3, 3, 3)
        sf_lay.setSpacing(3)

        self._sel: dict[int, QPushButton] = {}
        for no in (1, 2, 3):
            r = self._RENK[no]
            btn = QPushButton(f"AŞAMA {no}")
            btn.setCheckable(True)
            btn.setMinimumHeight(34)
            btn.setStyleSheet(
                f"QPushButton{{background:transparent;border:none;"
                f"color:{C['text_dim']};font-size:13px;font-weight:700;"
                f"letter-spacing:0.5px;border-radius:4px;padding:0 6px;}}"
                f"QPushButton:hover{{color:{r};background:{C['bg_overlay']};}}"
                f"QPushButton:checked{{color:{r};background:{C['bg_input']};"
                f"border-bottom:2px solid {r};}}")
            btn.clicked.connect(lambda _, n=no: self._sec_goster(n))
            self._sel[no] = btn
            sf_lay.addWidget(btn, 1)
        self._sel[1].setChecked(True)
        root.addWidget(sel_frame)

        # İçerik kartı
        self._kart = QFrame()
        self._kart.setObjectName("AsamaKF")
        kl = QVBoxLayout(self._kart)
        kl.setContentsMargins(14, 12, 14, 12)
        kl.setSpacing(9)

        # Başlık
        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        self._led = LedIndicator(size=12)
        self._led.set_state("idle")
        self._isim = QLabel("AŞAMA  1")
        self._isim.setStyleSheet(
            f"color:{C['accent']};font-size:14px;font-weight:800;"
            f"letter-spacing:1.2px;background:transparent;")
        self._aktif_tag = QLabel("AKTİF")
        self._aktif_tag.setStyleSheet(
            f"color:{C['accent']};font-size:10px;font-weight:800;"
            f"letter-spacing:2px;background:#071828;"
            f"border:1px solid {C['accent']};border-radius:3px;padding:1px 7px;")
        self._aktif_tag.setVisible(False)
        hdr.addWidget(self._led)
        hdr.addWidget(self._isim, 1)
        hdr.addWidget(self._aktif_tag)
        kl.addLayout(hdr)

        # Ateş modu combo
        mr = QHBoxLayout()
        mr.setSpacing(10)
        ml = QLabel("ATIŞ MODU")
        ml.setStyleSheet(
            f"color:{C['text_dim']};font-size:13px;font-weight:600;"
            f"letter-spacing:0.8px;background:transparent;min-width:82px;")
        self._mod_combo = QComboBox()
        self._mod_combo.addItems(["OTONOM", "MANUEL"])
        self._mod_combo.setStyleSheet(
            f"QComboBox{{background:{C['bg_input']};color:{C['text_pri']};"
            f"border:1px solid {C['border']};border-radius:4px;"
            f"font-size:13px;padding:2px 8px;min-height:30px;}}"
            f"QComboBox::drop-down{{border:none;width:18px;}}"
            f"QComboBox QAbstractItemView{{background:{C['bg_card']};"
            f"color:{C['text_pri']};border:1px solid {C['border_act']};"
            f"selection-background-color:{C['bg_overlay']};}}")
        self._mod_combo.currentTextChanged.connect(self._on_mod_change)
        mr.addWidget(ml)
        mr.addWidget(self._mod_combo, 1)
        kl.addLayout(mr)

        # Config stack
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background:transparent;")
        for no in (1, 2, 3):
            page, labels = self._build_cfg_page(no)
            self._stack.addWidget(page)
            self._cfg_labels[no] = labels
        kl.addWidget(self._stack)

        # ONAYLA butonu
        self._onay = QPushButton("✓   MANUEL ONAYLA")
        self._onay.setStyleSheet(
            f"QPushButton{{background:#004d30;color:{C['success']};"
            f"border:1px solid #00804d;border-radius:5px;"
            f"font-size:13px;font-weight:800;letter-spacing:0.8px;"
            f"padding:6px;min-height:36px;}}"
            f"QPushButton:hover{{background:#006040;border-color:{C['success']};}}"
            f"QPushButton:pressed{{background:#003020;}}")
        self._onay.setVisible(False)
        self._onay.clicked.connect(self.onayla_clicked)
        kl.addWidget(self._onay)

        root.addWidget(self._kart)
        self._uygula_stil(1)

    def _build_cfg_page(self, no: int) -> tuple[QWidget, dict]:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 3, 0, 0)
        lay.setSpacing(4)
        labels: dict[str, QLabel] = {}

        def satir(key: str, etiket: str, deger: str) -> None:
            row = QHBoxLayout()
            le = QLabel(etiket + ":")
            le.setStyleSheet(
                f"color:{C['text_dim']};font-size:13px;"
                f"background:transparent;min-width:110px;")
            lv = QLabel(deger)
            lv.setStyleSheet(
                f"color:{C['text_mono']};font-size:12px;"
                f"font-family:Consolas;font-weight:600;"
                f"background:transparent;")
            labels[key] = lv
            row.addWidget(le)
            row.addWidget(lv, 1)
            lay.addLayout(row)

        if no == 1:
            cfg = config.ASAMA_1
            satir("guven", "Güven Eşiği",
                  f"{cfg.get('GUVEN_ESIGI', 0.55):.2f}")
            satir("deadzone","Dead Zone",
                  f"{cfg.get('DEAD_ZONE_PIXEL', 8)} px")
            satir("sure", "Onay Zaman Aşımı",
                  f"{cfg.get('MANUEL_ONAY_TIMEOUT', 5.0):.1f} s")
        elif no == 2:
            cfg = config.ASAMA_2
            satir("guven", "Güven Eşiği",
                  f"{cfg.get('GUVEN_ESIGI', 0.50):.2f}")
            satir("uzlasma", "Uzlaşma Eşiği",
                  f"{cfg.get('UZLASMA_ESIGI', 0.55):.2f}")
            satir("suru", "Max Sürü Boyutu",
                  f"{cfg.get('MAX_SURU_BOYUTU', 20)}")
        elif no == 3:
            cfg = config.ASAMA_3
            satir("guven", "Güven Eşiği",
                  f"{cfg.get('GUVEN_ESIGI', 0.65):.2f}")
            satir("uzlasma", "Uzlaşma Eşiği",
                  f"{cfg.get('UZLASMA_ESIGI', 0.70):.2f}")
            satir("deadzone","Dead Zone",
                  f"{cfg.get('DEAD_ZONE_PIXEL', 6)} px")
        return w, labels

    def _uygula_stil(self, no: int) -> None:
        r = self._RENK.get(no, C["accent"])
        self._kart.setStyleSheet(
            f"QFrame#AsamaKF{{background:{C['bg_card']};"
            f"border:1px solid {C['border']};"
            f"border-left:4px solid {r};"
            f"border-radius:6px;}}")
        self._isim.setText(f"AŞAMA  {no}")
        self._isim.setStyleSheet(
            f"color:{r};font-size:14px;font-weight:800;"
            f"letter-spacing:1.2px;background:transparent;")
        self._aktif_tag.setStyleSheet(
            f"color:{r};font-size:10px;font-weight:800;"
            f"letter-spacing:2px;background:#071828;"
            f"border:1px solid {r};border-radius:3px;padding:1px 7px;")
        self._led.set_color(r)
        self._stack.setCurrentIndex(no - 1)
        for n, btn in self._sel.items():
            btn.setChecked(n == no)
        self._mod_combo.blockSignals(True)
        self._mod_combo.setCurrentText(self._mod.get(no, "OTONOM"))
        self._mod_combo.blockSignals(False)

    def _sec_goster(self, no: int) -> None:
        self._secili = no
        self._uygula_stil(no)
        sistem = no == self._sistem_aktif
        self._aktif_tag.setVisible(sistem)
        self._led.set_state("active" if sistem else "idle")

    def _on_mod_change(self, mod: str) -> None:
        no = self._secili
        self._mod[no] = mod
        self.mod_degisti.emit(no, mod)

    def set_sistem_aktif(self, no: int) -> None:
        self._sistem_aktif = no
        self._sec_goster(no)
        self.asama_secildi.emit(no)

    def set_onay_visible(self, visible: bool) -> None:
        self._onay.setVisible(visible)

    def get_mod(self, no: int) -> str:
        return self._mod.get(no, "OTONOM")

    def cfg_guncelle(self) -> None:
        cfgs = {
            1: (config.ASAMA_1, {
                "guven": lambda c: f"{c.get('GUVEN_ESIGI', 0.55):.2f}",
                "deadzone":lambda c: f"{c.get('DEAD_ZONE_PIXEL', 8)} px",
                "sure": lambda c: f"{c.get('MANUEL_ONAY_TIMEOUT', 5.0):.1f} s",
            }),
            2: (config.ASAMA_2, {
                "guven": lambda c: f"{c.get('GUVEN_ESIGI', 0.50):.2f}",
                "uzlasma": lambda c: f"{c.get('UZLASMA_ESIGI', 0.55):.2f}",
                "suru": lambda c: f"{c.get('MAX_SURU_BOYUTU', 20)}",
            }),
            3: (getattr(config, "ASAMA_3", {}), {
                "guven": lambda c: f"{c.get('GUVEN_ESIGI', 0.65):.2f}",
                "uzlasma": lambda c: f"{c.get('UZLASMA_ESIGI', 0.70):.2f}",
                "deadzone":lambda c: f"{c.get('DEAD_ZONE_PIXEL', 6)} px",
            }),
        }
        for no, (cfg, fns) in cfgs.items():
            for key, fn in fns.items():
                lbl = self._cfg_labels[no].get(key)
                if lbl:
                    try:
                        lbl.setText(fn(cfg))
                    except Exception:
                        pass


# Debug Dialog
class DebugDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DEBUG / CONFIG")
        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.resize(620, 700)
        self.setStyleSheet(
            f"QDialog{{background:{C['bg_panel']};}}"
            f"QTextEdit{{background:{C['bg_deep']};color:{C['success']};"
            f"font-family:Consolas;font-size:13px;border:none;padding:8px;}}"
            f"QPushButton{{background:{C['bg_card']};color:{C['text_sec']};"
            f"border:1px solid {C['border']};border-radius:4px;"
            f"padding:4px 12px;font-size:12px;}}"
            f"QPushButton:hover{{color:{C['accent']};border-color:{C['accent']};}}"
            f"QLabel{{background:transparent;}}")

        self._kaynak_fn = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        hrow = QHBoxLayout()
        lbl = QLabel("● DEBUG / CONFIG")
        lbl.setStyleSheet(
            f"color:{C['accent']};font-weight:700;font-size:14px;"
            f"letter-spacing:1px;background:transparent;")
        self._refresh_btn = QPushButton("⟳ Yenile")
        self._refresh_btn.setFixedHeight(30)
        self._refresh_btn.clicked.connect(self.guncelle)
        hrow.addWidget(lbl, 1)
        hrow.addWidget(self._refresh_btn)
        lay.addLayout(hrow)

        self._txt = QTextEdit()
        self._txt.setReadOnly(True)
        lay.addWidget(self._txt, 1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.guncelle)

    def showEvent(self, e):
        super().showEvent(e)
        self.guncelle()
        self._timer.start(1000)

    def hideEvent(self, e):
        super().hideEvent(e)
        self._timer.stop()

    def guncelle(self) -> None:
        if self._kaynak_fn:
            self._txt.setPlainText(self._kaynak_fn())


# Ana Panel
class GorevPaneli(QWidget):
    baslat = pyqtSignal(int)
    durdur = pyqtSignal()
    acil_durdur = pyqtSignal()
    atis_modu_degisti = pyqtSignal(int, str)
    manuel_onayla = pyqtSignal()
    asama_secildi = pyqtSignal(int)

    def __init__(self, imha_sirasi: list | None = None, parent=None):
        super().__init__(parent)
        self._imha_sirasi = list(imha_sirasi or [])
        self._baslangic_t: float | None = None
        self._aktif = False
        self._aktif_asama = 1
        self._asama_mod = {1: "OTONOM", 2: "OTONOM", 3: "OTONOM"}
        self._model_siniflari: list[str] = []
        self._debug_dialog: DebugDialog | None = None
        self._lidar_m: float | None = None
        self._hedefler: dict[int, list] = {0: [], 1: []}  # kameralara özel
        self._cam_fps: dict[int, float] = {0: 0.0, 1: 0.0}  # anlık FPS

        # Süreler
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._sure_guncelle)
        self._timer.start(1000)

        # Config refresh
        self._cfg_timer = QTimer(self)
        self._cfg_timer.timeout.connect(self._cfg_guncelle)
        self._cfg_timer.start(2000)

        self._ui_kur()

    def _ui_kur(self) -> None:
        self.setMinimumWidth(280)
        self.setMaximumWidth(400)
        self.setStyleSheet(f"background:{C['bg_deep']};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Üst şerit: LED + durum + süre
        header = QWidget()
        header.setFixedHeight(52)
        header.setAutoFillBackground(True)
        header.setStyleSheet(
            f"background:{C['bg_panel']};border-bottom:1px solid {C['border']};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 0, 14, 0)
        hl.setSpacing(10)

        self._sys_led = LedIndicator(size=13)
        self._sys_durum = QLabel("HAZIR")
        self._sys_durum.setStyleSheet(
            f"color:{C['text_pri']};font-size:16px;font-weight:800;"
            f"letter-spacing:1px;background:transparent;")
        self._sure_lbl = QLabel("00:00:00")
        self._sure_lbl.setStyleSheet(
            f"color:{C['text_dim']};font-size:12px;font-family:Consolas;"
            f"background:transparent;")

        hl.addWidget(self._sys_led)
        hl.addWidget(self._sys_durum, 1)
        hl.addWidget(self._sure_lbl)
        outer.addWidget(header)

        # Faz bandı
        faz_w = QWidget()
        faz_w.setAutoFillBackground(True)
        faz_w.setStyleSheet(f"background:{C['bg_panel']};")
        fl = QVBoxLayout(faz_w)
        fl.setContentsMargins(10, 5, 10, 7)
        self._phase_badge = PhaseBadge()
        fl.addWidget(self._phase_badge)
        outer.addWidget(faz_w)

        # Debug butonu
        self._debug_btn = QPushButton("⬡  DEBUG / CONFIG")
        self._debug_btn.setStyleSheet(
            f"QPushButton{{background:{C['bg_panel']};color:{C['text_dim']};"
            f"border:none;border-top:1px solid {C['border']};"
            f"border-bottom:1px solid {C['border']};"
            f"text-align:left;padding:8px 14px;font-size:13px;"
            f"font-weight:600;letter-spacing:1px;}}"
            f"QPushButton:hover{{color:{C['accent']};}}")
        self._debug_btn.clicked.connect(self._debug_ac)
        outer.addWidget(self._debug_btn)

        # Scroll: ana içerik
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent;border:none;")

        body = QWidget()
        body.setAutoFillBackground(True)
        body.setStyleSheet(f"background:{C['bg_deep']};")
        vbox = QVBoxLayout(body)
        vbox.setContentsMargins(10, 14, 10, 14)
        vbox.setSpacing(12)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # KONTROL
        vbox.addWidget(_sec("KONTROL"))
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self._btn_baslat = QPushButton("▶  BAŞLAT")
        self._btn_baslat.setObjectName("btn_start")
        self._btn_baslat.setMinimumHeight(46)
        self._btn_baslat.setStyleSheet(
            f"QPushButton{{background:#063d20;border:1px solid #0a6030;"
            f"color:{C['success']};font-weight:800;font-size:15px;"
            f"letter-spacing:0.8px;border-radius:5px;}}"
            f"QPushButton:hover{{background:#0a5028;border-color:{C['success']};}}"
            f"QPushButton:pressed{{background:#042810;}}"
            f"QPushButton:disabled{{background:{C['bg_card']};"
            f"border-color:{C['border_dim']};color:{C['text_dim']};}}")
        self._btn_baslat.clicked.connect(self._baslat_tiklandi)

        self._btn_durdur = QPushButton("■  DURDUR")
        self._btn_durdur.setObjectName("btn_stop")
        self._btn_durdur.setMinimumHeight(46)
        self._btn_durdur.setEnabled(False)
        self._btn_durdur.setStyleSheet(
            f"QPushButton{{background:#3d0615;border:1px solid #6b0a22;"
            f"color:{C['danger']};font-weight:800;font-size:15px;"
            f"letter-spacing:0.8px;border-radius:5px;}}"
            f"QPushButton:hover{{background:#4d0820;border-color:{C['danger']};}}"
            f"QPushButton:pressed{{background:#2d040f;}}"
            f"QPushButton:disabled{{background:{C['bg_card']};"
            f"border-color:{C['border_dim']};color:{C['text_dim']};}}")
        self._btn_durdur.clicked.connect(self._durdur_tiklandi)

        ctrl_row.addWidget(self._btn_baslat, 1)
        ctrl_row.addWidget(self._btn_durdur, 1)
        vbox.addLayout(ctrl_row)

        vbox.addWidget(_divider())

        # AŞAMA SEÇİCİ
        vbox.addWidget(_sec("AŞAMA"))
        self._asama_widget = _AsamaWidget()
        self._asama_widget.mod_degisti.connect(self._mod_degisti)
        self._asama_widget.onayla_clicked.connect(self.manuel_onayla)
        self._asama_widget.asama_secildi.connect(self._on_widget_asama_sec)
        vbox.addWidget(self._asama_widget)

        vbox.addWidget(_divider())

        hdr_row = QHBoxLayout()
        hdr_row.addWidget(_sec("AKTİF HEDEFLER"))
        hdr_row.addStretch()
        self._threat_badge = ThreatCountBadge()
        hdr_row.addWidget(self._threat_badge)
        vbox.addLayout(hdr_row)

        self._hedef_liste = QListWidget()
        self._hedef_liste.setMinimumHeight(80)
        self._hedef_liste.setMaximumHeight(180)
        self._hedef_liste.setStyleSheet(
            f"QListWidget{{background:{C['bg_input']};border:1px solid {C['border']};"
            f"border-radius:5px;color:{C['text_pri']};font-size:14px;padding:4px;}}"
            f"QListWidget::item{{padding:4px 8px;border-radius:3px;"
            f"border-bottom:1px solid {C['border_dim']};}}"
            f"QListWidget::item:hover{{background:{C['bg_card']};}}"
            f"QListWidget::item:selected{{background:{C['bg_overlay']};"
            f"border-left:2px solid {C['danger']};}}")
        vbox.addWidget(self._hedef_liste)

        vbox.addWidget(_divider())

        vbox.addWidget(_sec("KAMERALAR", accent=C["text_sec"]))
        self._dual_cam = DualCameraStatus()
        cam_card = QWidget()
        cam_card.setAutoFillBackground(True)
        cam_card.setStyleSheet(
            f"background:{C['bg_card']};border:1px solid {C['border']};"
            f"border-radius:6px;")
        cc_lay = QVBoxLayout(cam_card)
        cc_lay.setContentsMargins(10, 8, 10, 8)
        cc_lay.addWidget(self._dual_cam)
        vbox.addWidget(cam_card)

        vbox.addWidget(_divider())

        # TELEMETRİ
        vbox.addWidget(_sec("TELEMETRİ"))
        tel_card = QWidget()
        tel_card.setAutoFillBackground(True)
        tel_card.setStyleSheet(
            f"background:{C['bg_card']};border:1px solid {C['border']};"
            f"border-radius:6px;")
        tl = QVBoxLayout(tel_card)
        tl.setContentsMargins(10, 8, 10, 8)
        tl.setSpacing(3)

        # Sistem satırları
        self._tel_asama = MiniTelRow("◈", "Aktif Aşama", "1")
        self._tel_mod = MiniTelRow("⬡", "Ateş Modu", "OTONOM")
        self._tel_hedef = MiniTelRow("⊕", "Hedef Sayısı", "—",
                                     value_color=C["danger"])
        self._tel_imha = MiniTelRow("⦻", "Toplam İmha", "0",
                                     value_color=C["success"])
        self._tel_suru = MiniTelRow("⋮", "Sürü Boyutu", "—")
        self._tel_lidar = MiniTelRow("◯", "LiDAR", "— m",
                                     value_color=C["warning"])

        # Divider
        _div1 = QFrame()
        _div1.setFrameShape(QFrame.Shape.HLine)
        _div1.setStyleSheet(f"color:{C['border']};background:{C['border']};max-height:1px;")

        # CAM A
        _cam_a_lbl = QLabel("CAM A")
        _cam_a_lbl.setStyleSheet(
            f"color:{C['accent']};font-size:9px;font-weight:800;"
            f"letter-spacing:2px;background:transparent;"
            f"border-left:2px solid {C['accent']};padding-left:6px;margin-top:4px;")
        self._tel_a_fps = MiniTelRow("⏱", "FPS", "—", value_color=C["accent"])
        self._tel_a_det = MiniTelRow("⊡", "Tespit", "0", value_color=C["accent"])
        self._tel_a_mdl = MiniTelRow("◧", "Model", "—")

        # CAM B
        _cam_b_lbl = QLabel("CAM B")
        _cam_b_lbl.setStyleSheet(
            f"color:{C['warning']};font-size:9px;font-weight:800;"
            f"letter-spacing:2px;background:transparent;"
            f"border-left:2px solid {C['warning']};padding-left:6px;margin-top:4px;")
        self._tel_b_fps = MiniTelRow("⏱", "FPS", "—", value_color=C["warning"])
        self._tel_b_det = MiniTelRow("⊡", "Tespit", "0", value_color=C["warning"])
        self._tel_b_mdl = MiniTelRow("◧", "Model", "—")

        # Assemble
        for w in (self._tel_asama, self._tel_mod, self._tel_hedef,
                  self._tel_imha, self._tel_suru, self._tel_lidar):
            tl.addWidget(w)
        tl.addWidget(_div1)
        tl.addWidget(_cam_a_lbl)
        for w in (self._tel_a_fps, self._tel_a_det, self._tel_a_mdl):
            tl.addWidget(w)
        tl.addWidget(_cam_b_lbl)
        for w in (self._tel_b_fps, self._tel_b_det, self._tel_b_mdl):
            tl.addWidget(w)

        vbox.addWidget(tel_card)
        vbox.addStretch()

        # Telemetri yenileme zamanlayıcı (1 sn)
        self._tel_refresh = QTimer(self)
        self._tel_refresh.timeout.connect(self._tel_guncelle)
        self._tel_refresh.start(1000)

    def _debug_ac(self) -> None:
        if self._debug_dialog is None:
            self._debug_dialog = DebugDialog(self.window())
            self._debug_dialog._kaynak_fn = self._debug_veri_uret
        if self._debug_dialog.isVisible():
            self._debug_dialog.hide()
        else:
            self._debug_dialog.show()
            self._debug_dialog.raise_()
            self._debug_dialog.activateWindow()

    def _debug_veri_uret(self) -> str:
        import math
        lines = []
        try:
            # KAMERA DURUMU
            lines.append("══ KAMERA DURUMU ══════════════════════════")
            for i, km in enumerate(config.KAMERALAR):
                lbl = "A" if i == 0 else "B"
                etkin = config.KAMERA_AYARLAR[i].get("ETKIN", False)
                yol = km.get("model", config.MODEL_NESNE_YOLU)
                ok = "✓" if yol and Path(yol).exists() else "✗"
                lines.append(
                    f"  CAM {lbl}  id={km.get('id',i)}"
                    f"  {'[AÇIK]' if etkin else '[KAPALI]'}"
                    f"  {ok} {Path(yol).name if yol else '—'}")
                ayar = config.KAMERA_AYARLAR[i]
                lines.append(
                    f"    IMGSZ={ayar.get('IMGSZ',640)}"
                    f"  güven={ayar.get('GUVEN_ESIGI',0.25):.2f}"
                    f"  tracker={'Açık' if ayar.get('TRACKER') else 'Kapalı'}")

            # NİŞANGAH KALİBRASYONU
            lines.append("══ NİŞANGAH KALİBRASYONU ══════════════════")
            nis_list = getattr(config, "NISANGAH_AYAR", [{}, {}])
            cam_lbls = ["CAM A", "CAM B"]
            for ni, na in enumerate(nis_list[:len(config.KAMERALAR)]):
                try:
                    dx = na.get("LAZER_DX_CM", 0.0)
                    dy = na.get("LAZER_DY_CM", 0.0)
                    fov_h = na.get("FOV_YATAY_DEG", 62.0)
                    fov_v = na.get("FOV_DIKEY_DEG", 47.0)
                    w = na.get("COZUNURLUK_W", 1280)
                    h = na.get("COZUNURLUK_H", 720)
                    dist = max(na.get("HEDEF_MESAFE_M", 10.0), 0.01)
                    man_x = na.get("MANUEL_OFSET_X", 0)
                    man_y = na.get("MANUEL_OFSET_Y", 0)
                    foc_x = (w / 2) / math.tan(math.radians(fov_h / 2))
                    foc_y = (h / 2) / math.tan(math.radians(fov_v / 2))
                    par_x = (dx / 100.0) / dist * foc_x
                    par_y = (dy / 100.0) / dist * foc_y
                    tot_x = par_x + man_x
                    tot_y = par_y + man_y
                    lines.append(
                        f"  {cam_lbls[ni]}  Δ=({dx:+.1f},{dy:+.1f})cm"
                        f"  FOV={fov_h:.0f}°×{fov_v:.0f}°"
                        f"  @{dist:.0f}m")
                    lines.append(
                        f"    parallax=({par_x:+.1f},{par_y:+.1f})px"
                        f"  manuel=({man_x:+d},{man_y:+d})px"
                        f"  toplam=({tot_x:+.1f},{tot_y:+.1f})px")
                except Exception as _e:
                    lines.append(f"  {cam_lbls[ni]}  [hata: {_e}]")

            # ASAMA CONFIG
            lines.append("══ ASAMA KONFİGÜRASYONU ════════════════════")
            for no in (1, 2, 3):
                cfg = getattr(config, f"ASAMA_{no}", None)
                if cfg is None: continue
                lines.append(
                    f"  Aşama {no}  güven={cfg.get('GUVEN_ESIGI','?')}"
                    f"  mod={cfg.get('ATIS_MODU','?')}"
                    f"  imgsz={cfg.get('IMGSZ','?')}")

            # MODEL SINIFLARI
            lines.append("══ MODEL SINIFLARI ═════════════════════════")
            if self._model_siniflari:
                for j in range(0, len(self._model_siniflari), 6):
                    lines.append("  " + ",  ".join(self._model_siniflari[j:j+6]))
            else:
                lines.append("  (model yüklenmedi ya da sınıf listesi boş)")

            # DONANIM
            don = config.DONANIM
            lines.append("══ DONANIM ═════════════════════════════════")
            lines.append(
                f"  Port={don.get('PORT','?')}  Baud={don.get('BAUD_RATE','?')}"
                f"  Proto={don.get('PROTOKOL','?')}")
            lines.append(
                f"  Kp=({don.get('KP_X',1):.2f},{don.get('KP_Y',1):.2f})"
                f"  DeadZone={don.get('DEAD_ZONE_PIXEL',10)}px"
                f"  MaxStep=({don.get('MAX_STEPS_X',400)},{don.get('MAX_STEPS_Y',400)})")
            lines.append(
                f"  LazerOfset=({don.get('LAZER_OFFSET_X',0)},{don.get('LAZER_OFFSET_Y',0)})px")

            # TELEMETRİ
            lines.append("══ SİSTEM TELEMETRİSİ ══════════════════════")
            lines.append(f"  Aktif aşama  : {self._aktif_asama}")
            lines.append(f"  Ateş modu    : {self._asama_mod.get(self._aktif_asama,'—')}")
            lines.append(f"  Sistem aktif : {self._aktif}")
            if self._lidar_m is not None:
                lines.append(f"  LiDAR        : {self._lidar_m:.2f} m")
            merged_a = self._hedefler.get(0, [])
            merged_b = self._hedefler.get(1, [])
            lines.append(
                f"  Hedef CAM A  : {len(merged_a)}  |  CAM B : {len(merged_b)}")

        except Exception as e:
            lines.append(f"[HATA] {e}")
        return "\n".join(lines)

    def faz_guncelle(self, faz: str) -> None:
        self._phase_badge.set_phase(faz)
        if faz == "MANUEL_ONAY":
            self._asama_widget.set_onay_visible(True)
        else:
            self._asama_widget.set_onay_visible(False)

    def hedef_listesi_guncelle(self, hedefler: list) -> None:
        toplam = len(hedefler)
        dusman = sum(1 for h in hedefler
                     if not (h.get("dost", False) if isinstance(h, dict)
                             else getattr(h, "dost", False)))
        self._tel_hedef.setValue(str(toplam) if toplam else "—")
        self._threat_badge.set_count(dusman)
        self._hedef_liste.clear()

        for i, h in enumerate(hedefler, 1):
            if isinstance(h, dict):
                sinif = h.get("sinif") or h.get("renk", "?")
                balon = h.get("balon_eslesme", False)
                dost = h.get("dost", False)
                guven = h.get("guven", 0.0)
                hid = h.get("id", h.get("track_id", 0))
                uzaklik = h.get("uzaklik_m", None)
                cam_idx = h.get("kamera_idx", None)
            else:
                sinif = getattr(h, "sinif", getattr(h, "renk", "?"))
                balon = getattr(h, "balon_eslesme", False)
                dost = getattr(h, "dost", False)
                guven = getattr(h, "guven", 0.0)
                hid = getattr(h, "id", getattr(h, "track_id", 0))
                uzaklik = getattr(h, "uzaklik_m", None)
                cam_idx = getattr(h, "kamera_idx", None)

            # Kamera kaynağı eki
            if cam_idx == 0:
                cam_tag = "A"
                cam_col = CAM_A_COLOR
            elif cam_idx == 1:
                cam_tag = "B"
                cam_col = CAM_B_COLOR
            else:
                cam_tag = ""
                cam_col = C["text_dim"]

            # Mesafe
            if uzaklik is not None:
                dist_str = f"  {uzaklik:.1f}m"
            elif self._lidar_m is not None and i == 1:
                dist_str = f"  {self._lidar_m:.1f}m"
            else:
                dist_str = ""

            # Güven skoru
            guven_str = f" {guven:.0%}" if guven > 0 else ""

            # Etiket
            balon_mark = " ●" if balon else ""
            prefix = f"[{cam_tag}] " if cam_tag else ""
            metin = f"  {i}.  {prefix}{sinif}#{hid:03d}{balon_mark}{guven_str}{dist_str}"

            item = QListWidgetItem(metin)

            if dost:
                item.setForeground(QColor(C["success"]))
            elif balon:
                item.setForeground(QColor(C["danger"]))
            elif i == 1:
                item.setForeground(QColor(C["warning"]))
            else:
                item.setForeground(QColor(C["text_pri"]))

            if cam_idx is not None:
                bg = QColor(int(cam_col[1:3], 16),
                            int(cam_col[3:5], 16),
                            int(cam_col[5:7], 16), 12)
                item.setBackground(bg)

            self._hedef_liste.addItem(item)

    def hedef_listesi_guncelle_a(self, hedefler: list) -> None:
        for h in hedefler:
            if isinstance(h, dict):
                h.setdefault('kamera_idx', 0)
            elif hasattr(h, 'kamera_idx'):
                h.kamera_idx = 0
        self._hedefler[0] = hedefler
        self._render_hedefler()

    def hedef_listesi_guncelle_b(self, hedefler: list) -> None:
        for h in hedefler:
            if isinstance(h, dict):
                h.setdefault('kamera_idx', 1)
            elif hasattr(h, 'kamera_idx'):
                h.kamera_idx = 1
        self._hedefler[1] = hedefler
        self._render_hedefler()

    def _render_hedefler(self) -> None:
        merged = self._hedefler[0] + self._hedefler[1]
        self.hedef_listesi_guncelle(merged)

    def lidar_guncelle(self, uzaklik_m: float) -> None:
        self._lidar_m = uzaklik_m
        self._tel_lidar.setValue(f"{uzaklik_m:.2f} m")

    def kamera_fps_guncelle(self, cam_idx: int, fps: float) -> None:
        self._cam_fps[cam_idx] = fps
        etkin = config.KAMERA_AYARLAR[cam_idx].get("ETKIN", False) if cam_idx < len(config.KAMERA_AYARLAR) else False
        self._dual_cam.set_camera_fps(cam_idx, fps, etkin=etkin)
        fps_str = f"{fps:.1f}" if fps > 0 else "—"
        if cam_idx == 0:
            self._tel_a_fps.setValue(fps_str)
        elif cam_idx == 1:
            self._tel_b_fps.setValue(fps_str)

    def imha_bildir(self, bilgi: dict) -> None:
        try:
            n = int(self._tel_imha.value() or "0") + 1
        except Exception:
            n = 1
        self._tel_imha.setValue(str(n))

    def suru_sayac_guncelle(self, sayi: int) -> None:
        self._tel_suru.setValue(str(sayi))

    def asama_badge_guncelle(self, asama_adi: str) -> None:
        self._phase_badge.set_phase(asama_adi)

    def acil_durdur_tetikle(self) -> None:
        self._aktif = False
        config.ACIL_DURDUR_EVENT.set()
        self._sys_led.set_state("error")
        self._sys_durum.setText("ACİL DURDUR")
        self._btn_baslat.setEnabled(False)
        self._btn_durdur.setEnabled(False)
        self.acil_durdur.emit()

    def model_siniflari_guncelle(self, siniflari: list) -> None:
        self._model_siniflari = list(siniflari)
        if self._debug_dialog and self._debug_dialog.isVisible():
            self._debug_dialog.guncelle()

    def acil_reset(self) -> None:
        config.ACIL_DURDUR_EVENT.clear()
        self._sys_led.set_state("idle")
        self._sys_durum.setText("HAZIR")
        self._btn_baslat.setEnabled(True)
        self._asama_widget.set_onay_visible(False)

    def _asama_sec(self, no: int) -> None:
        self._aktif_asama = no
        self._tel_asama.setValue(str(no))
        self._tel_mod.setValue(self._asama_mod.get(no, "OTONOM"))
        self._asama_widget.set_sistem_aktif(no)
        self.asama_secildi.emit(no)

    def _on_widget_asama_sec(self, no: int) -> None:
        self._aktif_asama = no
        self._tel_asama.setValue(str(no))
        self._tel_mod.setValue(self._asama_mod.get(no, "OTONOM"))
        self.asama_secildi.emit(no)

    def _mod_degisti(self, asama_no: int, mod: str) -> None:
        self._asama_mod[asama_no] = mod
        if asama_no == self._aktif_asama:
            self._tel_mod.setValue(mod)
        self.atis_modu_degisti.emit(asama_no, mod)

    def _cfg_guncelle(self) -> None:
        self._asama_widget.cfg_guncelle()

    def _baslat_tiklandi(self) -> None:
        no = self._aktif_asama
        self._aktif = True
        self._baslangic_t = time.time()
        self._sys_led.set_state("active")
        self._sys_durum.setText("AKTİF")
        self._btn_baslat.setEnabled(False)
        self._btn_durdur.setEnabled(True)
        self.baslat.emit(no)

    def _durdur_tiklandi(self) -> None:
        self._aktif = False
        self._sys_led.set_state("idle")
        self._sys_durum.setText("DURDURULDU")
        self._btn_baslat.setEnabled(True)
        self._btn_durdur.setEnabled(False)
        self.durdur.emit()

    def _sure_guncelle(self) -> None:
        if self._aktif and self._baslangic_t:
            g = int(time.time() - self._baslangic_t)
            self._sure_lbl.setText(
                f"{g//3600:02d}:{(g//60)%60:02d}:{g%60:02d}")

    def _tel_guncelle(self) -> None:
        import os
        # Kameralara özel tespit sayısı
        cnt_a = len(self._hedefler.get(0, []))
        cnt_b = len(self._hedefler.get(1, []))
        self._tel_a_det.setValue(str(cnt_a))
        self._tel_b_det.setValue(str(cnt_b))
        self._tel_hedef.setValue(str(cnt_a + cnt_b) if (cnt_a + cnt_b) else "—")

        # CAM A - model adı
        if len(config.KAMERA_AYARLAR) > 0:
            ayar_a = config.KAMERA_AYARLAR[0]
            etkin_a = ayar_a.get("ETKIN", False)
            mdl_a = ayar_a.get("MODEL_YOLU") or (config.KAMERALAR[0].get("model", "") if config.KAMERALAR else "")
            mdl_a_adı = os.path.splitext(os.path.basename(mdl_a))[0][:12] if mdl_a else "—"
            self._tel_a_mdl.setValue(mdl_a_adı if etkin_a else "KAPALI")
            if not etkin_a:
                self._tel_a_fps.setValue("—")
                self._tel_a_det.setValue("—")

        # CAM B - model adı
        if len(config.KAMERA_AYARLAR) > 1:
            ayar_b = config.KAMERA_AYARLAR[1]
            etkin_b = ayar_b.get("ETKIN", False)
            mdl_b = ayar_b.get("MODEL_YOLU") or (config.KAMERALAR[1].get("model", "") if len(config.KAMERALAR) > 1 else "")
            mdl_b_adı = os.path.splitext(os.path.basename(mdl_b))[0][:12] if mdl_b else "—"
            self._tel_b_mdl.setValue(mdl_b_adı if etkin_b else "KAPALI")
            if not etkin_b:
                self._tel_b_fps.setValue("—")
                self._tel_b_det.setValue("—")

        # Acil durdur durumu - sys LED
        if config.ACIL_DURDUR_EVENT.is_set():
            self._sys_led.set_state("error")
        elif self._aktif:
            self._sys_led.set_state("active")

    def _tel_imha_val(self) -> str:
        return self._tel_imha._val.text()
