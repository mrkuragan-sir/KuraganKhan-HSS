from PyQt6.QtGui import QColor


def qc(hex_str: str, alpha: int = 255) -> QColor:
    col = QColor(hex_str)
    col.setAlpha(alpha)
    return col


SP = {
    "xs" : 8,
    "sm" : 16,
    "md" : 24,
    "lg" : 32,
    "xl" : 48,
    "2xl": 80,
}

C = {
    # Arka planlar
    "bg_deep" : "#050810",  # En derin - lacivert-siyah
    "bg_panel" : "#0b1120",  # Panel yüzeyi
    "bg_card" : "#101828",  # Kart / içerik yüzeyi
    "bg_input" : "#080e1c",  # Giriş alanı
    "bg_overlay" : "#162038",  # Hover / seçili

    # Kenarlıklar
    "border" : "#18253a",  # Pasif
    "border_act" : "#00c8f0",  # Aktif - parlak cyan
    "border_dim" : "#0d1828",  # Soluk

    # Vurgu renkleri
    "accent" : "#00e5ff",  # Birincil - elektrik cyan
    "success" : "#00e676",  # Başarı - yeşil
    "danger" : "#ff2d55",  # Tehlike - kırmızı
    "warning" : "#ff9f0a",  # Uyarı - amber
    "info" : "#5e6ad2",  # Bilgi - indigo

    # Semantik arka plan tonları (dim) - L99
    "accent_dim" : "#001a20",  # Cyan arka plan
    "success_dim": "#001a0f",  # Yeşil arka plan
    "danger_dim" : "#1a0008",  # Kırmızı arka plan
    "warning_dim": "#1a0f00",  # Amber arka plan
    "info_dim" : "#0a0d2a",  # İndigo arka plan

    # Metin hiyerarşisi (tinted, saf beyaz yok)
    "text_pri" : "#e4f0fa",  # %90 - birincil metin (mavi-beyaz tint)
    "text_sec" : "#637799",  # %55 - ikincil metin
    "text_dim" : "#3b4d66",  # %30 - üçüncü derece / devre dışı
    "text_mono" : "#9dcfe8",  # Telemetri / mono veri

    # Hedef durum renkleri
    "target_pri" : "#ff9f0a",  # Öncelikli - amber
    "target_nrm" : "#ff2d55",  # Düşman - kırmızı
    "target_ally": "#00e676",  # Dost - yeşil
    "target_done": "#3b4d66",  # İmha - gri
}

# DUAL-CAMERA AKSANLAR
CAM_A_COLOR = C["accent"]  # Kamera A - elektrik cyan  #00e5ff
CAM_B_COLOR = C["warning"]  # Kamera B - amber          #ff9f0a

CAM_COLORS = {
    0: CAM_A_COLOR,
    1: CAM_B_COLOR,
}

# GLOW YOĞUNLUK SABİTLERİ (alpha 0-255)
GLOW = {
    "off" : 0,  # kapalı
    "dim" : 35,  # pasif LED halo
    "idle" : 60,  # boşta LED halo
    "normal": 90,  # aktif LED halo
    "strong": 140,  # kilit / tehlike halo
    "max" : 200,  # kritik durum
}

# FPS RENK EŞİKLERİ
FPS_OK = "#00c87a"  # ≥ 25 fps
FPS_WARN = "#ffa500"  # ≥ 15 fps
FPS_BAD = "#ff3c3c"  # < 15 fps

def fps_color(fps: float) -> str:
    if fps >= 25: return FPS_OK
    if fps >= 15: return FPS_WARN
    return FPS_BAD

ANIM = {
    "micro" : 150,  # renk / opaklık
    "normal" : 300,  # transform / yükseklik
    "slow" : 400,  # sayfa geçişi
}

