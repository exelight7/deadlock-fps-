"""Local styling for the English Crosshair workspace; aligned with the shared Toolbox palette."""
from .core import ASSETS

STYLE='''
QWidget {font-family:"Segoe UI","Noto Sans",sans-serif;font-size:13px;color:#e8eff3;}
QLabel {background:transparent;}
QLabel#workspaceTitle {font-size:27px;font-weight:700;color:#f4f6f3;}
QLabel#workspaceEyebrow {font-size:10px;color:#e9c48c;font-weight:700;letter-spacing:2px;}
QLabel#subtitle {color:#9fb3c0;font-size:12px;}
QLabel#cardtitle {color:#f0f5f6;font-size:14px;font-weight:600;}
QLabel#previewMode {color:#aeeddc;background:#13332f;border:1px solid #2f6e63;border-radius:7px;padding:5px 9px;font-size:11px;}
QFrame#card {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #14212b,stop:1 #0f1a22);border:1px solid #223441;border-top-color:#30475a;border-radius:14px;}
QFrame#crosshairActions {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #16242e,stop:1 #101b23);border:1px solid #2b4150;border-radius:15px;}
QPushButton {background:#17252f;border:1px solid #2a3e4b;border-radius:9px;padding:9px 12px;font-size:12px;font-weight:600;}
QPushButton:hover {background:#203441;border-color:#bfa172;color:#ffffff;}
QPushButton:pressed {background:#2a3328;border-color:#e9c48c;}
QPushButton#primary {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #f6dcae,stop:1 #deb679);color:#191e21;border:1px solid #f0cf9b;padding:11px 15px;font-size:12px;font-weight:700;}
QPushButton#primary:hover {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #fdeccb,stop:1 #e9c48c);border-color:#fdeccb;color:#191e21;}
QPushButton#primary:pressed {background:#d4ab6f;border-color:#d4ab6f;}
QPushButton#quiet {background:transparent;border:1px solid #2a3e4b;color:#afc5cd;padding:7px 10px;font-size:11px;}
QPushButton#quiet:hover {background:#17252f;border-color:#bfa172;color:#ffffff;}
QPushButton:disabled {color:#5d7280;background:#111b23;border-color:#1f303c;}
QPushButton#primary:disabled {background:#1a2832;border-color:#2a3e4b;color:#74899a;}
QComboBox,QLineEdit,QDoubleSpinBox,QPlainTextEdit {background:#0c151c;border:1px solid #263a47;border-radius:9px;padding:8px 10px;selection-background-color:#5d5237;color:#e8eff3;}
QComboBox:hover,QLineEdit:hover,QDoubleSpinBox:hover {border-color:#3b5564;}
QComboBox:focus,QLineEdit:focus,QDoubleSpinBox:focus {border-color:#e9c48c;}
QComboBox {padding-right:28px;min-height:20px;}
QComboBox::drop-down {width:26px;border:0;background:transparent;}
QComboBox::down-arrow {image:url("ARROW");width:12px;height:8px;}
QComboBox QAbstractItemView {background:#121e27;border:1px solid #2b4150;color:#e8eff3;selection-background-color:#3a3a2a;outline:0;}
QDoubleSpinBox {font-family:"Segoe UI","Noto Sans",sans-serif;font-size:12px;padding:5px 8px;}
QTabWidget::pane {border:0;background:transparent;}
QTabBar {background:transparent;}
QTabBar::tab {background:#101b23;color:#93a7b4;border:1px solid #223441;padding:10px 16px;margin-bottom:9px;min-width:60px;font-weight:600;}
QTabBar::tab:first {border-top-left-radius:9px;border-bottom-left-radius:9px;}
QTabBar::tab:last {border-top-right-radius:9px;border-bottom-right-radius:9px;}
QTabBar::tab:selected {background:#2b2a1f;color:#f7deb2;border-color:#8f8259;}
QTabBar::tab:hover {color:#ffffff;}
QSlider {background:transparent;min-height:24px;}
QSlider::groove:horizontal {height:4px;background:#1c2d39;border-radius:2px;}
QSlider::sub-page:horizontal {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #c79d5f,stop:1 #f3d6a4);border-radius:2px;}
QSlider::handle:horizontal {width:10px;margin:-6px 0;background:#fff3dc;border:3px solid #c9a064;border-radius:8px;}
QSlider::handle:horizontal:hover {background:#ffffff;border-color:#f3d6a4;}
QCheckBox {spacing:9px;padding:8px 0;}
QScrollArea {background:transparent;border:0;}
QMenu {background:#121e27;color:#e8eff3;border:1px solid #2f4553;padding:6px;}
QMenu::item {padding:9px 18px;}
QMenu::item:selected {background:#3a3a2a;color:#f8e4c1;}
'''.replace('ARROW',(ASSETS/'chevron-down.svg').as_posix())
