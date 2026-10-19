import config
from pathlib import Path

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSpinBox,
    QFrame, QFileDialog, QSizePolicy
)

from .styles import C, CAM_COLORS
from .widgets import SectionHeader, LedIndicator, FpsBar


class KameraKart(QWidget):
    id_degisti = pyqtSignal(int, int)
    model_degisti = pyqtSignal(int, str)
    etkin_degisti = pyqtSignal(int, bool)

    def __init__(self, kamera_idx: int, parent=None):
        super().__init__(parent)
        self._idx = kamera_idx
        self._kamera = (config.KAMERALAR[kamera_idx]
                        if kamera_idx < len(config.KAMERALAR) else {})
        self._ayar = (config.KAMERA_AYARLAR[kamera_idx]
                        if kamera_idx < len(config.KAMERA_AYARLAR) else {})
        self._accent = CAM_COLORS.get(kamera_idx, C["accent"])
        self._cam_lbl = "A" if kamera_idx == 0 else "B"
        # YOLO numarası kamera indeksine göre sabit
        self._yolo_no = f"YOLO{kamera_idx + 1}"
        self._ui_kur()

    def _ui_kur(self) -> None:
        self.setStyleSheet(
            f"background:{C['bg_card']};border:1px solid {C['border']};"
            f"border-left:4px solid {self._accent};"
            "border-radius:6px;")

        outer = QVBoxLayout(self)
        outer.setSpacing(5)
        outer.setContentsMargins(10, 8, 10, 8)

        # Başlık: [CAM A] ● [> AÇ / ■ KAPAT]
        top = QHBoxLayout()
        top.setSpacing(6)

        cam_badge = QLabel(f"CAM {self._cam_lbl}")
        cam_badge.setFixedSize(46, 22)
        cam_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cam_badge.setStyleSheet(
            f"background:{self._accent}22;border:1px solid {self._accent}66;"
            f"border-radius:3px;color:{self._accent};font-size:10px;"
            f"font-weight:800;letter-spacing:1px;font-family:Consolas;")
        top.addWidget(cam_badge)

        self._led = LedIndicator(C["text_dim"], size=8)
        top.addWidget(self._led)

        top.addStretch(1)

        etkin_baslangic = self._kamera.get("etkin", False)
        self._toggle_btn = QPushButton(
            "■ KAPAT" if etkin_baslangic else "▶ AÇ")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(etkin_baslangic)
        self._toggle_btn.setFixedHeight(26)
        self._toggle_btn.setMinimumWidth(70)
        self._toggle_btn.setStyleSheet(
            f"QPushButton{{background:#1a0a0a;color:#ff5252;"
            f"border:1px solid #5c1a1a;border-radius:4px;"
            f"font-size:11px;font-weight:700;padding:0 10px;}}"
            f"QPushButton:checked{{background:#0a2a0a;color:#00e676;"
            f"border-color:#1a5c1a;}}"
            f"QPushButton:hover{{border-color:{self._accent};}}")
        self._toggle_btn.clicked.connect(self._toggle_etkin)
        top.addWidget(self._toggle_btn)

        outer.addLayout(top)

        # Ayırıcı çizgi
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{C['border']};")
        outer.addWidget(sep)

        # CAM ID satırı
        id_row = QHBoxLayout()
        id_row.setSpacing(6)

        lbl_id = QLabel("CAM ID")
        lbl_id.setFixedWidth(52)
        lbl_id.setStyleSheet(
            f"color:{C['text_dim']};font-size:11px;background:transparent;")
        self._id_spin = QSpinBox()
        self._id_spin.setRange(0, 99)
        self._id_spin.setValue(self._kamera.get("id", self._idx))
        self._id_spin.setFixedHeight(24)
        self._id_spin.valueChanged.connect(self._on_id_degisti)
        id_row.addWidget(lbl_id)
        id_row.addWidget(self._id_spin, 1)
        outer.addLayout(id_row)

        # Model satırı: [YOLO1] dosya.pt [...]
        model_row = QHBoxLayout()
        model_row.setSpacing(5)

        self._model_led = LedIndicator(size=7)
        mevcut = self._kamera.get("model", config.MODEL_NESNE_YOLU)
        self._model_led.set_state(
            "active" if mevcut and Path(mevcut).exists() else "error")
        model_row.addWidget(self._model_led)

        # YOLO rozeti - sabit, kamera indeksine göre
        yolo_badge = QLabel(self._yolo_no)
        yolo_badge.setFixedSize(46, 18)
        yolo_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        yolo_badge.setStyleSheet(
            f"background:{self._accent}22;border:1px solid {self._accent}55;"
            f"border-radius:3px;color:{self._accent};font-size:9px;"
            f"font-weight:700;letter-spacing:0.5px;font-family:Consolas;")
        model_row.addWidget(yolo_badge)

        self._model_lbl = QLabel(Path(mevcut).name if mevcut else "—")
        self._model_lbl.setStyleSheet(
            f"color:{C['text_sec']};font-size:11px;background:transparent;")
        self._model_lbl.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        model_row.addWidget(self._model_lbl, 1)

        btn = QPushButton("…")
        btn.setFixedSize(24, 24)
        btn.setStyleSheet(
            f"QPushButton{{background:{C['bg_input']};color:{C['text_sec']};"
            f"border:1px solid {C['border']};border-radius:4px;font-size:13px;}}"
            f"QPushButton:hover{{color:{self._accent};border-color:{self._accent};}}")
        btn.clicked.connect(self._model_sec)
        model_row.addWidget(btn)

        outer.addLayout(model_row)

        # FPS Bar
        fps_row = QHBoxLayout()
        fps_row.setSpacing(6)

        fps_lbl = QLabel("FPS")
        fps_lbl.setFixedWidth(28)
        fps_lbl.setStyleSheet(
            f"color:{C['text_dim']};font-size:10px;background:transparent;")
        self._fps_bar = FpsBar()
        fps_row.addWidget(fps_lbl)
        fps_row.addWidget(self._fps_bar, 1)
        outer.addLayout(fps_row)

    # Slot'lar
    def _toggle_etkin(self, checked: bool) -> None:
        self._kamera["etkin"] = checked
        self._ayar["ETKIN"] = checked
        self._toggle_btn.setText("■ KAPAT" if checked else "▶ AÇ")
        # Kamera açılırken "BAĞLANIYOR..." göster, thread hazır olunca FPS gelir
        self._led.set_state("warn" if checked else "idle")
        if not checked:
            self._fps_bar.set_fps(0.0, etkin=False)
        # Sinyal async - UI bloke olmaz
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.etkin_degisti.emit(self._idx, checked))

    def _on_id_degisti(self, val: int) -> None:
        if self._idx < len(config.KAMERALAR):
            config.KAMERALAR[self._idx]["id"] = val
        self.id_degisti.emit(self._idx, val)

    def _model_sec(self) -> None:
        yol, _ = QFileDialog.getOpenFileName(
            self, "Model Dosyası Seç", "models/",
            "Model Dosyaları (*.pt *.onnx *.engine *.tflite *.torchscript)")
        if not yol:
            return
        if self._idx < len(config.KAMERALAR):
            config.KAMERALAR[self._idx]["model"] = yol
        if self._idx < len(config.KAMERA_AYARLAR):
            config.KAMERA_AYARLAR[self._idx]["MODEL_YOLU"] = yol
        self._model_lbl.setText(Path(yol).name)
        self._model_led.set_state("active")
        self.model_degisti.emit(self._idx, yol)

    def fps_guncelle(self, fps: float) -> None:
        etkin = self._ayar.get("ETKIN", False)
        if not etkin:
            self._fps_bar.set_fps(0.0, etkin=False)
            return
        self._fps_bar.set_fps(fps, etkin=True)
        self._led.set_state("active" if fps > 0 else "warn")

    def durum_guncelle(self, bagli: bool) -> None:
        self._led.set_state("active" if bagli else "error")