# GLOBAL QSS
GLOBAL_QSS = f"""
* {{
    font-family: 'Segoe UI', 'Inter', 'SF Pro Text', system-ui, sans-serif;
    font-size: 13px;
    color: {C['text_pri']};
    outline: none;
}}

QMainWindow {{
    background: {C['bg_deep']};
}}

QDialog {{
    background: {C['bg_panel']};
}}

QWidget {{
    background: transparent;
}}

QLabel {{
    background: transparent;
}}

.TacticalPanel {{
    background: {C['bg_panel']};
    border: 1px solid {C['border']};
    border-radius: 8px;
}}

.TacticalCard {{
    background: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: {SP['xs']}px;
}}

QGroupBox {{
    background: {C['bg_panel']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    margin-top: 22px;
    padding-top: {SP['sm']}px;
    padding-left: {SP['xs']}px;
    padding-right: {SP['xs']}px;
    padding-bottom: {SP['xs']}px;
    font-size: 10px;
    font-weight: 600;
    color: {C['accent']};
    letter-spacing: 1px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 2px;
    background: {C['bg_panel']};
    padding: 2px {SP['xs']}px;
    color: {C['accent']};
    border-radius: 3px;
    text-transform: uppercase;
}}

QPushButton {{
    background: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    color: {C['text_sec']};
    padding: 6px {SP['sm']}px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.6px;
    min-height: 32px;
}}

QPushButton:hover {{
    background: {C['bg_overlay']};
    border-color: {C['border_act']};
    color: {C['accent']};
}}

QPushButton:pressed {{
    background: {C['bg_input']};
    border-color: {C['accent']};
    color: {C['text_pri']};
}}

QPushButton:disabled {{
    background: {C['bg_card']};
    border-color: {C['border_dim']};
    color: {C['text_dim']};
}}

QPushButton#btn_start {{
    background: #063d20;
    border: 1px solid #0a6030;
    color: {C['success']};
    font-weight: 700;
    letter-spacing: 0.8px;
}}
QPushButton#btn_start:hover {{
    background: #0a5028;
    border-color: {C['success']};
}}
QPushButton#btn_start:pressed {{
    background: #042810;
}}

QPushButton#btn_stop {{
    background: #3d0615;
    border: 1px solid #6b0a22;
    color: {C['danger']};
    font-weight: 700;
    letter-spacing: 0.8px;
}}
QPushButton#btn_stop:hover {{
    background: #4d0820;
    border-color: {C['danger']};
}}
QPushButton#btn_stop:pressed {{
    background: #2d040f;
}}

QPushButton#btn_icon {{
    background: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    padding: 6px;
    min-width: 30px;  max-width: 30px;
    min-height: 30px; max-height: 30px;
    font-size: 14px;
    color: {C['text_sec']};
}}
QPushButton#btn_icon:hover {{
    border-color: {C['border_act']};
    color: {C['accent']};
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {C['bg_input']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    color: {C['text_pri']};
    padding: 5px {SP['xs']}px;
    min-height: 28px;
    selection-background-color: {C['accent']};
    selection-color: {C['bg_deep']};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {C['border_act']};
}}

QComboBox:focus {{ border-color: {C['border_act']}; }}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
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
}}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: {C['bg_card']};
    border: none;
    width: 16px;
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

QScrollBar:horizontal {{
    background: {C['bg_deep']};
    height: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {C['border']};
    border-radius: 3px;
}}

QListWidget {{
    background: {C['bg_input']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    alternate-background-color: {C['bg_card']};
}}
QListWidget::item {{
    padding: 6px {SP['xs']}px;
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
    background: {C['bg_input']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    color: {C['success']};
    font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    padding: 6px;
    line-height: 1.6;
}}

QFrame[frameShape="4"],
QFrame[frameShape="5"] {{
    color: {C['border']};
    background: {C['border']};
    max-height: 1px;
    border: none;
}}

QToolBar {{
    background: {C['bg_panel']};
    border-bottom: 1px solid {C['border']};
    spacing: {SP['xs']}px;
    padding: 6px {SP['sm']}px;
}}

QStatusBar {{
    background: {C['bg_panel']};
    border-top: 1px solid {C['border']};
    color: {C['text_sec']};
    font-size: 11px;
    padding: 0 {SP['xs']}px;
}}
QStatusBar QLabel {{
    color: {C['text_sec']};
    font-size: 11px;
    padding: 2px {SP['xs']}px;
}}

QSlider::groove:horizontal {{
    background: {C['bg_input']};
    border: 1px solid {C['border']};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {C['accent']};
    border: none;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{ background: {C['text_pri']}; }}
QSlider::sub-page:horizontal {{
    background: {C['accent']};
    border-radius: 2px;
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
    padding: 6px {SP['sm']}px;
    color: {C['text_sec']};
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.4px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}
QTabBar::tab:selected {{
    background: {C['bg_panel']};
    color: {C['accent']};
    border-top: 2px solid {C['accent']};
}}
QTabBar::tab:hover:!selected {{
    color: {C['text_pri']};
    background: {C['bg_card']};
}}

QSplitter::handle {{ background: {C['border']}; }}
QSplitter::handle:hover {{ background: {C['border_act']}; }}
QSplitter::handle:horizontal {{ width: 3px; }}
QSplitter::handle:vertical   {{ height: 3px; }}

QCheckBox {{
    color: {C['text_sec']};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    background: {C['bg_input']};
    border: 1px solid {C['border']};
    border-radius: 3px;
}}
QCheckBox::indicator:checked {{
    background: {C['accent']};
    border-color: {C['accent']};
}}
"""
