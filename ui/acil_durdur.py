
from PyQt6.QtCore import (Qt, QTimer, pyqtSignal,
                              QRectF)
from PyQt6.QtGui import (QPainter, QColor, QPen, QFont,
                              QRadialGradient, QPainterPath)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                              QPushButton, QSizePolicy)



class AcilDurdurButon(QWidget):

    acil_durdur = pyqtSignal()  # tetiklenince
    acil_reset = pyqtSignal()  # sıfırlanınca

    def __init__(self, parent=None):
        super().__init__(parent)
        self._aktif = False
        self._pulse = 0.0
        self._up = True
        self._blink = False
        self._blink_on = True

        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Yavaş pulsing animasyonu (hazır durumu)
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_adim)
        self._pulse_timer.start(30)

        # Hızlı blink (aktif durum)
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink_adim)

    # Animasyon
    def _pulse_adim(self):
        if self._blink: return
        self._pulse += 0.025 if self._up else -0.025
        if self._pulse >= 1.0: self._up = False
        if self._pulse <= 0.0: self._up = True
        self.update()

    def _blink_adim(self):
        self._blink_on = not self._blink_on
        self.update()

    # Durum yönetimi
    def tetikle(self):
        self._aktif = True
        self._blink = True
        self._blink_timer.start(200)  # hızlı blink
        self.update()
        self.acil_durdur.emit()

    def sifirla(self):
        self._aktif = False
        self._blink = False
        self._blink_on = True
        self._blink_timer.stop()
        self.update()
        self.acil_reset.emit()

    @property
    def aktif(self) -> bool:
        return self._aktif

    # Çizim
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if self._aktif:
            # AKTİF - parlak kırmızı (blink)
            alpha = 255 if self._blink_on else 120
            bg_col = QColor(180, 10, 30, alpha)
            border_col = QColor(255, 40, 60)
            text_col = QColor(255, 220, 220)
        else:
            # HAZIR - koyu kırmızı, yavaş pulsing
            glow = int(60 + 60 * self._pulse)
            bg_col = QColor(100, 8, 20, 200)
            border_col = QColor(200, 30, 50, glow + 80)
            text_col = QColor(255, 100, 110)

        # Arka plan
        path = QPainterPath()
        path.addRoundedRect(QRectF(1, 1, w - 2, h - 2), 8, 8)
        p.fillPath(path, bg_col)

        # Glow border
        if self._aktif and self._blink_on:
            glow_grad = QRadialGradient(w / 2, h / 2, w * 0.7)
            glow_grad.setColorAt(0, QColor(255, 40, 60, 40))
            glow_grad.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillPath(path, glow_grad)

        p.setPen(QPen(border_col, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(1, 1, w - 2, h - 2, 8, 8)

        # İkon + metin
        if self._aktif:
            ikon = "⛔"
            satir1 = "ACİL DURDUR"
            satir2 = "AKTİF — Sıfırlamak için tıkla"
        else:
            ikon = "⚠"
            satir1 = "ACİL DURDUR"
            satir2 = "Basmak için tıkla"

        p.setPen(text_col)
        p.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        p.drawText(QRectF(0, 8, w, h // 2),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                   f"{ikon}  {satir1}")

        p.setFont(QFont("Segoe UI", 11))
        p.setPen(QColor(text_col.red(), text_col.green(), text_col.blue(), 160))
        p.drawText(QRectF(0, h // 2, w, h // 2 - 6),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                   satir2)

    # Tıklama
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._aktif:
                self.sifirla()
            else:
                self.tetikle()


class AcilDurdurOverlay(QWidget):

    kapatildi = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")
        self._alpha = 0.0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._fade_in)
        self._blink_on = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink)

        self._ui_kur()
        self.hide()

    def _ui_kur(self):
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._lbl_ana = QLabel("⛔  ACİL DURDUR  ⛔")
        self._lbl_ana.setStyleSheet(
            "color: white; font-size: 48px; font-weight: 900; "
            "letter-spacing: 4px; background: transparent;")
        self._lbl_ana.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._lbl_alt = QLabel("TÜM MOTORLAR DURDURULDU")
        self._lbl_alt.setStyleSheet(
            "color: rgba(255,180,180,220); font-size: 20px; "
            "letter-spacing: 2px; background: transparent;")
        self._lbl_alt.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_reset = QPushButton("  SİSTEMİ SIFIRLA  ")
        btn_reset.setStyleSheet(
            f"QPushButton {{ background: #1a0008; border: 2px solid #ff2d55; "
            f"border-radius: 8px; color: #ff2d55; font-size: 16px; "
            f"font-weight: 700; letter-spacing: 2px; padding: 14px 48px; }}"
            f"QPushButton:hover {{ background: #2a0010; color: white; }}")
        btn_reset.clicked.connect(self._kapat)

        lay.addStretch()
        lay.addWidget(self._lbl_ana)
        lay.addSpacing(12)
        lay.addWidget(self._lbl_alt)
        lay.addSpacing(32)
        lay.addWidget(btn_reset, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addStretch()

    def goster(self):
        self.show()
        self.raise_()
        self._alpha = 0.0
        self._anim_timer.start(16)
        self._blink_timer.start(500)

    def _fade_in(self):
        self._alpha = min(1.0, self._alpha + 0.06)
        self.update()
        if self._alpha >= 1.0:
            self._anim_timer.stop()

    def _blink(self):
        self._blink_on = not self._blink_on
        self.update()

    def _kapat(self):
        self._blink_timer.stop()
        self.hide()
        self.kapatildi.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Yarı saydam kırmızı arka plan (fade-in)
        alpha = int(200 * self._alpha)
        p.fillRect(0, 0, w, h, QColor(100, 0, 10, alpha))

        # Titreyen ince border
        if self._blink_on:
            p.setPen(QPen(QColor(255, 40, 60, 180), 4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(4, 4, w - 8, h - 8)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._kapat()
