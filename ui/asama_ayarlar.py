from __future__ import annotations
import config

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QDoubleSpinBox, QSpinBox, QComboBox,
    QLineEdit, QListWidget, QTextEdit, QTabWidget
)
from .styles import C, CAM_A_COLOR, CAM_B_COLOR


_DIALOG_QSS = f"""
QDialog {{
    background: {C['bg_panel']};
}}

QTabWidget::pane {{
    background: {C['bg_panel']};
    border: 1px solid {C['border']};
    border-radius: 6px;
}}
QTabBar::tab {{
    background: {C['bg_card']};
    border: 1px solid {C['border']};
    border-bottom: none;
    padding: 7px 20px;
    color: {C['text_sec']};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    min-width: 90px;
}}
QTabBar::tab:selected {{
    background: {C['bg_panel']};
    color: {C['accent']};
    border-top: 2px solid {C['accent']};
}}
QTabBar::tab:hover:!selected {{
    color: {C['text_pri']};
    background: {C['bg_overlay']};
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {C['bg_input']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    color: {C['text_mono']};
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 8px;
    min-height: 28px;
    selection-background-color: {C['accent']};
    selection-color: {C['bg_deep']};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {C['border_act']};
    background: #050d1a;
    color: {C['text_pri']};
}}
QComboBox:focus {{ border: 1px solid {C['border_act']}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {C['text_sec']};
    margin-right: 5px;
}}
QComboBox QAbstractItemView {{
    background: {C['bg_panel']};
    border: 1px solid {C['border_act']};
    selection-background-color: {C['bg_overlay']};
    selection-color: {C['accent']};
    padding: 4px;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 12px;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: {C['bg_card']};
    border: none;
    width: 18px;
    border-radius: 2px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {C['bg_overlay']};
}}

QListWidget {{
    background: {C['bg_input']};
    border: 1px solid {C['border']};
    border-radius: 4px;
}}
QListWidget::item {{
    padding: 5px 8px;
    border-bottom: 1px solid {C['border_dim']};
    color: {C['text_pri']};
}}
QListWidget::item:selected {{
    background: {C['bg_overlay']};
    border-left: 2px solid {C['accent']};
    color: {C['accent']};
}}
QListWidget::item:hover {{ background: {C['bg_card']}; }}

QTextEdit {{
    background: {C['bg_deep']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    color: {C['success']};
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 11px;
    padding: 6px;
}}

QScrollBar:vertical {{
    background: {C['bg_deep']};
    width: 6px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C['border']};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {C['border_act']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


class KatlanirBolum(QWidget):

    _ACIK_STIL = (
        f"QPushButton{{background:{C['bg_card']};border:none;"
        f"border-left:3px solid {C['accent']};"
        f"border-bottom:1px solid {C['border']};"
        f"color:{C['accent']};font-size:10px;font-weight:700;"
        f"letter-spacing:1.5px;text-align:left;padding:0 14px;min-height:36px;}}"
        f"QPushButton:hover{{background:{C['bg_overlay']};color:{C['text_pri']};}}"
    )
    _KAPALI_STIL = (
        f"QPushButton{{background:{C['bg_card']};border:none;"
        f"border-left:3px solid {C['border']};"
        f"border-bottom:1px solid {C['border_dim']};"
        f"color:{C['text_sec']};font-size:10px;font-weight:700;"
        f"letter-spacing:1.5px;text-align:left;padding:0 14px;min-height:36px;}}"
        f"QPushButton:hover{{background:{C['bg_overlay']};color:{C['text_pri']};}}"
    )

    def __init__(self, baslik: str, parent=None, acik: bool = True):
        super().__init__(parent)
        self._baslik = baslik
        self._acik = acik

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 6, 0, 0)
        outer.setSpacing(0)

        self._hdr = QPushButton()
        self._hdr.setFixedHeight(36)
        self._hdr.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hdr.clicked.connect(self._togla)
        outer.addWidget(self._hdr)

        self._body = QFrame()
        self._body.setStyleSheet(
            f"QFrame{{background:{C['bg_input']};border:1px solid {C['border']};"
            f"border-top:none;border-bottom-left-radius:6px;"
            f"border-bottom-right-radius:6px;}}")
        self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(14, 12, 14, 14)
        self._body_lay.setSpacing(6)
        self._body.setVisible(acik)
        outer.addWidget(self._body)

        self._refresh_hdr()

    def _refresh_hdr(self) -> None:
        ok = "▼" if self._acik else "▶"
        self._hdr.setText(f"   {ok}   {self._baslik}")
        self._hdr.setStyleSheet(
            self._ACIK_STIL if self._acik else self._KAPALI_STIL)

    def _togla(self) -> None:
        self._acik = not self._acik
        self._body.setVisible(self._acik)
        self._refresh_hdr()

    def ekle(self, widget: QWidget) -> None:
        self._body_lay.addWidget(widget)

    def ekle_layout(self, layout) -> None:
        self._body_lay.addLayout(layout)

    def ic_lay(self) -> QVBoxLayout:
        return self._body_lay


def _float_spin(val: float, lo=0.0, hi=1.0, step=0.01, dec=2) -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(lo, hi); s.setSingleStep(step)
    s.setValue(val); s.setDecimals(dec)
    s.setFixedHeight(30)
    return s


def _int_spin(val: int, lo=0, hi=9999) -> QSpinBox:
    s = QSpinBox()
    s.setRange(lo, hi); s.setValue(val)
    s.setFixedHeight(30)
    return s


def _combo(opts: list[str], cur: str) -> QComboBox:
    c = QComboBox()
    c.addItems(opts); c.setCurrentText(cur)
    c.setFixedHeight(30)
    return c


def _pkart(etiket: str, widget: QWidget, alt: str = "") -> QFrame:
    kart = QFrame()
    kart.setStyleSheet(
        f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};"
        f"border-radius:5px;}}")
    row = QHBoxLayout(kart)
    row.setContentsMargins(12, 0, 10, 0)
    row.setSpacing(10)

    txt_col = QVBoxLayout()
    txt_col.setSpacing(1); txt_col.setContentsMargins(0, 0, 0, 0)
    lbl = QLabel(etiket)
    lbl.setStyleSheet(
        f"color:{C['text_sec']};font-size:11px;font-weight:500;background:transparent;")
    txt_col.addWidget(lbl)
    if alt:
        a = QLabel(alt)
        a.setStyleSheet(
            f"color:{C['text_dim']};font-size:9px;font-style:italic;background:transparent;")
        txt_col.addWidget(a)

    row.addLayout(txt_col, 1)
    widget.setMinimumWidth(110); widget.setMaximumWidth(170)
    row.addWidget(widget)
    kart.setFixedHeight(46 if not alt else 54)
    return kart


def _port_listesi() -> list[str]:
    try:
        import serial.tools.list_ports
        ps = [p.device for p in serial.tools.list_ports.comports()]
        return sorted(ps) if ps else []
    except Exception:
        import sys
        if sys.platform == "win32":
            return [f"COM{i}" for i in range(1, 17)]
        return ([f"/dev/ttyUSB{i}" for i in range(6)] +
                [f"/dev/ttyACM{i}" for i in range(6)])


def _ikon_btn(metin: str, renk: str = None, min_w: int = 70) -> QPushButton:
    b = QPushButton(metin)
    b.setFixedHeight(30)
    b.setMinimumWidth(min_w)
    if renk:
        b.setStyleSheet(
            f"QPushButton{{background:{C['bg_card']};color:{renk};"
            f"border:1px solid {renk};border-radius:4px;"
            f"font-size:11px;font-weight:700;letter-spacing:0.5px;padding:0 10px;}}"
            f"QPushButton:hover{{background:{renk};color:{C['bg_deep']};}}"
            f"QPushButton:pressed{{opacity:0.7;}}")
    return b


class SinifListesi(QWidget):
    def __init__(self, cfg_liste: list, parent=None):
        super().__init__(parent)
        self._cfg = cfg_liste
        self._model_siniflari: list[str] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(4)

        self._liste = QListWidget()
        self._liste.setMaximumHeight(88)
        for item in self._cfg:
            self._liste.addItem(item)
        lay.addWidget(self._liste)

        row = QHBoxLayout(); row.setSpacing(4)
        self._giris = QLineEdit()
        self._giris.setPlaceholderText("sınıf adı…"); self._giris.setFixedHeight(28)
        self._giris.returnPressed.connect(self._ekle)

        be = QPushButton("+"); be.setFixedSize(28, 28)
        be.setStyleSheet(
            f"QPushButton{{background:#063d20;color:{C['success']};"
            f"border:none;border-radius:4px;font-size:15px;font-weight:800;}}"
            f"QPushButton:hover{{background:#0a5028;}}")
        be.clicked.connect(self._ekle)

        bs = QPushButton("−"); bs.setFixedSize(28, 28)
        bs.setStyleSheet(
            f"QPushButton{{background:#3d0615;color:{C['danger']};"
            f"border:none;border-radius:4px;font-size:15px;font-weight:800;}}"
            f"QPushButton:hover{{background:#4d0820;}}")
        bs.clicked.connect(self._sil)

        row.addWidget(self._giris, 1); row.addWidget(be); row.addWidget(bs)
        lay.addLayout(row)

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(
            f"color:{C['text_dim']};font-size:10px;font-style:italic;background:transparent;")
        self._hint.setVisible(False)
        lay.addWidget(self._hint)

    def model_siniflari_guncelle(self, sl: list[str]) -> None:
        self._model_siniflari = sl; self._hint_guncelle()

    def _hint_guncelle(self) -> None:
        pasif = [s for s in self._model_siniflari if s not in set(self._cfg)]
        self._hint.setText("Modelde var, filtrede yok: " + ", ".join(pasif) if pasif else "")
        self._hint.setVisible(bool(pasif))

    def _ekle(self) -> None:
        t = self._giris.text().strip()
        if t and t not in self._cfg:
            self._cfg.append(t); self._liste.addItem(t); self._hint_guncelle()
        self._giris.clear()

    def _sil(self) -> None:
        r = self._liste.currentRow()
        if r < 0: return
        item = self._liste.takeItem(r)
        if item and item.text() in self._cfg:
            self._cfg.remove(item.text()); self._hint_guncelle()


class AsamaAyarlarPanel(QDialog):

    def __init__(self, ana: QWidget):
        super().__init__(ana)
        self.setWindowTitle("Aşama Ayarları")
        self.setWindowFlags(Qt.WindowType.Tool |
                            Qt.WindowType.WindowCloseButtonHint |
                            Qt.WindowType.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.resize(520, 620)
        self.setStyleSheet(_DIALOG_QSS)
        # ÖNCE init, SONRA tab oluşturma
        self._sinif_listeleri: list[SinifListesi] = []

        self._tabs = QTabWidget(self)
        self._tabs.setDocumentMode(True)
        self._tabs.addTab(self._asama1_tab(), "  AŞAMA 1  ")
        self._tabs.addTab(self._asama2_tab(), "  AŞAMA 2  ")
        self._tabs.addTab(self._asama3_tab(), "  AŞAMA 3  ")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._tabs)

    @staticmethod
    def _scroll_w() -> tuple[QWidget, QVBoxLayout]:
        w = QWidget(); w.setStyleSheet(f"background:{C['bg_panel']};")
        sa = QScrollArea(w); sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.Shape.NoFrame)
        sa.setStyleSheet(f"background:{C['bg_panel']};border:none;")
        body = QWidget(); body.setStyleSheet(f"background:{C['bg_panel']};")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(16, 14, 16, 16); lay.setSpacing(2)
        sa.setWidget(body)
        ow = QVBoxLayout(w); ow.setContentsMargins(0, 0, 0, 0); ow.addWidget(sa)
        return w, lay

    # Aşama 1
    def _asama1_tab(self) -> QWidget:
        w, lay = self._scroll_w()
        cfg = config.ASAMA_1

        b = KatlanirBolum("EŞİKLER  &  ZAMANLAMA")
        s = _float_spin(cfg.get("GUVEN_ESIGI", 0.55))
        s.valueChanged.connect(lambda v: cfg.__setitem__("GUVEN_ESIGI", v))
        b.ekle(_pkart("Güven Eşiği", s, "YOLO detection confidence"))

        dz = _int_spin(cfg.get("DEAD_ZONE_PIXEL", 8), 0, 100)
        dz.valueChanged.connect(lambda v: cfg.__setitem__("DEAD_ZONE_PIXEL", v))
        b.ekle(_pkart("Dead Zone (px)", dz, "Gimbal hareketsizlik bölgesi"))

        nms = _float_spin(cfg.get("NMS_ESIGI", 0.45))
        nms.valueChanged.connect(lambda v: cfg.__setitem__("NMS_ESIGI", v))
        b.ekle(_pkart("NMS Eşiği", nms))

        ai = _float_spin(cfg.get("ATIS_ARALIK", 1.5), 0.2, 10.0, 0.1)
        ai.valueChanged.connect(lambda v: cfg.__setitem__("ATIS_ARALIK", v))
        b.ekle(_pkart("Ateş Aralığı (sn)", ai, "Tekrar ateş minimum bekleme"))

        mo = _float_spin(cfg.get("MANUEL_ONAY_TIMEOUT", 5.0), 1.0, 60.0, 1.0)
        mo.valueChanged.connect(lambda v: cfg.__setitem__("MANUEL_ONAY_TIMEOUT", v))
        b.ekle(_pkart("Manuel Onay Timeout (sn)", mo))
        lay.addWidget(b)

        # Genel hedef sınıfları (her iki kamera için ortak nesne filtresi)
        b_genel = KatlanirBolum("GENEL  HEDEF  SINIFLARI")
        genel_lbl = QLabel("  HEDEF SINIFLARI  [Her İki Kamera]")
        genel_lbl.setStyleSheet(
            f"color:{C['text_sec']};font-size:10px;font-weight:600;"
            f"letter-spacing:1px;background:transparent;padding-top:6px;")
        b_genel.ekle(genel_lbl)
        genel_lst = SinifListesi(cfg.setdefault("NESNE_SINIFLARI", []))
        b_genel.ekle(genel_lst)
        self._sinif_listeleri.append(genel_lst)
        lay.addWidget(b_genel)

        # Faz bazlı model yolu override (dost/imha Ayarlar panelindedir)
        self._kamera_model_bolum(lay, cfg, "KAMERA A", "KAMERA_A_MODEL", 0, C["accent"])
        self._kamera_model_bolum(lay, cfg, "KAMERA B", "KAMERA_B_MODEL", 1, C["warning"])

        lay.addStretch()
        return w

    # Aşama 2
    def _asama2_tab(self) -> QWidget:
        w, lay = self._scroll_w()
        cfg = config.ASAMA_2

        b = KatlanirBolum("EŞİKLER  &  SÜRÜ")
        for etiket, key, lo, hi, step, dec, alt in [
            ("Güven Eşiği", "GUVEN_ESIGI", 0.0, 1.0, 0.01, 2, ""),
            ("Uzlaşma Eşiği", "UZLASMA_ESIGI", 0.0, 1.0, 0.01, 2, "Kilitleme güven eşiği"),
            ("NMS Eşiği", "NMS_ESIGI", 0.0, 1.0, 0.01, 2, ""),
            ("Manuel Onay Timeout (sn)","MANUEL_ONAY_TIMEOUT", 1.0, 60., 1.0, 1, ""),
        ]:
            s = _float_spin(cfg.get(key, 0.5), lo, hi, step, dec)
            s.valueChanged.connect(lambda v, k=key: cfg.__setitem__(k, v))
            b.ekle(_pkart(etiket, s, alt))

        for etiket, key, lo, hi, alt in [
            ("Uzlaşma (kare)", "UZLASMA_GEREK", 1, 20, "Kilitleme için min kare"),
            ("Kayıp Kare Limiti","KAYIP_KARE_LIMIT", 1, 50, ""),
            ("Max Sürü Boyutu", "MAX_SURU_BOYUTU", 1, 100, ""),
        ]:
            s = _int_spin(cfg.get(key, 5), lo, hi)
            s.valueChanged.connect(lambda v, k=key: cfg.__setitem__(k, v))
            b.ekle(_pkart(etiket, s, alt))
        lay.addWidget(b)

        b2 = KatlanirBolum("TRACKER  AYARLARI")
        alg = _combo(["botsort", "bytetrack"], cfg.get("TRACKER_ALGORITMA", "botsort"))
        alg.currentTextChanged.connect(lambda v: cfg.__setitem__("TRACKER_ALGORITMA", v))
        b2.ekle(_pkart("Tracker Algoritması", alg))
        mh = _int_spin(cfg.get("TRACKER_MIN_HITS", 3), 1, 20)
        mh.valueChanged.connect(lambda v: cfg.__setitem__("TRACKER_MIN_HITS", v))
        b2.ekle(_pkart("Min Hits", mh, "Takip doğrulama eşiği"))
        lay.addWidget(b2)

        b_genel2 = KatlanirBolum("GENEL  HEDEF  SINIFLARI")
        genel_lbl2 = QLabel("  HEDEF SINIFLARI  [Her İki Kamera]")
        genel_lbl2.setStyleSheet(
            f"color:{C['text_sec']};font-size:10px;font-weight:600;"
            f"letter-spacing:1px;background:transparent;padding-top:6px;")
        b_genel2.ekle(genel_lbl2)
        genel_lst2 = SinifListesi(cfg.setdefault("NESNE_SINIFLARI", []))
        b_genel2.ekle(genel_lst2)
        self._sinif_listeleri.append(genel_lst2)
        lay.addWidget(b_genel2)

        self._kamera_model_bolum(lay, cfg, "KAMERA A", "KAMERA_A_MODEL", 0, C["accent"])
        self._kamera_model_bolum(lay, cfg, "KAMERA B", "KAMERA_B_MODEL", 1, C["warning"])

        lay.addStretch()
        return w

    # Aşama 3
    def _asama3_tab(self) -> QWidget:
        w, lay = self._scroll_w()
        cfg = config.ASAMA_3

        b = KatlanirBolum("EŞİKLER  &  HIZLI İMHA")
        for etiket, key, lo, hi, step, dec, alt in [
            ("Güven Eşiği", "GUVEN_ESIGI", 0.0, 1.0, 0.01, 2, ""),
            ("Uzlaşma Eşiği", "UZLASMA_ESIGI", 0.0, 1.0, 0.01, 2, "Kilitleme güven eşiği"),
            ("NMS Eşiği", "NMS_ESIGI", 0.0, 1.0, 0.01, 2, ""),
            ("Manuel Onay Timeout (sn)","MANUEL_ONAY_TIMEOUT", 1.0, 60., 1.0, 1, ""),
        ]:
            s = _float_spin(cfg.get(key, 0.5), lo, hi, step, dec)
            s.valueChanged.connect(lambda v, k=key: cfg.__setitem__(k, v))
            b.ekle(_pkart(etiket, s, alt))

        for etiket, key, lo, hi, alt in [
            ("Dead Zone (px)", "DEAD_ZONE_PIXEL", 0, 100, "Gimbal hareketsizlik bölgesi"),
            ("Uzlaşma (kare)", "UZLASMA_GEREK", 1, 20, "Kilitleme için min kare"),
            ("Kayıp Kare Limiti", "KAYIP_KARE_LIMIT", 1, 50, ""),
            ("Max Sürü Boyutu", "MAX_SURU_BOYUTU", 1, 100, ""),
        ]:
            s = _int_spin(cfg.get(key, 5), lo, hi)
            s.valueChanged.connect(lambda v, k=key: cfg.__setitem__(k, v))
            b.ekle(_pkart(etiket, s, alt))
        lay.addWidget(b)

        b2 = KatlanirBolum("TRACKER  AYARLARI")
        alg = _combo(["botsort", "bytetrack"], cfg.get("TRACKER_ALGORITMA", "botsort"))
        alg.currentTextChanged.connect(lambda v: cfg.__setitem__("TRACKER_ALGORITMA", v))
        b2.ekle(_pkart("Tracker Algoritması", alg))
        mh = _int_spin(cfg.get("TRACKER_MIN_HITS", 3), 1, 20)
        mh.valueChanged.connect(lambda v: cfg.__setitem__("TRACKER_MIN_HITS", v))
        b2.ekle(_pkart("Min Hits", mh, "Takip doğrulama eşiği"))
        lay.addWidget(b2)

        b_genel3 = KatlanirBolum("GENEL  HEDEF  SINIFLARI")
        genel_lbl3 = QLabel("  HEDEF SINIFLARI  [Her İki Kamera]")
        genel_lbl3.setStyleSheet(
            f"color:{C['text_sec']};font-size:10px;font-weight:600;"
            f"letter-spacing:1px;background:transparent;padding-top:6px;")
        b_genel3.ekle(genel_lbl3)
        genel_lst3 = SinifListesi(cfg.setdefault("NESNE_SINIFLARI", []))
        b_genel3.ekle(genel_lst3)
        self._sinif_listeleri.append(genel_lst3)
        lay.addWidget(b_genel3)

        self._kamera_model_bolum(lay, cfg, "KAMERA A", "KAMERA_A_MODEL", 0, C["accent"])
        self._kamera_model_bolum(lay, cfg, "KAMERA B", "KAMERA_B_MODEL", 1, C["warning"])

        lay.addStretch()
        return w

    def _bolum_listeler(self, bolum: KatlanirBolum,
                        cfg: dict, prefix: str) -> None:
        pass

    def _kamera_model_bolum(self, lay, cfg: dict, cam_lbl: str,
                            model_key: str, cam_idx: int, accent_renk: str) -> None:
        global_isim = (config.KAMERALAR[cam_idx]["isim"].upper()
                       if cam_idx < len(config.KAMERALAR) else cam_lbl)
        model_global = (config.KAMERALAR[cam_idx].get("model", "")
                        if cam_idx < len(config.KAMERALAR) else "")

        b = KatlanirBolum(f"{cam_lbl}  ·  {global_isim}  —  Model Override", acik=False)

        model_edit = QLineEdit(cfg.get(model_key, "") or model_global)
        model_edit.setPlaceholderText(
            f"Boş = global ({model_global[-30:] if model_global else 'yok'})")
        model_edit.textChanged.connect(lambda v, k=model_key: cfg.__setitem__(k, v))
        mkart = QFrame()
        mkart.setStyleSheet(
            f"QFrame{{background:{C['bg_card']};border:1px solid {accent_renk}22;"
            f"border-left:3px solid {accent_renk};border-radius:5px;}}")
        mk_lay = QHBoxLayout(mkart)
        mk_lay.setContentsMargins(12, 4, 10, 4); mk_lay.setSpacing(10)
        ml = QLabel("Model Yolu (faz override)")
        ml.setStyleSheet(
            f"color:{C['text_sec']};font-size:11px;background:transparent;")
        mk_lay.addWidget(ml)
        mk_lay.addWidget(model_edit, 1)
        mkart.setFixedHeight(46)
        b.ekle(mkart)
        lay.addWidget(b)

    def _kamera_bolum(self, lay, cfg: dict, cam_lbl: str,
                      model_key: str, dost_key: str, imha_key: str,
                      cam_idx: int, accent_renk: str) -> None:
        global_isim = (config.KAMERALAR[cam_idx]["isim"].upper()
                       if cam_idx < len(config.KAMERALAR) else cam_lbl)
        model_global = (config.KAMERALAR[cam_idx].get("model", "")
                        if cam_idx < len(config.KAMERALAR) else "")

        b = KatlanirBolum(f"{cam_lbl}  ·  {global_isim}", acik=(cam_idx == 0))

        # Model yolu override (bu faz için)
        model_edit = QLineEdit(cfg.get(model_key, "") or model_global)
        model_edit.setPlaceholderText(f"Boş = global ({model_global[-30:] if model_global else 'yok'})")
        model_edit.textChanged.connect(lambda v, k=model_key: cfg.__setitem__(k, v))
        mkart = QFrame()
        mkart.setStyleSheet(
            f"QFrame{{background:{C['bg_card']};border:1px solid {accent_renk}22;"
            f"border-left:3px solid {accent_renk};border-radius:5px;}}")
        mk_lay = QHBoxLayout(mkart)
        mk_lay.setContentsMargins(12, 4, 10, 4); mk_lay.setSpacing(10)
        ml = QLabel("Model Yolu (faz override)")
        ml.setStyleSheet(
            f"color:{C['text_sec']};font-size:11px;background:transparent;")
        mk_lay.addWidget(ml)
        mk_lay.addWidget(model_edit, 1)
        mkart.setFixedHeight(46)
        b.ekle(mkart)

        # Dost sınıfları
        dost_lbl = QLabel(f"  DOST SINIFLARI  [{cam_lbl}]")
        dost_lbl.setStyleSheet(
            f"color:{C['success']};font-size:10px;font-weight:600;"
            f"letter-spacing:1px;background:transparent;padding-top:6px;")
        b.ekle(dost_lbl)
        dost_lst = SinifListesi(cfg.setdefault(dost_key, []))
        b.ekle(dost_lst)
        self._sinif_listeleri.append(dost_lst)

        # İmha öncelik sırası
        imha_lbl = QLabel(f"  İMHA ÖNCELİK SIRASI  [{cam_lbl}]")
        imha_lbl.setStyleSheet(
            f"color:{C['danger']};font-size:10px;font-weight:600;"
            f"letter-spacing:1px;background:transparent;padding-top:6px;")
        b.ekle(imha_lbl)
        imha_lst = SinifListesi(cfg.setdefault(imha_key, []))
        b.ekle(imha_lst)
        self._sinif_listeleri.append(imha_lst)

        lay.addWidget(b)

    # Public
    def toggle(self, no: int = 1) -> None:
        if self.isVisible() and getattr(self, "_aktif_no", None) == no:
            self.hide(); return
        self._aktif_no = no
        self._tabs.setCurrentIndex(max(0, no - 1))
        self.show(); self.raise_()

    def model_siniflari_guncelle(self, sl: list[str]) -> None:
        for lst in self._sinif_listeleri:
            lst.model_siniflari_guncelle(sl)


class MotorAyarlariPanel(QDialog):
    tus_degisti = pyqtSignal(str, str)  # (config_key, yeni_deger) - kısayol güncelleme


    def __init__(self, ana: QWidget):
        super().__init__(ana)
        self.setWindowTitle("AYARLAR — Donanım & Kamera Kalibrasyonu")
        self.setWindowFlags(Qt.WindowType.Tool |
                            Qt.WindowType.WindowCloseButtonHint |
                            Qt.WindowType.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.resize(560, 720)
        self.setStyleSheet(_DIALOG_QSS)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background:{C['bg_panel']};border:none;")
        body = QWidget(); body.setStyleSheet(f"background:{C['bg_panel']};")
        self._lay = QVBoxLayout(body)
        self._lay.setContentsMargins(16, 14, 16, 20)
        self._lay.setSpacing(2)
        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._sinif_listeleri: list[SinifListesi] = []
        # Per-camera unclassified label + list references for dynamic update
        self._uncls_lbls: dict[int, QLabel] = {}
        self._cam_sinif_listeleri: dict[int, dict] = {i: {} for i in range(4)}
        self._cam_model_siniflari: dict[int, list] = {}
        self._kur()

        # Bağlantı durumu timer'ı
        self._durum_timer = QTimer(self)
        self._durum_timer.timeout.connect(self._durum_guncelle)
        self._durum_timer.start(1000)

    # UI inşa
    def _kur(self) -> None:
        lay = self._lay
        don = config.DONANIM

        # STM32 BAĞLANTI
        b_bag = KatlanirBolum("STM32  BAĞLANTI", acik=True)

        # Bağlantı durumu LED
        self._durum_lbl = QLabel("◉  DURUM BILINMIYOR")
        self._durum_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._durum_lbl.setFixedHeight(34)
        self._durum_lbl.setStyleSheet(
            f"background:{C['bg_card']};border:1px solid {C['border']};"
            f"border-radius:5px;font-size:11px;font-weight:700;"
            f"letter-spacing:0.8px;color:{C['text_dim']};")
        b_bag.ekle(self._durum_lbl)

        # Port satırı - combo + yenile butonu
        portlar = _port_listesi()
        mevcut = don.get("PORT", "COM8")
        self._port_combo = _combo(portlar if portlar else [mevcut], mevcut)
        self._port_combo.setEditable(True)
        self._port_combo.setMinimumWidth(130); self._port_combo.setMaximumWidth(999)
        self._port_combo.currentTextChanged.connect(
            lambda v: don.__setitem__("PORT", v))

        yenile_btn = _ikon_btn("↻", C['accent'], 32)
        yenile_btn.setFixedWidth(34)
        yenile_btn.setToolTip("Portları yenile")
        yenile_btn.clicked.connect(self._portlari_yenile)

        port_row = QFrame()
        port_row.setStyleSheet(
            f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};"
            f"border-radius:5px;}}")
        pr_lay = QHBoxLayout(port_row)
        pr_lay.setContentsMargins(12, 0, 10, 0); pr_lay.setSpacing(8)
        lbl_p = QLabel("Seri Port")
        lbl_p.setStyleSheet(
            f"color:{C['text_sec']};font-size:11px;background:transparent;")
        pr_lay.addWidget(lbl_p)
        pr_lay.addWidget(self._port_combo, 1)
        pr_lay.addWidget(yenile_btn)
        port_row.setFixedHeight(46)
        b_bag.ekle(port_row)

        baud_combo = _combo(
            ["9600","19200","38400","57600","115200","230400","460800"],
            str(don.get("BAUD_RATE", 115200)))
        baud_combo.currentTextChanged.connect(
            lambda v: don.__setitem__("BAUD_RATE", int(v)))
        b_bag.ekle(_pkart("Baud Rate", baud_combo))

        proto_combo = _combo(["stm32", "generic"], don.get("PROTOKOL", "stm32"))
        proto_combo.currentTextChanged.connect(
            lambda v: don.__setitem__("PROTOKOL", v))
        b_bag.ekle(_pkart("Protokol", proto_combo, "stm32=!X Y* / generic=G:pan:tilt"))

        fmt_combo = _combo(["stm32_xy", "generic"],
                           don.get("HEDEF_FORMATI", "stm32_xy"))
        fmt_combo.currentTextChanged.connect(
            lambda v: don.__setitem__("HEDEF_FORMATI", v))
        b_bag.ekle(_pkart("Hedef Formatı", fmt_combo, "Konum komutu formatı"))

        # BAĞLAN / KES + PING butonları
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)

        self._baglan_btn = QPushButton("▶  BAĞLAN")
        self._baglan_btn.setFixedHeight(36)
        self._baglan_btn.setStyleSheet(
            f"QPushButton{{background:#063d20;color:{C['success']};"
            f"border:1px solid #0a6030;border-radius:5px;"
            f"font-size:12px;font-weight:800;letter-spacing:1px;}}"
            f"QPushButton:hover{{background:#0a5028;border-color:{C['success']};}}"
            f"QPushButton:pressed{{background:#042810;}}")
        self._baglan_btn.clicked.connect(self._baglan_toggle)

        ping_btn = QPushButton("◈  PING")
        ping_btn.setFixedHeight(36)
        ping_btn.setStyleSheet(
            f"QPushButton{{background:{C['bg_card']};color:{C['info']};"
            f"border:1px solid {C['info']};border-radius:5px;"
            f"font-size:12px;font-weight:700;letter-spacing:0.8px;}}"
            f"QPushButton:hover{{background:{C['info']};color:{C['bg_deep']};}}"
            f"QPushButton:pressed{{opacity:0.7;}}")
        ping_btn.clicked.connect(self._ping_test)

        btn_row.addWidget(self._baglan_btn, 2)
        btn_row.addWidget(ping_btn, 1)
        b_bag.ekle_layout(btn_row)

        lay.addWidget(b_bag)

        # GİMBAL / HEDEF TAKİP AYARLARI
        b_gim = KatlanirBolum("GİMBAL  /  HEDEF  TAKİP  AYARLARI", acik=True)

        # Canlı formül önizleme etiketi - "Hata 100px -> adım: X"
        self._gimbal_onizleme = QLabel("")
        self._gimbal_onizleme.setWordWrap(True)
        self._gimbal_onizleme.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gimbal_onizleme.setStyleSheet(
            f"background:{C['bg_deep']};border:1px solid {C['border']};"
            f"border-radius:4px;color:{C['accent']};font-family:Consolas;"
            f"font-size:11px;padding:6px;")
        b_gim.ekle(self._gimbal_onizleme)

        def _gimbal_onizleme_guncelle(_=None):
            kp_ = don.get("KP_X", 1.0)
            dz_ = don.get("DEAD_ZONE_PIXEL", 10)
            mx_ = don.get("MAX_STEPS_X", 400)
            # Formül: adim = clamp(round((hata - dead_zone) * kp), -max, max)
            def _adim(hata):
                if abs(hata) <= dz_: return 0
                sign = 1 if hata > 0 else -1
                # Karesel ölçekleme - motor.py._adim_hesapla ile eş
                return max(-mx_, min(mx_, int((hata ** 2) * kp_ / 100 * sign)))
            vals = [10, 50, 100, 200]
            preview = "  |  ".join(
                f"{v}px→{_adim(v)}" for v in vals
            )
            self._gimbal_onizleme.setText(
                f"Kp={kp_:.2f}  DZ={dz_}px  Max={mx_}\n"
                f"Hata → Adım:  {preview}")

        # Kp X (hedef yatay hata katsayısı)
        kp_x = _float_spin(don.get("KP_X", 1.0), 0.0, 20.0, 0.1)
        kp_x.valueChanged.connect(lambda v: (
            don.__setitem__("KP_X", v), _gimbal_onizleme_guncelle()))
        b_gim.ekle(_pkart("Kp X  (yatay)", kp_x, "Hata → adım katsayısı (X ekseni)"))

        # Kp Y (hedef dikey hata katsayısı)
        kp_y = _float_spin(don.get("KP_Y", 1.0), 0.0, 20.0, 0.1)
        kp_y.valueChanged.connect(lambda v: (
            don.__setitem__("KP_Y", v), _gimbal_onizleme_guncelle()))
        b_gim.ekle(_pkart("Kp Y  (dikey)", kp_y, "Hata → adım katsayısı (Y ekseni)"))

        dz = _int_spin(don.get("DEAD_ZONE_PIXEL", 10), 0, 200)
        dz.valueChanged.connect(lambda v: (
            don.__setitem__("DEAD_ZONE_PIXEL", v),
            # ASAMA_1 dead zone da senkronize et
            config.ASAMA_1.__setitem__("DEAD_ZONE_PIXEL", v),
            _gimbal_onizleme_guncelle()))
        b_gim.ekle(_pkart("Dead Zone (px)", dz,
                          "Bu pikselden küçük hata = gimbal hareketsiz"))

        mx = _int_spin(don.get("MAX_STEPS_X", 400), 1, 5000)
        mx.valueChanged.connect(lambda v: (
            don.__setitem__("MAX_STEPS_X", v),
            don.__setitem__("MAX_STEPS_Y", v),
            _gimbal_onizleme_guncelle()))
        b_gim.ekle(_pkart("Max Adım (X & Y)", mx,
                          "Tek hamlede gönderilebilecek maksimum PWM adımı"))

        lox = _int_spin(don.get("LAZER_OFFSET_X", 0), -500, 500)
        lox.valueChanged.connect(lambda v: don.__setitem__("LAZER_OFFSET_X", v))
        b_gim.ekle(_pkart("Lazer Ofset X (px)", lox, "Kamera-lazer parallax ofseti (X)"))

        loy = _int_spin(don.get("LAZER_OFFSET_Y", 0), -500, 500)
        loy.valueChanged.connect(lambda v: don.__setitem__("LAZER_OFFSET_Y", v))
        b_gim.ekle(_pkart("Lazer Ofset Y (px)", loy, "Kamera-lazer parallax ofseti (Y)"))

        pan_s = _float_spin(don.get("PAN_OLCEK", 0.1), 0.001, 5.0, 0.01)
        pan_s.valueChanged.connect(lambda v: don.__setitem__("PAN_OLCEK", v))
        b_gim.ekle(_pkart("Pan Ölçek", pan_s, "Generic protokol için"))

        tilt_s = _float_spin(don.get("TILT_OLCEK", 0.1), 0.001, 5.0, 0.01)
        tilt_s.valueChanged.connect(lambda v: don.__setitem__("TILT_OLCEK", v))
        b_gim.ekle(_pkart("Tilt Ölçek", tilt_s, "Generic protokol için"))

        _gimbal_onizleme_guncelle()  # başlangıç önizleme
        lay.addWidget(b_gim)

        # STM32 GİMBAL KOMUT FORMATI
        b_fmt = KatlanirBolum("STM32  GİMBAL  KOMUT  FORMATI", acik=True)

        _fmt_aciklama = QLabel(
            "{x} = X adımı   {y} = Y adımı\n"
            "Örn: !X{{x}}Y{{y}}*  →  !X1600Y-800*\n"
            "Not: !Y formatı (eski) kullanılmaz — doğru: Y")
        _fmt_aciklama.setWordWrap(True)
        _fmt_aciklama.setStyleSheet(
            f"background:{C['bg_deep']};border:1px solid {C['border']};"
            f"border-radius:4px;color:{C['text_dim']};font-family:Consolas;"
            f"font-size:10px;padding:6px;")
        b_fmt.ekle(_fmt_aciklama)

        # Canlı önizleme
        self._fmt_onizleme = QLabel("")
        self._fmt_onizleme.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._fmt_onizleme.setStyleSheet(
            f"background:{C['bg_card']};border:1px solid {C['accent']}33;"
            f"border-left:3px solid {C['accent']};border-radius:4px;"
            f"color:{C['accent']};font-family:Consolas;font-size:12px;"
            f"font-weight:700;padding:6px;")
        b_fmt.ekle(self._fmt_onizleme)

        def _fmt_onizleme_guncelle(_=None):
            fmt = don.get("GIMBAL_FORMAT", "!X{x}Y{y}*")
            try:
                ornek = fmt.format(x=1600, y=-800)
            except Exception as e:
                ornek = f"FORMAT HATASI: {e}"
            self._fmt_onizleme.setText(
                f"Önizleme (x=1600, y=-800):\n{ornek}")

        _fmt_edit = QLineEdit(don.get("GIMBAL_FORMAT", "!X{x}Y{y}*"))
        _fmt_edit.setFixedHeight(30)
        _fmt_edit.setPlaceholderText("!X{x}Y{y}*")
        _fmt_edit.textChanged.connect(lambda v: (
            don.__setitem__("GIMBAL_FORMAT", v), _fmt_onizleme_guncelle()))
        b_fmt.ekle(_pkart("Takip Komut Formatı", _fmt_edit,
                          "Hedef takip sırasında gönderilen komut"))

        _dur_edit = QLineEdit(don.get("GIMBAL_DUR_FORMAT", "!X0Y0*"))
        _dur_edit.setFixedHeight(30)
        _dur_edit.setPlaceholderText("!X0Y0*")
        _dur_edit.textChanged.connect(lambda v: don.__setitem__("GIMBAL_DUR_FORMAT", v))
        b_fmt.ekle(_pkart("Dur Komut Formatı", _dur_edit,
                          "Hedef yokken gönderilen dur komutu"))

        _fmt_onizleme_guncelle()
        lay.addWidget(b_fmt)


        # NİŞANGAH KALİBRASYONU (Kamera başına)
        b_nis = KatlanirBolum("NİŞANGAH  KALİBRASYONU", acik=True)

        _nisangah_header = QLabel(
            "Kamera-lazer parallax ofseti. Formul:\n"
            "piksel = (lazer_cm/100) / mesafe_m x fokal_px\n"
            "fokal_px = (W/2) / tan(FOV_h/2)")
        _nisangah_header.setStyleSheet(
            f"color:{C['text_dim']};font-size:10px;font-family:Consolas;"
            f"background:{C['bg_card']};border:1px solid {C['border']};"
            f"border-radius:4px;padding:6px 10px;")
        _nisangah_header.setWordWrap(True)
        b_nis.ekle(_nisangah_header)

        if not hasattr(config, "NISANGAH_AYAR"):
            config.NISANGAH_AYAR = [{} for _ in config.KAMERALAR]

        _cam_labels = ["CAM  A  (KAMERA 0)", "CAM  B  (KAMERA 1)"]
        _cam_colors = [CAM_A_COLOR, CAM_B_COLOR]
        self._nis_result_lbls: list = []

        for ni, nayar in enumerate(config.NISANGAH_AYAR[:len(config.KAMERALAR)]):
            cam_hdr = QLabel(f"── {_cam_labels[ni]} ──")
            cam_hdr.setStyleSheet(
                f"color:{_cam_colors[ni]};font-size:11px;font-weight:700;"
                f"font-family:Consolas;background:transparent;"
                f"padding-top:6px;")
            b_nis.ekle(cam_hdr)

            dx = _float_spin(nayar.get("LAZER_DX_CM", 0.0), -100.0, 100.0, 0.1)
            dx.valueChanged.connect(lambda v, a=nayar: a.__setitem__("LAZER_DX_CM", v))
            b_nis.ekle(_pkart("Lazer ΔX (cm)", dx, "Lazer→kamera yatay fark (sağ+)"))

            dy = _float_spin(nayar.get("LAZER_DY_CM", 0.0), -100.0, 100.0, 0.1)
            dy.valueChanged.connect(lambda v, a=nayar: a.__setitem__("LAZER_DY_CM", v))
            b_nis.ekle(_pkart("Lazer ΔY (cm)", dy, "Lazer→kamera dikey fark (aşağı+)"))

            fov_h = _float_spin(nayar.get("FOV_YATAY_DEG", 62.0), 1.0, 180.0, 0.5)
            fov_h.valueChanged.connect(lambda v, a=nayar: a.__setitem__("FOV_YATAY_DEG", v))
            b_nis.ekle(_pkart("FOV Yatay (°)", fov_h, "Kamera yatay görüş açısı"))

            fov_v = _float_spin(nayar.get("FOV_DIKEY_DEG", 47.0), 1.0, 180.0, 0.5)
            fov_v.valueChanged.connect(lambda v, a=nayar: a.__setitem__("FOV_DIKEY_DEG", v))
            b_nis.ekle(_pkart("FOV Dikey (°)", fov_v, "Kamera dikey görüş açısı"))

            mesafe = _float_spin(nayar.get("HEDEF_MESAFE_M", 10.0), 0.5, 1000.0, 0.5)
            mesafe.valueChanged.connect(lambda v, a=nayar: a.__setitem__("HEDEF_MESAFE_M", v))
            b_nis.ekle(_pkart("Hedef Mesafe (m)", mesafe, "Parallax hesabı için referans"))

            mx_off = _int_spin(nayar.get("MANUEL_OFSET_X", 0), -500, 500)
            mx_off.valueChanged.connect(lambda v, a=nayar: a.__setitem__("MANUEL_OFSET_X", v))
            b_nis.ekle(_pkart("Manuel Ofset X (px)", mx_off, "İnce ayar piksel ofseti"))

            my_off = _int_spin(nayar.get("MANUEL_OFSET_Y", 0), -500, 500)
            my_off.valueChanged.connect(lambda v, a=nayar: a.__setitem__("MANUEL_OFSET_Y", v))
            b_nis.ekle(_pkart("Manuel Ofset Y (px)", my_off, "İnce ayar piksel ofseti"))

            # Hesaplanan sonuç göstergesi
            result_lbl = QLabel("Hesaplanan: — px, — px")
            result_lbl.setStyleSheet(
                f"color:{_cam_colors[ni]};font-size:11px;font-family:Consolas;"
                f"font-weight:700;background:{C['bg_card']};"
                f"border:1px solid {_cam_colors[ni]}44;border-radius:4px;"
                f"padding:4px 10px;")
            b_nis.ekle(result_lbl)
            self._nis_result_lbls.append((result_lbl, nayar))

            def _update_result(_, _lbl=result_lbl, _a=nayar, _ni=ni):
                import math
                try:
                    dx_cm = _a.get("LAZER_DX_CM", 0.0)
                    dy_cm = _a.get("LAZER_DY_CM", 0.0)
                    fov_h = _a.get("FOV_YATAY_DEG", 62.0)
                    fov_v = _a.get("FOV_DIKEY_DEG", 47.0)
                    w = _a.get("COZUNURLUK_W", 1280)
                    h = _a.get("COZUNURLUK_H", 720)
                    dist = max(_a.get("HEDEF_MESAFE_M", 10.0), 0.01)
                    man_x = _a.get("MANUEL_OFSET_X", 0)
                    man_y = _a.get("MANUEL_OFSET_Y", 0)
                    foc_x = (w / 2) / math.tan(math.radians(fov_h / 2))
                    foc_y = (h / 2) / math.tan(math.radians(fov_v / 2))
                    par_x = (dx_cm / 100.0) / dist * foc_x
                    par_y = (dy_cm / 100.0) / dist * foc_y
                    tot_x = par_x + man_x
                    tot_y = par_y + man_y
                    _lbl.setText(
                        f"Parallax: {par_x:+.1f}px, {par_y:+.1f}px  |  "
                        f"Toplam: {tot_x:+.1f}px, {tot_y:+.1f}px")
                    if _ni == 0:
                        config.DONANIM["LAZER_OFFSET_X"] = int(round(tot_x))
                        config.DONANIM["LAZER_OFFSET_Y"] = int(round(tot_y))
                except Exception as e:
                    _lbl.setText(f"Hata: {e}")

            dx.valueChanged.connect(_update_result)
            dy.valueChanged.connect(_update_result)
            fov_h.valueChanged.connect(_update_result)
            fov_v.valueChanged.connect(_update_result)
            mesafe.valueChanged.connect(_update_result)
            mx_off.valueChanged.connect(_update_result)
            my_off.valueChanged.connect(_update_result)
            _update_result(0)

        lay.addWidget(b_nis)

        # MANUEL KOMUT TERMİNALİ
        b_term = KatlanirBolum("MANUEL  KOMUT  TERMİNALİ", acik=False)

        # Terminal log
        self._terminal = QTextEdit()
        self._terminal.setReadOnly(True)
        self._terminal.setFixedHeight(110)
        self._terminal.setPlaceholderText("Gönderilen / alınan komutlar burada görünür…")
        b_term.ekle(self._terminal)

        # Preset komut butonları
        preset_lbl = QLabel("HAZIR KOMUTLAR")
        preset_lbl.setStyleSheet(
            f"color:{C['text_dim']};font-size:9px;font-weight:700;"
            f"letter-spacing:1.5px;background:transparent;padding-top:4px;")
        b_term.ekle(preset_lbl)

        presets_row1 = QHBoxLayout(); presets_row1.setSpacing(6)
        presets_row2 = QHBoxLayout(); presets_row2.setSpacing(6)

        # (etiket, MOTOR_KONTROL config key, renk, min_genislik)
        _presets1 = [
            ("PING", "PING_KOMUTU", C['info'], 70),
            ("ATEŞ", "ATES_KOMUTU", C['warning'], 70),
            ("ATEŞ DUR", "ATES_DUR_KOMUTU", C['text_sec'],70),
            ("ACİL DUR", "ACIL_DUR_KOMUTU", C['danger'], 70),
        ]
        _presets2 = [
            ("MERKEZ", "MERKEZ_KOMUTU", C['accent'], 60),
            ("SOL", "KOMUT_SOL", C['text_sec'],60),
            ("SAĞ", "KOMUT_SAG", C['text_sec'],60),
            ("YUKARI", "KOMUT_YUKARI", C['text_sec'],60),
            ("AŞAĞI", "KOMUT_ASAGI", C['text_sec'],60),
        ]

        # Butonlar tıklandığında MOTOR_KONTROL'den canlı okur - preset edit senkronizasyonu otomatik
        for metin, cfg_key, renk, mw in _presets1:
            b = _ikon_btn(metin, renk, mw)
            b.clicked.connect(
                lambda _, k=cfg_key, m=metin: self._gonder(
                    config.MOTOR_KONTROL.get(k, ""), m))
            presets_row1.addWidget(b)

        for metin, cfg_key, renk, mw in _presets2:
            b = _ikon_btn(metin, renk, mw)
            b.clicked.connect(
                lambda _, k=cfg_key, m=metin: self._gonder(
                    config.MOTOR_KONTROL.get(k, ""), m))
            presets_row2.addWidget(b)

        b_term.ekle_layout(presets_row1)
        b_term.ekle_layout(presets_row2)

        # Özel komut giriş satırı
        giris_frame = QFrame()
        giris_frame.setStyleSheet(
            f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};"
            f"border-radius:5px;}}")
        gf_lay = QHBoxLayout(giris_frame)
        gf_lay.setContentsMargins(10, 4, 8, 4); gf_lay.setSpacing(8)

        self._komut_giris = QLineEdit()
        self._komut_giris.setPlaceholderText("Özel komut girin… (örn: PING\\n)")
        self._komut_giris.setFixedHeight(30)
        self._komut_giris.returnPressed.connect(self._ozel_komut_gonder)

        gonder_btn = QPushButton("⏎  GÖNDER")
        gonder_btn.setFixedHeight(30)
        gonder_btn.setMinimumWidth(90)
        gonder_btn.setStyleSheet(
            f"QPushButton{{background:{C['bg_overlay']};color:{C['accent']};"
            f"border:1px solid {C['accent']};border-radius:4px;"
            f"font-size:11px;font-weight:700;letter-spacing:0.5px;padding:0 10px;}}"
            f"QPushButton:hover{{background:{C['accent']};color:{C['bg_deep']};}}"
            f"QPushButton:pressed{{background:#007a8f;}}")
        gonder_btn.clicked.connect(self._ozel_komut_gonder)

        gf_lay.addWidget(self._komut_giris, 1)
        gf_lay.addWidget(gonder_btn)
        giris_frame.setFixedHeight(46)
        b_term.ekle(giris_frame)

        lay.addWidget(b_term)

        # KAMERA BAŞINA YOLO
        _flip_map = {-1: "-1 (Yok)", 0: "0 (Dikey)", 1: "1 (Yatay)", 2: "2 (180°)"}

        for i, ayar in enumerate(config.KAMERA_AYARLAR):
            isim = (config.KAMERALAR[i]["isim"]
                    if i < len(config.KAMERALAR) else f"KAMERA {i}")
            b_cam = KatlanirBolum(f"YOLO  —  {isim.upper()}", acik=(i == 0))

            # Model yolu (geniş)
            model_edit = QLineEdit(ayar.get("MODEL_YOLU", ""))
            model_edit.setPlaceholderText("models/nesne.pt")
            model_edit.textChanged.connect(
                lambda v, a=ayar: a.__setitem__("MODEL_YOLU", v))

            mkart = QFrame()
            mkart.setStyleSheet(
                f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};"
                f"border-radius:5px;}}")
            mk_lay = QHBoxLayout(mkart)
            mk_lay.setContentsMargins(12, 4, 10, 4); mk_lay.setSpacing(10)
            ml = QLabel("Model Yolu")
            ml.setStyleSheet(
                f"color:{C['text_sec']};font-size:11px;background:transparent;")
            mk_lay.addWidget(ml)
            mk_lay.addWidget(model_edit, 1)
            mkart.setFixedHeight(46)
            b_cam.ekle(mkart)

            imgsz = _combo(["320","416","512","640","768","1024","1280"],
                           str(ayar.get("IMGSZ", 640)))
            imgsz.currentTextChanged.connect(
                lambda v, a=ayar: a.__setitem__("IMGSZ", int(v)))
            b_cam.ekle(_pkart("IMGSZ", imgsz, "Çıkarım giriş boyutu"))

            gspin = _float_spin(ayar.get("GUVEN_ESIGI", 0.25), 0.0, 1.0, 0.01)
            gspin.valueChanged.connect(
                lambda v, a=ayar: a.__setitem__("GUVEN_ESIGI", v))
            b_cam.ekle(_pkart("Güven Eşiği", gspin))

            _trk_secenekler = ["Kapalı", "BoT-SORT", "ByteTrack"]
            _trk_mevcut = "Kapalı"
            if ayar.get("TRACKER", False):
                _alg = ayar.get("TRACKER_ALGORITMA", "botsort").lower()
                _trk_mevcut = "ByteTrack" if "byte" in _alg else "BoT-SORT"
            trk = _combo(_trk_secenekler, _trk_mevcut)
            def _trk_degisti(v, a=ayar):
                if v == "Kapalı":
                    a["TRACKER"] = False
                elif v == "BoT-SORT":
                    a["TRACKER"] = True
                    a["TRACKER_ALGORITMA"] = "botsort"
                else:  # ByteTrack
                    a["TRACKER"] = True
                    a["TRACKER_ALGORITMA"] = "bytetrack"
            trk.currentTextChanged.connect(_trk_degisti)
            b_cam.ekle(_pkart("Tracker Algoritması", trk, "BoT-SORT=kalıcı iz · ByteTrack=hız"))

            # Tracker ince ayarları
            trk_buf = _int_spin(ayar.get("TRACK_BUFFER", 30), 1, 120)
            trk_buf.valueChanged.connect(lambda v, a=ayar: a.__setitem__("TRACK_BUFFER", v))
            b_cam.ekle(_pkart("Track Buffer (kare)", trk_buf, "Kayıp iz tutma süresi"))

            trk_thr = _float_spin(ayar.get("TRACK_THRESH", 0.5), 0.1, 0.99, 0.01)
            trk_thr.valueChanged.connect(lambda v, a=ayar: a.__setitem__("TRACK_THRESH", v))
            b_cam.ekle(_pkart("Track Eşiği", trk_thr, "İz başlatma güven eşiği"))

            match_thr = _float_spin(ayar.get("MATCH_THRESH", 0.8), 0.1, 0.99, 0.01)
            match_thr.valueChanged.connect(lambda v, a=ayar: a.__setitem__("MATCH_THRESH", v))
            b_cam.ekle(_pkart("Eşleşme Eşiği (IoU)", match_thr, "Tespit↔iz IoU eşleşme"))

            etk = _combo(["Kapalı","Açık"],
                         "Açık" if ayar.get("ETKIN", False) else "Kapalı")
            etk.currentTextChanged.connect(
                lambda v, a=ayar, _i=i: (
                    a.__setitem__("ETKIN", v == "Açık"),
                    config.KAMERALAR[_i].__setitem__("etkin", v == "Açık")))
            b_cam.ekle(_pkart("Kamera Etkin", etk))

            flip_val = (config.KAMERALAR[i].get("flip", -1)
                        if i < len(config.KAMERALAR) else -1)
            flip_c = _combo(list(_flip_map.values()),
                            _flip_map.get(flip_val, "-1 (Yok)"))
            def _flip_cb(v, _i=i):
                val = int(v.split()[0])
                if _i < len(config.KAMERALAR):
                    config.KAMERALAR[_i]["flip"] = val
                    config.UI_AYAR[f"KAMERA_{_i}_FLIP"] = val
            flip_c.currentTextChanged.connect(_flip_cb)
            b_cam.ekle(_pkart("Flip", flip_c, "Görüntü aynalama"))

            # 3-katmanlı sınıf filtresi (KAMERA_AYARLAR'dan)
            [CAM_A_COLOR, CAM_B_COLOR][i] if i < 2 else C["accent"]

            # Sınıflandırılmamış göstergesi (dinamik - model yüklenince güncellenir)
            _uncls_lbl = QLabel("Sınıflandırılmamış: —")
            _uncls_lbl.setWordWrap(True)
            _uncls_lbl.setStyleSheet(
                f"color:{C['text_dim']};font-size:10px;font-family:Consolas;"
                f"background:{C['bg_card']};border:1px solid {C['border']};"
                f"border-radius:4px;padding:4px 8px;")
            b_cam.ekle(_uncls_lbl)
            self._uncls_lbls[i] = _uncls_lbl

            dost_hdr = QLabel(f"  DOST SINIFLARI  [YOLO {i}]  — gösterilir, hedef alınmaz")
            dost_hdr.setStyleSheet(
                f"color:{C['success']};font-size:10px;font-weight:700;"
                f"letter-spacing:1px;background:transparent;padding-top:8px;")
            b_cam.ekle(dost_hdr)
            dost_lst = SinifListesi(ayar.setdefault("DOST_SINIFLAR", []))
            b_cam.ekle(dost_lst)
            self._sinif_listeleri.append(dost_lst)
            self._cam_sinif_listeleri[i]["dost"] = dost_lst

            dusman_hdr = QLabel(f"  DÜŞMAN SINIFLARI  [YOLO {i}]  — hedef alınır")
            dusman_hdr.setStyleSheet(
                f"color:{C['danger']};font-size:10px;font-weight:700;"
                f"letter-spacing:1px;background:transparent;padding-top:6px;")
            b_cam.ekle(dusman_hdr)
            dusman_lst = SinifListesi(ayar.setdefault("DUSMAN_SINIFLAR", []))
            b_cam.ekle(dusman_lst)
            self._sinif_listeleri.append(dusman_lst)
            self._cam_sinif_listeleri[i]["dusman"] = dusman_lst

            tehdit_hdr = QLabel(f"  TEHDİT SIRASI  [YOLO {i}]  — öncelikli önce hedef alınır")
            tehdit_hdr.setStyleSheet(
                f"color:{C['warning']};font-size:10px;font-weight:700;"
                f"letter-spacing:1px;background:transparent;padding-top:6px;")
            b_cam.ekle(tehdit_hdr)
            tehdit_lst = SinifListesi(ayar.setdefault("TEHDIT_SIRASI", []))
            b_cam.ekle(tehdit_lst)
            self._sinif_listeleri.append(tehdit_lst)
            self._cam_sinif_listeleri[i]["tehdit"] = tehdit_lst

            # Motor Komut Filtresi
            motor_hdr = QLabel(f"  MOTOR KOMUT FİLTRESİ  [YOLO {i}]")
            motor_hdr.setStyleSheet(
                f"color:{C['info']};font-size:10px;font-weight:700;"
                f"letter-spacing:1px;background:transparent;padding-top:8px;")
            b_cam.ekle(motor_hdr)

            motor_etkin = _combo(["Açık", "Kapalı"],
                                 "Açık" if ayar.get("MOTOR_KOMUT_ETKIN", True) else "Kapalı")
            motor_etkin.currentTextChanged.connect(
                lambda v, a=ayar: a.__setitem__("MOTOR_KOMUT_ETKIN", v == "Açık"))
            b_cam.ekle(_pkart("Motor Komut Gönderme", motor_etkin,
                              "Bu kamera gimbal komutu gönderebilir mi?"))

            motor_prio = _int_spin(ayar.get("MOTOR_KOMUT_ONCELIK", 0), 0, 10)
            motor_prio.valueChanged.connect(
                lambda v, a=ayar: a.__setitem__("MOTOR_KOMUT_ONCELIK", v))
            b_cam.ekle(_pkart("Motor Önceliği", motor_prio,
                              "0=en yüksek — iki kamera çakışınca hangisi kazanır"))

            motor_guven = _float_spin(ayar.get("MOTOR_KOMUT_MIN_GUVEN", 0.25), 0.0, 1.0, 0.01)
            motor_guven.valueChanged.connect(
                lambda v, a=ayar: a.__setitem__("MOTOR_KOMUT_MIN_GUVEN", v))
            b_cam.ekle(_pkart("Motor Min Güven", motor_guven,
                              "Bu güvenin altındaki hedefler gimbal'ı hareket ettirmez"))

            motor_sinif_hdr = QLabel(f"  MOTOR SINIF FİLTRESİ  [YOLO {i}]  — boş=tüm düşmanlar")
            motor_sinif_hdr.setStyleSheet(
                f"color:{C['info']};font-size:10px;font-weight:600;"
                f"letter-spacing:1px;background:transparent;padding-top:4px;")
            b_cam.ekle(motor_sinif_hdr)
            motor_sinif_lst = SinifListesi(ayar.setdefault("MOTOR_KOMUT_SINIF", []))
            b_cam.ekle(motor_sinif_lst)
            self._sinif_listeleri.append(motor_sinif_lst)
            if i in self._cam_sinif_listeleri:
                self._cam_sinif_listeleri[i]["motor"] = motor_sinif_lst

            lay.addWidget(b_cam)

        # CANLI MOTOR KOMUT LOGU
        b_log = KatlanirBolum("CANLI  MOTOR  KOMUT  LOGU", acik=True)

        self._motor_log_txt = QTextEdit()
        self._motor_log_txt.setReadOnly(True)
        self._motor_log_txt.setFixedHeight(130)
        self._motor_log_txt.setStyleSheet(
            f"QTextEdit{{background:#05090f;color:{C['success']};font-family:Consolas;"
            f"font-size:11px;border:1px solid {C['border']};border-radius:4px;}}")
        self._motor_log_txt.setPlaceholderText("Gönderilen tüm motor komutları burada görünür…")
        b_log.ekle(self._motor_log_txt)

        log_btn_row = QHBoxLayout(); log_btn_row.setSpacing(6)
        log_temizle = _ikon_btn("🗑  TEMİZLE", C['danger'], 90)
        log_temizle.clicked.connect(self._motor_log_temizle)
        log_btn_row.addWidget(log_temizle)
        log_btn_row.addStretch()
        b_log.ekle_layout(log_btn_row)

        lay.addWidget(b_log)

        # Düzenlenebilir Preset Komutlar - tüm MOTOR_KONTROL komutları
        b_preset = KatlanirBolum("DÜZENLENEBİLİR  PRESET  KOMUTLAR", acik=False)

        _pr_baslik = QLabel(
            "Komut metnini değiştirin → HAZIR KOMUTLAR butonları otomatik senkronize olur")
        _pr_baslik.setWordWrap(True)
        _pr_baslik.setStyleSheet(
            f"color:{C['text_dim']};font-size:10px;background:transparent;padding-bottom:4px;")
        b_preset.ekle(_pr_baslik)

        # Gruplar: (grup başlık, [(etiket, MOTOR_KONTROL key, renk)])
        _pr_gruplar = [
            ("ATEŞ / ÖZEL", [
                ("PING", "PING_KOMUTU", C['info']),
                ("ATEŞ", "ATES_KOMUTU", C['warning']),
                ("ATEŞ DUR", "ATES_DUR_KOMUTU", C['text_sec']),
                ("ACİL DUR", "ACIL_DUR_KOMUTU", C['danger']),
            ]),
            ("HAREKET", [
                ("MERKEZ", "MERKEZ_KOMUTU", C['accent']),
                ("SOL", "KOMUT_SOL", C['text_sec']),
                ("SAĞ", "KOMUT_SAG", C['text_sec']),
                ("YUKARI", "KOMUT_YUKARI", C['text_sec']),
                ("AŞAĞI", "KOMUT_ASAGI", C['text_sec']),
                ("DUR", "KOMUT_DUR", C['text_dim']),
            ]),
        ]

        self._preset_edits: list = []
        mcfg = config.MOTOR_KONTROL

        for grp_baslik, satirlar in _pr_gruplar:
            g_hdr = QLabel(grp_baslik)
            g_hdr.setStyleSheet(
                f"color:{C['text_dim']};font-size:9px;font-weight:700;letter-spacing:1.5px;"
                f"background:transparent;padding-top:6px;padding-bottom:2px;")
            b_preset.ekle(g_hdr)

            for metin, cfg_key, renk in satirlar:
                row_f = QFrame()
                row_f.setStyleSheet(
                    f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};"
                    f"border-radius:5px;}}")
                row_l = QHBoxLayout(row_f)
                row_l.setContentsMargins(8, 4, 8, 4); row_l.setSpacing(8)

                lbl = QLabel(metin)
                lbl.setFixedWidth(70)
                lbl.setStyleSheet(
                    f"color:{renk};font-size:11px;font-weight:700;background:transparent;")
                edit = QLineEdit(mcfg.get(cfg_key, ""))
                edit.setFixedHeight(26)
                # textChanged -> config güncelle -> butonlar canlı senkronize
                edit.textChanged.connect(
                    lambda v, k=cfg_key: mcfg.__setitem__(k, v))
                send_btn = _ikon_btn("▶", renk, 30)
                send_btn.setFixedWidth(32)
                send_btn.clicked.connect(lambda _, e=edit: self._preset_gonder(e.text()))
                row_l.addWidget(lbl); row_l.addWidget(edit, 1); row_l.addWidget(send_btn)
                row_f.setFixedHeight(40)
                b_preset.ekle(row_f)
                self._preset_edits.append(edit)

        lay.addWidget(b_preset)

        # Motor log polling timer
        self._log_poll_timer = QTimer(self)
        self._log_poll_timer.timeout.connect(self._motor_log_guncelle)
        self._log_poll_timer.start(250)  # 4 Hz - yeterince hızlı, UI'ı yormaz
        self._log_son_uzunluk = 0

        # TUŞ ATAMALARI
        b_tus = KatlanirBolum("TUŞ  ATAMALARI", acik=False)

        _tus_baslik = QLabel(
            "Klavye kısayollarını değiştirin — tek karakter (a-z 0-9) "
            "veya Qt key ismi (space, escape, f1…f12, ctrl+x, …)")
        _tus_baslik.setWordWrap(True)
        _tus_baslik.setStyleSheet(
            f"color:{C['text_dim']};font-size:10px;background:transparent;"
            f"padding-bottom:4px;")
        b_tus.ekle(_tus_baslik)

        _tus_satirlar = [
            # (etiket, MOTOR_KONTROL key, renk)
            ("Sola Hareket", "TUS_SOL", C['text_sec']),
            ("Sağa Hareket", "TUS_SAG", C['text_sec']),
            ("Yukarı Hareket", "TUS_YUKARI", C['text_sec']),
            ("Aşağı Hareket", "TUS_ASAGI", C['text_sec']),
            ("Dur", "TUS_DUR", C['text_dim']),
            ("Ateş", "TUS_ATES", C['warning']),
            ("Ateş Durdur", "TUS_ATIS_DUR", C['text_sec']),
            ("Lazer (basılı tut)", "TUS_LAZER", C['info']),
            ("Acil Durdur", "TUS_ACIL_DUR", C['danger']),
        ]

        mcfg_tus = config.MOTOR_KONTROL
        for etiket, tus_key, renk in _tus_satirlar:
            row_f = QFrame()
            row_f.setStyleSheet(
                f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};"
                f"border-radius:5px;}}")
            row_l = QHBoxLayout(row_f)
            row_l.setContentsMargins(10, 4, 8, 4); row_l.setSpacing(8)

            lbl = QLabel(etiket)
            lbl.setFixedWidth(110)
            lbl.setStyleSheet(
                f"color:{C['text_sec']};font-size:11px;background:transparent;")
            edit = QLineEdit(mcfg_tus.get(tus_key, ""))
            edit.setFixedHeight(26)
            edit.setPlaceholderText("tuş…")

            def _tus_degisti_cb(v, k=tus_key):
                mcfg_tus[k] = v
                self.tus_degisti.emit(k, v)

            edit.textChanged.connect(_tus_degisti_cb)
            row_l.addWidget(lbl); row_l.addWidget(edit, 1)
            row_f.setFixedHeight(40)
            b_tus.ekle(row_f)

        lay.addWidget(b_tus)

        # LiDAR AYARLARI
        b_lidar = KatlanirBolum("LiDAR  MESAFE  SENSÖRÜ", acik=False)
        lidar = config.LIDAR

        # Etkin toggle
        etkin_combo = _combo(["Pasif", "Aktif"], "Aktif" if lidar.get("ETKIN") else "Pasif")
        etkin_combo.currentTextChanged.connect(
            lambda v: lidar.__setitem__("ETKIN", v == "Aktif"))
        b_lidar.ekle(_pkart("Durum", etkin_combo, "Aktif = bağlan ve ölç"))

        # Tip
        tip_combo = _combo(["TFLUNA", "TFLUNAP", "RPLIDAR", "SIM"],
                           lidar.get("TIP", "TFLUNA"))
        tip_combo.currentTextChanged.connect(lambda v: lidar.__setitem__("TIP", v))
        b_lidar.ekle(_pkart("Sensör Tipi", tip_combo,
                            "TFLUNA=TF-Luna · RPLIDAR=RP-LiDAR A1/A2 · SIM=test"))

        # Port
        lidar_port_edit = QLineEdit(lidar.get("PORT", "COM6"))
        lidar_port_edit.setFixedHeight(30)
        lidar_port_edit.textChanged.connect(lambda v: lidar.__setitem__("PORT", v))
        b_lidar.ekle(_pkart("Port", lidar_port_edit, "Örn: COM6 · /dev/ttyUSB0"))

        # Baud
        baud_combo = _combo(["9600", "115200", "230400"],
                            str(lidar.get("BAUD", 115200)))
        baud_combo.currentTextChanged.connect(
            lambda v: lidar.__setitem__("BAUD", int(v)))
        b_lidar.ekle(_pkart("Baud Rate", baud_combo))

        # Min / Max cm
        for etiket, key, lo, hi, alt in [
            ("Min Mesafe (cm)", "MIN_CM", 0, 500, "Gürültü filtresi alt sınırı"),
            ("Max Mesafe (cm)", "MAX_CM", 100, 5000, "Ölçüm üst sınırı"),
        ]:
            sp = _int_spin(lidar.get(key, 10 if "MIN" in key else 3000), lo, hi)
            sp.valueChanged.connect(lambda v, k=key: lidar.__setitem__(k, v))
            b_lidar.ekle(_pkart(etiket, sp, alt))

        lay.addWidget(b_lidar)

        # STEREO & KAMERA GEOMETRİSİ
        b_stereo = KatlanirBolum("STEREO  KAMERA  GEOMETRİSİ", acik=False)
        geo = config.KAMERA_GEOMETRI

        # Stereo etkin
        stereo_combo = _combo(["Pasif", "Aktif"],
                              "Aktif" if geo.get("STEREO_ETKIN") else "Pasif")
        stereo_combo.currentTextChanged.connect(
            lambda v: geo.__setitem__("STEREO_ETKIN", v == "Aktif"))
        b_stereo.ekle(_pkart("Stereo Triangülasyon", stereo_combo,
                             "Aktif = iki kameradan 3D konum hesapla"))

        # Baseline
        bl = _float_spin(geo.get("BASELINE_M", 0.30), 0.01, 2.00, 0.01, 3)
        bl.valueChanged.connect(lambda v: geo.__setitem__("BASELINE_M", v))
        b_stereo.ekle(_pkart("Baseline (m)", bl, "Kamera A-B arası fiziksel mesafe"))

        # FOV
        for etiket, key in [("FOV Yatay A (°)", "FOV_H_A"), ("FOV Yatay B (°)", "FOV_H_B")]:
            fov = _float_spin(geo.get(key, 90.0), 10.0, 180.0, 1.0, 1)
            fov.valueChanged.connect(lambda v, k=key: geo.__setitem__(k, v))
            b_stereo.ekle(_pkart(etiket, fov, "Kameranın yatay görüş açısı"))

        lay.addWidget(b_stereo)

        # AYARLARI KAYDET
        kaydet_btn = QPushButton("💾  AYARLARI KAYDET  (config_override.json)")
        kaydet_btn.setFixedHeight(44)
        kaydet_btn.setStyleSheet(
            f"QPushButton{{background:#0a3020;color:{C['success']};"
            f"border:2px solid {C['success']};border-radius:6px;"
            f"font-size:13px;font-weight:800;letter-spacing:1px;}}"
            f"QPushButton:hover{{background:#0f4a30;border-color:#00ff88;}}"
            f"QPushButton:pressed{{background:#062010;}}")
        kaydet_btn.clicked.connect(self._ayarlari_kaydet)
        lay.addWidget(kaydet_btn)

        self._kaydet_durum = QLabel("")
        self._kaydet_durum.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._kaydet_durum.setStyleSheet(
            f"color:{C['text_dim']};font-size:11px;background:transparent;")
        lay.addWidget(self._kaydet_durum)

        lay.addStretch()

    # Model sınıfları güncelleme
    def model_siniflari_guncelle(self, cam_idx: int, siniflari: list) -> None:
        self._cam_model_siniflari[cam_idx] = list(siniflari)
        self._uncls_guncelle(cam_idx)
        # SinifListesi autocomplete
        for lst in self._sinif_listeleri:
            lst.model_siniflari_guncelle(siniflari)

    def _uncls_guncelle(self, cam_idx: int) -> None:
        lbl = self._uncls_lbls.get(cam_idx)
        if lbl is None:
            return
        tum = set(self._cam_model_siniflari.get(cam_idx, []))
        if not tum:
            lbl.setText("Sınıflandırılmamış: —  (model yüklenmedi)")
            return
        listeleri = self._cam_sinif_listeleri.get(cam_idx, {})
        sinifli: set = set()
        for lst in listeleri.values():
            sinifli.update(lst._cfg)  # SinifListesi internal cfg list
        uncls = sorted(tum - sinifli)
        if uncls:
            lbl.setText("Sınıflandırılmamış:  " + "  ·  ".join(uncls))
        else:
            lbl.setText("✓ Tüm sınıflar kategorize edildi")

    # Motor log
    def _motor_log_guncelle(self) -> None:
        try:
            from motor import _KOMUT_LOG
            uzunluk = len(_KOMUT_LOG)
            if uzunluk == self._log_son_uzunluk:
                return
            # Sadece yeni girişleri al
            yeni = list(_KOMUT_LOG)[self._log_son_uzunluk:]
            self._log_son_uzunluk = uzunluk
            for ts, komut, ok in yeni:
                simge = "✓" if ok else "✕"
                renk = "#00e676" if ok else "#ff5252"
                self._motor_log_txt.append(
                    f'<span style="color:#666">[{ts}]</span> '
                    f'<span style="color:{renk}">{simge}</span> '
                    f'<span style="color:#e0e0e0">{komut}</span>')
            sb = self._motor_log_txt.verticalScrollBar()
            sb.setValue(sb.maximum())
        except Exception:
            pass

    def _motor_log_temizle(self) -> None:
        self._motor_log_txt.clear()
        try:
            from motor import _KOMUT_LOG
            _KOMUT_LOG.clear()
            self._log_son_uzunluk = 0
        except Exception:
            pass

    def _preset_gonder(self, metin: str) -> None:
        if not metin.strip():
            return
        komut = metin.replace("\\n", "\n").replace("\\r", "\r")
        if not komut.endswith("\n"):
            komut += "\n"
        self._gonder(komut, metin.strip())

    # Kaydet
    def _ayarlari_kaydet(self) -> None:
        ok = config.json_kaydet()
        if ok:
            self._kaydet_durum.setText("✓ Kaydedildi → config_override.json")
            self._kaydet_durum.setStyleSheet(
                f"color:{C['success']};font-size:12px;background:transparent;font-weight:700;")
        else:
            self._kaydet_durum.setText("✗ Kayıt başarısız — log'u kontrol edin")
            self._kaydet_durum.setStyleSheet(
                f"color:{C['danger']};font-size:12px;background:transparent;font-weight:700;")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(4000, lambda: self._kaydet_durum.setText(""))

    # Bağlantı yönetimi
    def _motor_al(self):
        try:
            from motor import MotorKontrol
            return MotorKontrol._instance
        except Exception:
            return None

    def _baglan_toggle(self) -> None:
        port = self._port_combo.currentText().strip()
        if not port:
            self._log("⚠ Port seçilmedi.")
            return
        try:
            from motor import MotorKontrol
            m = MotorKontrol._instance
            if m and m.bagli_mi():
                m.kapat()
                MotorKontrol._instance = None
                self._log(f"✕ Bağlantı kesildi ({port})")
            else:
                config.DONANIM["PORT"] = port
                yeni = MotorKontrol.port_degistir(port)
                if yeni.bagli_mi():
                    self._log(f"✓ Bağlandı → {port} @ {config.DONANIM.get('BAUD_RATE',115200)}")
                else:
                    self._log(f"✕ Bağlantı başarısız ({port}) — yeniden deneniyor…")
        except Exception as e:
            self._log(f"⚠ Hata: {e}")
        self._durum_guncelle()

    def _portlari_yenile(self) -> None:
        portlar = _port_listesi()
        mevcut = self._port_combo.currentText()
        self._port_combo.blockSignals(True)
        self._port_combo.clear()
        self._port_combo.addItems(portlar if portlar else [mevcut])
        idx = self._port_combo.findText(mevcut)
        self._port_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._port_combo.blockSignals(False)
        self._log(f"↻ {len(portlar)} port bulundu: {', '.join(portlar)}" if portlar
                  else "⚠ Bağlı port yok")

    def _ping_test(self) -> None:
        try:
            from motor import MotorKontrol
            m = MotorKontrol._instance
            if m and m.bagli_mi():
                ok = m.ping()
                self._log("✓ PING → PONG" if ok else "✕ PING → yanıt yok")
            else:
                self._log("⚠ Motor bağlı değil — önce BAĞLAN")
        except Exception as e:
            self._log(f"⚠ Ping hatası: {e}")

    def _durum_guncelle(self) -> None:
        try:
            from motor import MotorKontrol
            m = MotorKontrol._instance
            bagli = m is not None and m.bagli_mi()
        except Exception:
            bagli = False

        if bagli:
            port = config.DONANIM.get("PORT", "?")
            self._durum_lbl.setText(f"● BAĞLI  —  {port}")
            self._durum_lbl.setStyleSheet(
                f"background:#021a0d;border:1px solid #0a4020;border-radius:5px;"
                f"font-size:11px;font-weight:700;letter-spacing:0.8px;"
                f"color:{C['success']};")
            self._baglan_btn.setText("■  BAĞLANTIYI KES")
            self._baglan_btn.setStyleSheet(
                f"QPushButton{{background:#3d0615;color:{C['danger']};"
                f"border:1px solid #6b0a22;border-radius:5px;"
                f"font-size:12px;font-weight:800;letter-spacing:1px;}}"
                f"QPushButton:hover{{background:#4d0820;border-color:{C['danger']};}}"
                f"QPushButton:pressed{{background:#2d040f;}}")
        else:
            self._durum_lbl.setText("○ BAĞLANTI YOK")
            self._durum_lbl.setStyleSheet(
                f"background:{C['bg_card']};border:1px solid {C['border']};"
                f"border-radius:5px;font-size:11px;font-weight:700;"
                f"letter-spacing:0.8px;color:{C['danger']};")
            self._baglan_btn.setText("▶  BAĞLAN")
            self._baglan_btn.setStyleSheet(
                f"QPushButton{{background:#063d20;color:{C['success']};"
                f"border:1px solid #0a6030;border-radius:5px;"
                f"font-size:12px;font-weight:800;letter-spacing:1px;}}"
                f"QPushButton:hover{{background:#0a5028;border-color:{C['success']};}}"
                f"QPushButton:pressed{{background:#042810;}}")

    def _gonder(self, komut: str, etiket: str = "") -> None:
        try:
            from motor import MotorKontrol
            m = MotorKontrol._instance
            if m and m.bagli_mi():
                ok = m._gonder(komut)
                tag = etiket or komut.strip()
                self._log(f"→ {tag}" if ok else f"✕ {tag} (gönderim hatası)")
            else:
                self._log("⚠ Bağlı değil — önce BAĞLAN")
        except Exception as e:
            self._log(f"⚠ {e}")

    def _ozel_komut_gonder(self) -> None:
        t = self._komut_giris.text()
        if not t: return
        komut = t.replace("\\n", "\n").replace("\\r", "\r")
        if not komut.endswith("\n"):
            komut += "\n"
        self._gonder(komut, t.strip())
        self._komut_giris.clear()

    def _log(self, mesaj: str) -> None:
        self._terminal.append(mesaj)
        sb = self._terminal.verticalScrollBar()
        sb.setValue(sb.maximum())

    def toggle(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show(); self.raise_()
            self._durum_guncelle()
            # Panel açılınca config'den güncel model sınıflarını oku
            for ci, ayar in enumerate(config.KAMERA_AYARLAR):
                siniflari = ayar.get("_MODEL_SINIFLARI", [])
                if siniflari:
                    self.model_siniflari_guncelle(ci, siniflari)


class MotorKontrolPanel(QDialog):
    ates_sinyal = pyqtSignal()
    ates_dur_sinyal = pyqtSignal()

    def __init__(self, ana: QWidget):
        super().__init__(ana)
        self.setWindowTitle("KONTROL")
        self.setWindowFlags(Qt.WindowType.Tool |
                            Qt.WindowType.WindowCloseButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.resize(420, 600)
        self.setStyleSheet(_DIALOG_QSS)
        self._ates_aktif = False
        self._lazer_aktif = False
        self._basin_tuslar: set[str] = set()  # şu an basılı tuşlar

        # Basılı tuş -> sürekli motor komutu zamanlayıcısı
        self._hareket_timer = QTimer(self)
        self._hareket_timer.timeout.connect(self._hareket_gonder)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background:{C['bg_panel']};border:none;")
        body = QWidget(); body.setStyleSheet(f"background:{C['bg_panel']};")
        vbox = QVBoxLayout(body)
        vbox.setContentsMargins(16, 14, 16, 16); vbox.setSpacing(6)
        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0); outer.addWidget(scroll)
        self._vbox = vbox
        self._kur()

    # Klavye override: basılı tutma davranışı
    def keyPressEvent(self, event) -> None:
        if event.isAutoRepeat():
            return
        key_str = self._event_to_key(event)
        if key_str and key_str not in self._basin_tuslar:
            self._basin_tuslar.add(key_str)
            self._tus_bas_kontrol(key_str)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if event.isAutoRepeat():
            return
        key_str = self._event_to_key(event)
        if key_str:
            self._basin_tuslar.discard(key_str)
            self._tus_birak_kontrol(key_str)
        super().keyReleaseEvent(event)

    def _event_to_key(self, event) -> str:
        txt = event.text().lower()
        if txt and txt.isprintable() and txt.strip():
            return txt
        from PyQt6.QtCore import Qt as _Qt
        _map = {
            _Qt.Key.Key_Space: "space",
            _Qt.Key.Key_Escape: "escape",
            _Qt.Key.Key_F: "f",
            _Qt.Key.Key_G: "g",
            _Qt.Key.Key_W: "w",
            _Qt.Key.Key_A: "a",
            _Qt.Key.Key_S: "s",
            _Qt.Key.Key_D: "d",
        }
        return _map.get(event.key(), "")

    def _tus_bas_kontrol(self, key: str) -> None:
        mcfg = config.MOTOR_KONTROL
        # Lazer
        if key == mcfg.get("TUS_LAZER", "space"):
            self._lazer_ac()
            return
        # Ateş
        if key == mcfg.get("TUS_ATES", "f"):
            if not self._ates_aktif:
                self._ates_btn.setChecked(True)
                self._ates_toggle()
            return
        # Ateş durdur
        if key == mcfg.get("TUS_ATIS_DUR", "g"):
            if self._ates_aktif:
                self._ates_btn.setChecked(False)
                self._ates_toggle()
            return
        # Acil durdur
        if key == mcfg.get("TUS_ACIL_DUR", "escape"):
            self._acil_dur_kisa()
            return
        # Hareket tuşlarından biri basılıysa timer başlat
        hareket_tuslar = {
            mcfg.get("TUS_SOL", "a"),
            mcfg.get("TUS_SAG", "d"),
            mcfg.get("TUS_YUKARI", "w"),
            mcfg.get("TUS_ASAGI", "s"),
            mcfg.get("TUS_DUR", "space"),
        }
        if key in hareket_tuslar:
            hz = mcfg.get("HAREKET_HZ", 20)
            interval = max(20, int(1000 / hz))
            if not self._hareket_timer.isActive():
                self._hareket_timer.start(interval)
                self._hareket_gonder()  # ilk komut hemen

    def _tus_birak_kontrol(self, key: str) -> None:
        mcfg = config.MOTOR_KONTROL
        # Lazer bırakıldı -> kapat
        if key == mcfg.get("TUS_LAZER", "space"):
            self._lazer_kapat()
        # Hareket tuşu bırakıldı - aktif hareket tuşu kalmadıysa durdur
        hareket_tuslar = {
            mcfg.get("TUS_SOL", "a"),
            mcfg.get("TUS_SAG", "d"),
            mcfg.get("TUS_YUKARI", "w"),
            mcfg.get("TUS_ASAGI", "s"),
        }
        remaining_hareket = self._basin_tuslar & hareket_tuslar
        if not remaining_hareket:
            self._hareket_timer.stop()
            self._motor_gonder(mcfg.get("KOMUT_DUR", "!X0Y0*\n"))

    def _hareket_gonder(self) -> None:
        mcfg = config.MOTOR_KONTROL
        # Öncelik sırası: YUKARI > ASAGI > SOL > SAG
        prio = [
            (mcfg.get("TUS_YUKARI", "w"), mcfg.get("KOMUT_YUKARI", "!X0Y-300*\n")),
            (mcfg.get("TUS_ASAGI", "s"), mcfg.get("KOMUT_ASAGI", "!X0Y300*\n")),
            (mcfg.get("TUS_SOL", "a"), mcfg.get("KOMUT_SOL", "!X-300Y0*\n")),
            (mcfg.get("TUS_SAG", "d"), mcfg.get("KOMUT_SAG", "!X300Y0*\n")),
        ]
        for tus, komut in prio:
            if tus in self._basin_tuslar:
                self._motor_gonder(komut)
                return

    # UI İnşa
    def _kur(self) -> None:
        lay = self._vbox
        mcfg = config.MOTOR_KONTROL

        # Bilgi bandı
        info = QLabel(
            "WASD = Hareket (basılı tut)   ·   SPACE = Lazer   ·   F = Ateş")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        info.setStyleSheet(
            f"color:{C['text_dim']};font-size:10px;background:{C['bg_card']};"
            f"border:1px solid {C['border']};border-radius:4px;padding:6px;")
        lay.addWidget(info)

        # Yönlü kontrol
        b_joy = KatlanirBolum("YÖNLÜ  KONTROL  (basılı tut)", acik=True)
        joy_frame = QFrame()
        joy_frame.setStyleSheet(
            f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};"
            f"border-radius:8px;}}")
        jl = QVBoxLayout(joy_frame)
        jl.setContentsMargins(12, 12, 12, 12); jl.setSpacing(8)

        _BTN = (
            f"QPushButton{{background:{C['bg_panel']};color:{C['text_pri']};"
            f"border:1px solid {C['border']};border-radius:6px;"
            f"font-size:22px;font-weight:700;min-width:60px;min-height:60px;}}"
            f"QPushButton:pressed{{background:{C['accent']};color:{C['bg_deep']};"
            f"border-color:{C['accent']};}}"
            f"QPushButton:hover{{border-color:{C['border_act']};}}"
        )

        def _joy_btn(txt, tip, komut_key, tus_key):
            b = QPushButton(txt); b.setStyleSheet(_BTN); b.setToolTip(tip)
            # pressed/released -> sürekli gönderim
            b.pressed.connect(lambda k=tus_key: self._tus_bas_kontrol(
                mcfg.get(k, "")))
            b.released.connect(lambda k=tus_key: self._tus_birak_kontrol(
                mcfg.get(k, "")))
            return b

        r1 = QHBoxLayout(); r1.setSpacing(8)
        r1.addStretch()
        r1.addWidget(_joy_btn(
            "▲", f"Yukarı [{mcfg.get('TUS_YUKARI','W').upper()}] — basılı tut",
            "KOMUT_YUKARI", "TUS_YUKARI"))
        r1.addStretch()
        jl.addLayout(r1)

        r2 = QHBoxLayout(); r2.setSpacing(8)
        r2.addWidget(_joy_btn(
            "◀", f"Sol [{mcfg.get('TUS_SOL','A').upper()}]",
            "KOMUT_SOL", "TUS_SOL"))
        dur_btn = QPushButton("■")
        dur_btn.setStyleSheet(
            f"QPushButton{{background:#1a0510;color:{C['danger']};"
            f"border:1px solid {C['border']};border-radius:6px;"
            f"font-size:18px;min-width:60px;min-height:60px;}}"
            f"QPushButton:pressed{{background:{C['danger']};color:{C['bg_deep']};}}"
            f"QPushButton:hover{{border-color:{C['danger']};}}")
        dur_btn.setToolTip("Dur")
        dur_btn.clicked.connect(lambda: self._motor_gonder(
            mcfg.get("KOMUT_DUR", "!X0Y0*\n")))
        r2.addWidget(dur_btn)
        r2.addWidget(_joy_btn(
            "▶", f"Sağ [{mcfg.get('TUS_SAG','D').upper()}]",
            "KOMUT_SAG", "TUS_SAG"))
        jl.addLayout(r2)

        r3 = QHBoxLayout(); r3.setSpacing(8)
        r3.addStretch()
        r3.addWidget(_joy_btn(
            "▼", f"Aşağı [{mcfg.get('TUS_ASAGI','S').upper()}]",
            "KOMUT_ASAGI", "TUS_ASAGI"))
        r3.addStretch()
        jl.addLayout(r3)

        b_joy.ekle(joy_frame)
        lay.addWidget(b_joy)

        # Lazer
        b_lazer = KatlanirBolum("LAZER", acik=True)
        lazer_frame = QFrame()
        lazer_frame.setStyleSheet(
            f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};"
            f"border-radius:8px;}}")
        lf = QVBoxLayout(lazer_frame)
        lf.setContentsMargins(12, 12, 12, 12); lf.setSpacing(8)

        self._lazer_btn = QPushButton(
            f"◉   LAZER   [{mcfg.get('TUS_LAZER','SPACE').upper()}]")
        self._lazer_btn.setFixedHeight(48)
        self._lazer_btn.setCheckable(True)
        self._lazer_btn.setStyleSheet(
            f"QPushButton{{background:#001a33;color:{C['info']};"
            f"font-weight:800;font-size:13px;letter-spacing:1px;"
            f"border:1px solid #003366;border-radius:6px;}}"
            f"QPushButton:hover{{background:#002244;border-color:{C['info']};}}"
            f"QPushButton:checked{{background:{C['info']};color:{C['bg_deep']};"
            f"border-color:{C['info']};}}"
            f"QPushButton:pressed{{background:#001533;}}")
        self._lazer_btn.pressed.connect(self._lazer_ac)
        self._lazer_btn.released.connect(self._lazer_kapat)

        self._lazer_durum = QLabel("○ KAPALI")
        self._lazer_durum.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lazer_durum.setStyleSheet(
            f"color:{C['text_dim']};font-size:10px;font-weight:600;"
            f"letter-spacing:1px;background:transparent;")
        lf.addWidget(self._lazer_btn)
        lf.addWidget(self._lazer_durum)
        b_lazer.ekle(lazer_frame)
        lay.addWidget(b_lazer)

        # Manuel ateş
        b_ates = KatlanirBolum("MANUEL  ATEŞ", acik=True)
        ates_frame = QFrame()
        ates_frame.setStyleSheet(
            f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};"
            f"border-radius:8px;}}")
        af = QVBoxLayout(ates_frame)
        af.setContentsMargins(12, 12, 12, 12); af.setSpacing(8)

        self._ates_btn = QPushButton(
            f"🎯   ATEŞ   [{mcfg.get('TUS_ATES','F').upper()}]")
        self._ates_btn.setFixedHeight(52)
        self._ates_btn.setCheckable(True)
        self._ates_btn.setStyleSheet(
            f"QPushButton{{background:#5c0018;color:{C['danger']};"
            f"font-weight:800;font-size:14px;letter-spacing:1.5px;"
            f"border:1px solid #8b0028;border-radius:6px;}}"
            f"QPushButton:hover{{background:#7a0022;border-color:{C['danger']};}}"
            f"QPushButton:checked{{background:{C['danger']};color:{C['bg_deep']};"
            f"border-color:{C['danger']};}}"
            f"QPushButton:pressed{{background:#3d0010;}}")
        self._ates_btn.clicked.connect(self._ates_toggle)

        self._ates_durum = QLabel("● BEKLEMEDE")
        self._ates_durum.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ates_durum.setStyleSheet(
            f"color:{C['text_dim']};font-size:10px;font-weight:600;"
            f"letter-spacing:1px;background:transparent;")
        af.addWidget(self._ates_btn)
        af.addWidget(self._ates_durum)
        b_ates.ekle(ates_frame)
        lay.addWidget(b_ates)

        # Ayarlar
        b_set = KatlanirBolum("JOYSTICK  AYARLARI", acik=False)

        hz_spin = _int_spin(mcfg.get("HAREKET_HZ", 20), 1, 100)
        hz_spin.valueChanged.connect(lambda v: (
            mcfg.__setitem__("HAREKET_HZ", v),
            self._hareket_timer.setInterval(max(20, int(1000/v)))
            if self._hareket_timer.isActive() else None))
        b_set.ekle(_pkart("Hareket Gönderim Hz", hz_spin,
                          "Basılı tuş başına saniyedeki komut sayısı"))

        ol = _int_spin(mcfg.get("JOISTIK_OLCEK", 300), 50, 2000)
        ol.valueChanged.connect(lambda v: mcfg.__setitem__("JOISTIK_OLCEK", v))
        b_set.ekle(_pkart("Joystick Ölçek", ol))

        as_s = _int_spin(mcfg.get("ATES_SURE_MS", 500), 50, 10000)
        as_s.valueChanged.connect(lambda v: mcfg.__setitem__("ATES_SURE_MS", v))
        b_set.ekle(_pkart("Ateş Süresi (ms)", as_s))

        lay.addWidget(b_set)
        lay.addStretch()

        # Kısayol nesneleri (tus_guncelle için referans) 
        self._kisa_yollar: dict[str, QShortcut] = {}

    # Lazer
    def _lazer_ac(self) -> None:
        if self._lazer_aktif:
            return
        self._lazer_aktif = True
        self._lazer_btn.setChecked(True)
        self._lazer_durum.setText("● AKTİF")
        self._lazer_durum.setStyleSheet(
            f"color:{C['info']};font-size:10px;font-weight:700;"
            f"letter-spacing:1px;background:transparent;")
        komut = config.MOTOR_KONTROL.get("LAZER_KOMUTU", "lazer_ac\n")
        self._motor_gonder(komut.replace("\\n", "\n"))

    def _lazer_kapat(self) -> None:
        if not self._lazer_aktif:
            return
        self._lazer_aktif = False
        self._lazer_btn.setChecked(False)
        self._lazer_durum.setText("○ KAPALI")
        self._lazer_durum.setStyleSheet(
            f"color:{C['text_dim']};font-size:10px;font-weight:600;"
            f"letter-spacing:1px;background:transparent;")
        komut = config.MOTOR_KONTROL.get("LAZER_DUR_KOMUTU", "lazer_kapat\n")
        self._motor_gonder(komut.replace("\\n", "\n"))

    # Ateş
    def _ates_toggle(self) -> None:
        if self._ates_btn.isChecked():
            self._ates_aktif = True
            self._ates_durum.setText("🔴 ATEŞ EDİYOR")
            self._ates_durum.setStyleSheet(
                f"color:{C['danger']};font-size:10px;font-weight:700;"
                f"letter-spacing:1px;background:transparent;")
            try:
                from donanim import ates_komutu
                ates_komutu(0, (0, 0, 0, 0), "manuel")
            except Exception:
                pass
        else:
            self._ates_aktif = False
            self._ates_durum.setText("● BEKLEMEDE")
            self._ates_durum.setStyleSheet(
                f"color:{C['text_dim']};font-size:10px;font-weight:600;"
                f"letter-spacing:1px;background:transparent;")
            try:
                from donanim import ates_dur_komutu
                ates_dur_komutu()
            except Exception:
                pass

    def _ates_toggle_kisa(self) -> None:
        self._ates_btn.setChecked(not self._ates_btn.isChecked())
        self._ates_toggle()

    def _ates_dur_kisa(self) -> None:
        if self._ates_aktif:
            self._ates_btn.setChecked(False)
            self._ates_toggle()

    def _acil_dur_kisa(self) -> None:
        if self._ates_aktif:
            self._ates_btn.setChecked(False)
            self._ates_toggle()
        self._lazer_kapat()
        self._hareket_timer.stop()
        self._basin_tuslar.clear()
        self._motor_gonder(
            config.MOTOR_KONTROL.get("ACIL_DUR_KOMUTU", "dur\n"))

    # Motor gönder
    def _motor_gonder(self, komut: str) -> None:
        if not komut:
            return
        # \n escape -> gerçek newline
        k = komut.replace("\\n", "\n")
        if not k.endswith("\n"):
            k += "\n"
        try:
            from motor import MotorKontrol
            m = MotorKontrol._instance
            if m and m.bagli_mi():
                m._gonder(k)
        except Exception:
            pass

    # Kısayol güncelle (tus_degisti sinyalinden)
    def tus_guncelle(self, key: str, deger: str) -> None:
        sc = self._kisa_yollar.get(key)
        if sc:
            try:
                sc.setKey(QKeySequence(deger))
            except Exception:
                pass

    def toggle(self) -> None:
        if self.isVisible():
            self._hareket_timer.stop()
            self._basin_tuslar.clear()
            self.hide()
        else:
            self.show(); self.raise_()

