
from PyQt6.QtCore import (Qt, QTimer, QRectF)
from PyQt6.QtGui import (QColor, QPainter, QPen, QBrush,
                              QFont, QRadialGradient)
from PyQt6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout,
                              QPushButton, QSizePolicy, QFrame,
                              QSpinBox)

from .styles import C, CAM_A_COLOR, CAM_B_COLOR, CAM_COLORS, GLOW, fps_color, qc


class LedIndicator(QWidget):
    def __init__(self, color: str = C["text_dim"], size: int = 10,
                 blink: bool = False, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._size = size
        self._alpha = 255
        self._blink = blink
        self._on = True
        self._pulse = 0.0
        self._pulse_up = True
        setattr(self, '_t', None)
        self.setFixedSize(size + 8, size + 8)

        # Sürekli pulse animasyonu (glow nefes efekti)
        self._anim_t = QTimer(self)
        self._anim_t.timeout.connect(self._anim_step)
        self._anim_t.start(30)

        if blink:
            self._start_blink()

    def _start_blink(self) -> None:
        t = QTimer(self)
        t.timeout.connect(self._toggle)
        t.start(500)
        self._blink_t = t

    def set_state(self, durum: str) -> None:
        renk = {
            "active": C["success"],
            "error": C["danger"],
            "warn": C["warning"],
            "idle": C["text_dim"],
        }.get(durum, C["text_dim"])
        blink = durum in ("error", "warn")
        self.set_color(renk, blink)

    def set_color(self, hex_color: str, blink: bool = False):
        self._color = QColor(hex_color)
        self._blink = blink
        if blink and not hasattr(self, '_blink_t'):
            self._start_blink()
        elif not blink and hasattr(self, '_blink_t'):
            self._blink_t.stop()
            del self._blink_t
        self._on = True
        self.update()

    def _toggle(self):
        self._on = not self._on
        self.update()

    def _anim_step(self):
        step = 0.05
        self._pulse += step if self._pulse_up else -step
        if self._pulse >= 1.0: self._pulse_up = False
        if self._pulse <= 0.0: self._pulse_up = True
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self._size
        cx = (self.width() - s) // 2
        cy = (self.height() - s) // 2
        col = QColor(self._color)
        if not self._on:
            col.setAlpha(35)

        # Dış glow halo (nefes efekti ile)
        glow_alpha = int(GLOW["normal"] + GLOW["dim"] * self._pulse)
        if not self._on:
            glow_alpha = 0
        glow = QRadialGradient(cx + s/2, cy + s/2, s * 1.4)
        glow.setColorAt(0, QColor(col.red(), col.green(), col.blue(), glow_alpha))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(cx - s//2, cy - s//2, s * 2, s * 2)

        # İç parlak halka
        ring_col = QColor(col.red(), col.green(), col.blue(),
                          int(40 + 30 * self._pulse) if self._on else 0)
        p.setPen(QPen(ring_col, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(cx - 1, cy - 1, s + 2, s + 2)

        # Core dot
        p.setBrush(QBrush(col))
        p.setPen(QPen(col.lighter(140), 0.5))
        p.drawEllipse(cx, cy, s, s)


class PhaseBadge(QWidget):
    FAZ_RENK = {
        "TARAMA" : C["text_sec"],
        "ONCELIK_SEC" : C["warning"],
        "HEDEF_SEC" : C["warning"],
        "DOST_DUSMAN" : C["info"],
        "KAMERA_YONLENDIR": C["accent"],
        "BALON_DOGRULA" : "#b042ff",
        "ATIS" : C["danger"],
        "BALON_YOK_ISLE" : "#b042ff",
        "SIRADAKI" : C["accent"],
        "TAMAMLANDI" : C["success"],
        "DURDURULDU" : C["text_dim"],
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._faz = "TARAMA"
        self._renk = QColor(C["text_sec"])
        self._pulse = 0.0
        self._up = True
        self._t = QTimer(self)
        self._t.timeout.connect(self._pulse_step)
        self._t.start(25)
        self.setFixedHeight(36)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)

    def set_faz(self, faz: str):
        self._faz = faz
        hex_renk = self.FAZ_RENK.get(faz, C["text_sec"])
        self._renk = QColor(hex_renk)
        self.update()

    set_phase = set_faz  # compat alias

    def _pulse_step(self):
        step = 0.045
        self._pulse += step if self._up else -step
        if self._pulse >= 1.0: self._up = False
        if self._pulse <= 0.0: self._up = True
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        col = self._renk

        # Arka plan dolu tonu (pulse ile)
        bg_alpha = int(12 + 18 * self._pulse)
        p.setBrush(QColor(col.red(), col.green(), col.blue(), bg_alpha))
        border_alpha = int(110 + 120 * self._pulse)
        p.setPen(QPen(QColor(col.red(), col.green(), col.blue(), border_alpha), 1.5))
        p.drawRoundedRect(r, 5, 5)

        # İç ışıma çizgisi (üst kenar)
        glow_line = QColor(col.red(), col.green(), col.blue(),
                           int(60 + 60 * self._pulse))
        p.setPen(QPen(glow_line, 1))
        p.drawLine(r.left() + 10, r.top() + 1, r.right() - 10, r.top() + 1)

        # Metin
        p.setPen(col)
        font = QFont("Consolas", 10, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        p.setFont(font)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self._faz)


class TelemetryLabel(QWidget):
    def __init__(self, isim: str, deger: str = "—",
                 color: str = C["text_mono"], parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(isim)
        lbl.setStyleSheet(
            f"color:{C['text_sec']};font-size:12px;background:transparent;")
        self._val = QLabel(deger)
        self._val.setStyleSheet(
            f"color:{color};font-family:'Consolas','Courier New',monospace;"
            f"font-size:12px;font-weight:600;background:transparent;")
        h.addWidget(lbl)
        h.addStretch()
        h.addWidget(self._val)

    def setValue(self, v: str) -> None:
        self._val.setText(v)

    def value(self) -> str:
        return self._val.text()


class MiniTelRow(QWidget):
    def __init__(self, icon: str, label: str, value: str = "—",
                 value_color: str = C["text_mono"], parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setStyleSheet("background:transparent;")
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(5)

        if icon:
            ico = QLabel(icon)
            ico.setFixedWidth(16)
            ico.setStyleSheet(f"color:{C['text_dim']};font-size:13px;"
                              f"background:transparent;")
            h.addWidget(ico)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{C['text_sec']};font-size:13px;"
                          f"background:transparent;")
        self._val = QLabel(value)
        self._val.setStyleSheet(
            f"color:{value_color};font-family:Consolas;font-size:13px;"
            f"font-weight:600;background:transparent;")
        h.addWidget(lbl)
        h.addStretch()
        h.addWidget(self._val)

    def setValue(self, v: str) -> None:
        self._val.setText(v)

    def value(self) -> str:
        return self._val.text()

    def setColor(self, color: str) -> None:
        self._val.setStyleSheet(
            f"color:{color};font-family:Consolas;font-size:13px;"
            f"font-weight:600;background:transparent;")


class FpsBar(QWidget):
    MAX_FPS = 60.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fps = 0.0
        self._etkin = False
        self.setFixedHeight(18)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_fps(self, fps: float, etkin: bool = True) -> None:
        self._fps = fps
        self._etkin = etkin
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Arka plan
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C["bg_input"]))
        p.drawRoundedRect(0, 0, w, h, 3, 3)

        if self._etkin and self._fps > 0:
            oran = min(1.0, self._fps / self.MAX_FPS)
            renk = QColor(fps_color(self._fps))
            fill_w = max(4, int(w * oran))

            # Dolum
            p.setBrush(QColor(renk.red(), renk.green(), renk.blue(), 60))
            p.drawRoundedRect(0, 0, fill_w, h, 3, 3)

            # Parlak kenar çizgisi (sağ)
            p.setBrush(renk)
            p.drawRect(fill_w - 2, 0, 2, h)

            # FPS metni
            p.setPen(renk)
            p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            metin = f"{self._fps:.0f}"
            p.drawText(QRectF(4, 0, w - 8, h), Qt.AlignmentFlag.AlignVCenter, metin)
        else:
            p.setPen(QColor(C["text_dim"]))
            p.setFont(QFont("Consolas", 9))
            p.drawText(QRectF(4, 0, w - 8, h), Qt.AlignmentFlag.AlignVCenter, "—")

        # Kenarlık
        p.setPen(QPen(QColor(C["border"]), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(0, 0, w, h, 3, 3)


class DualCameraStatus(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self.setFixedHeight(50)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)

        self._leds: dict[int, LedIndicator] = {}
        self._bars: dict[int, FpsBar] = {}
        self._lbls: dict[int, QLabel] = {}

        for idx, (label, color) in enumerate([("CAM A", CAM_A_COLOR),
                                               ("CAM B", CAM_B_COLOR)]):
            row = QHBoxLayout()
            row.setSpacing(6)
            row.setContentsMargins(0, 0, 0, 0)

            led = LedIndicator(C["text_dim"], size=8)
            self._leds[idx] = led
            row.addWidget(led)

            lbl = QLabel(label)
            lbl.setFixedWidth(44)
            lbl.setStyleSheet(
                f"color:{color};font-size:12px;font-weight:700;"
                f"letter-spacing:1px;font-family:Consolas;background:transparent;")
            self._lbls[idx] = lbl
            row.addWidget(lbl)

            bar = FpsBar()
            self._bars[idx] = bar
            row.addWidget(bar, 1)

            lay.addLayout(row)

    def set_camera_fps(self, cam_idx: int, fps: float, etkin: bool = True) -> None:
        if cam_idx in self._bars:
            self._bars[cam_idx].set_fps(fps, etkin)
        if cam_idx in self._leds:
            if not etkin:
                self._leds[cam_idx].set_state("idle")
            elif fps >= 1:
                self._leds[cam_idx].set_state("active")
            else:
                self._leds[cam_idx].set_state("warn")

    def set_camera_state(self, cam_idx: int, state: str) -> None:
        if cam_idx in self._leds:
            self._leds[cam_idx].set_state(state)


class ThreatCountBadge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._count = 0
        self._pulse = 0.0
        self._up = True
        self.setFixedSize(64, 36)

        self._t = QTimer(self)
        self._t.timeout.connect(self._step)
        self._t.start(30)

    def set_count(self, n: int) -> None:
        self._count = n
        self.update()

    def _step(self):
        if self._count > 0:
            step = 0.06
            self._pulse += step if self._up else -step
            if self._pulse >= 1.0: self._up = False
            if self._pulse <= 0.0: self._up = True
        else:
            self._pulse = 0.0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)

        if self._count > 0:
            col = QColor(C["danger"])
            bg_alpha = int(20 + 25 * self._pulse)
            border_alpha = int(140 + 100 * self._pulse)
        else:
            col = QColor(C["text_dim"])
            bg_alpha = 12
            border_alpha = 60

        p.setBrush(QColor(col.red(), col.green(), col.blue(), bg_alpha))
        p.setPen(QPen(QColor(col.red(), col.green(), col.blue(), border_alpha), 1))
        p.drawRoundedRect(r, 4, 4)

        p.setPen(col)
        p.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter,
                   str(self._count) if self._count > 0 else "—")


class ProgressRing(QWidget):
    def __init__(self, toplam: int = 2, parent=None):
        super().__init__(parent)
        self._toplam = toplam
        self._mevcut = 0
        self._color = QColor(C["accent"])
        self.setFixedSize(48, 48)

    def set_deger(self, mevcut: int, renk: str = None):
        self._mevcut = mevcut
        if renk:
            self._color = QColor(renk)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        r = QRectF(4, 4, w - 8, h - 8)

        p.setPen(QPen(qc(C["border"]), 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(r)

        if self._toplam > 0 and self._mevcut > 0:
            oran = self._mevcut / self._toplam
            span = int(360 * 16 * oran)
            p.setPen(QPen(self._color, 3,
                          Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap))
            p.drawArc(r, 90 * 16, -span)

        p.setPen(self._color)
        p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter,
                   f"{self._mevcut}/{self._toplam}")


class SectionHeader(QWidget):
    def __init__(self, title: str, accent: str = None, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 4)
        lay.setSpacing(8)

        clr = accent or C["text_sec"]
        lbl = QLabel(title.upper())
        lbl.setStyleSheet(
            f"color: {clr}; "
            f"font-size: 10px; font-weight: 700; "
            f"letter-spacing: 1.6px; background: transparent;")

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background: {C['border']}; max-height: 1px;")

        lay.addWidget(lbl)
        lay.addWidget(line, 1)


class CameraCard(QWidget):
    def __init__(self, index: int, isim: str, kamera_id: int,
                 on_id_change=None, parent=None):
        super().__init__(parent)
        self.index = index
        self._on_change = on_id_change
        self._connected = False
        self._build(isim, kamera_id)

    def _build(self, isim: str, kamera_id: int):
        accent = CAM_COLORS.get(self.index, C["accent"])
        self.setStyleSheet(
            f"background: {C['bg_card']}; border: 1px solid {C['border']}; "
            f"border-left: 3px solid {accent}; border-radius: 6px;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)

        self._led = LedIndicator(C["text_dim"], 8)
        top.addWidget(self._led)

        self._lbl_isim = QLabel(isim)
        self._lbl_isim.setStyleSheet(
            f"color: {accent}; font-weight: 700; "
            f"font-size: 12px; background: transparent;")
        top.addWidget(self._lbl_isim, 1)

        lbl_id = QLabel("ID:")
        lbl_id.setStyleSheet(
            f"color: {C['text_sec']}; font-size: 11px; background: transparent;")
        top.addWidget(lbl_id)

        self.spin_id = QSpinBox()
        self.spin_id.setRange(0, 20)
        self.spin_id.setValue(kamera_id)
        self.spin_id.setFixedWidth(55)
        self.spin_id.setToolTip("Kamera ID'sini değiştirin (0-20)")
        self.spin_id.valueChanged.connect(self._id_degisti)
        top.addWidget(self.spin_id)

        self._btn_conn = QPushButton("⟳")
        self._btn_conn.setObjectName("btn_icon")
        self._btn_conn.setToolTip("Yeniden bağlan")
        self._btn_conn.setStyleSheet(
            f"QPushButton{{background:{C['bg_card']};border:1px solid {C['border']};"
            f"border-radius:4px;color:{accent};font-size:14px;"
            f"min-width:28px;max-width:28px;min-height:28px;max-height:28px;}}"
            f"QPushButton:hover{{border-color:{accent};color:white;}}")
        self._btn_conn.clicked.connect(self._yeniden_baglan)
        top.addWidget(self._btn_conn)

        lay.addLayout(top)

        self._lbl_durum = TelemetryLabel("Durum", "Bağlanmaya çalışılıyor…",
                                          C["text_dim"])
        lay.addWidget(self._lbl_durum)

    def set_connected(self, ok: bool, fps: float = 0.0):
        self._connected = ok
        if ok:
            self._led.set_color(C["success"])
            self._lbl_durum.setValue(f"Bağlı  ·  {fps:.1f} FPS")
            self._lbl_durum.setStyleSheet(
                f"color: {C['success']}; font-size: 10px; "
                f"font-family: monospace; background: transparent;")
        else:
            self._led.set_color(C["danger"], blink=True)
            self._lbl_durum.setValue("Bağlantı kesildi")
            self._lbl_durum.setStyleSheet(
                f"color: {C['danger']}; font-size: 10px; "
                f"font-family: monospace; background: transparent;")

    def _id_degisti(self, yeni_id: int):
        if self._on_change:
            self._on_change(self.index, yeni_id)

    def _yeniden_baglan(self):
        if self._on_change:
            self._on_change(self.index, self.spin_id.value())