class KameraYonetici(QWidget):
    kamera_id_degisti = pyqtSignal(int, int)
    model_degisti = pyqtSignal(int, str)
    kamera_etkin_degisti = pyqtSignal(int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(190)
        self.setMaximumWidth(260)
        self._kartlar: list[KameraKart] = []
        self._ui_kur()

    def _ui_kur(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 8, 6, 6)
        outer.setSpacing(8)

        outer.addWidget(SectionHeader("KAMERA & MODEL"))

        hint = QLabel("A = CYAN  ·  B = AMBER")
        hint.setStyleSheet(
            f"color:{C['text_dim']};font-size:10px;font-family:Consolas;"
            f"letter-spacing:0.5px;background:transparent;")
        outer.addWidget(hint)

        self._kart_alan = QVBoxLayout()
        self._kart_alan.setSpacing(8)
        outer.addLayout(self._kart_alan)

        for i in range(len(config.KAMERALAR)):
            kart = KameraKart(i)
            kart.id_degisti.connect(self.kamera_id_degisti)
            kart.model_degisti.connect(self.model_degisti)
            kart.etkin_degisti.connect(self.kamera_etkin_degisti)
            self._kartlar.append(kart)
            self._kart_alan.addWidget(kart)

        outer.addStretch()

    def fps_guncelle(self, kamera_idx: int, fps: float) -> None:
        if kamera_idx < len(self._kartlar):
            self._kartlar[kamera_idx].fps_guncelle(fps)

    def durum_guncelle(self, kamera_idx: int, bagli: bool) -> None:
        if kamera_idx < len(self._kartlar):
            self._kartlar[kamera_idx].durum_guncelle(bagli)
