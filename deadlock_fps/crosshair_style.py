"""Local styling for the English Crosshair workspace; other pages stay unchanged."""
from .core import ASSETS

STYLE='''
QWidget {font-family:"Segoe UI","Noto Sans",sans-serif;font-size:13px;color:#e9ece7;}
QLabel {background:transparent;}
QLabel#workspaceTitle {font-size:27px;font-weight:700;color:#f3f0e8;}
QLabel#workspaceEyebrow {font-size:10px;color:#d1b48b;font-weight:700;letter-spacing:2px;}
QLabel#subtitle {color:#9aa6a3;font-size:12px;}
QLabel#cardtitle {color:#e5e8e1;font-size:14px;font-weight:600;}
QLabel#previewMode {color:#a8d5bd;background:#1b2c26;border:1px solid #304b40;border-radius:7px;padding:5px 9px;font-size:11px;}
QFrame#card {background:#1a2022;border:1px solid #303a3c;border-radius:14px;}
QFrame#crosshairActions {background:#1a2022;border:1px solid #344044;border-radius:14px;}
QPushButton {background:#242d30;border:1px solid #39474a;border-radius:8px;padding:9px 12px;font-size:12px;font-weight:600;}
QPushButton:hover {background:#2b3739;border-color:#a99471;}
QPushButton#primary {background:#dfbd88;color:#211d16;border:1px solid #dfbd88;padding:11px 15px;font-size:12px;font-weight:700;}
QPushButton#primary:hover {background:#f0d4a9;}
QPushButton#quiet {background:transparent;border:1px solid #3b484a;color:#b2bfba;padding:7px 10px;font-size:11px;}
QPushButton:disabled {color:#65736e;background:#1b2427;border-color:#303c3d;}
QComboBox,QLineEdit,QDoubleSpinBox,QPlainTextEdit {background:#131a1d;border:1px solid #354246;border-radius:8px;padding:8px 10px;selection-background-color:#665337;color:#e4e9e3;}
QComboBox {padding-right:28px;min-height:20px;}
QComboBox::drop-down {width:26px;border:0;background:transparent;}
QComboBox::down-arrow {image:url("ARROW");width:12px;height:8px;}
QComboBox QAbstractItemView {background:#1c2528;color:#e5e9e2;selection-background-color:#3a443c;}
QDoubleSpinBox {font-family:"Segoe UI","Noto Sans",sans-serif;font-size:12px;padding:5px 8px;}
QTabWidget::pane {border:0;background:transparent;}
QTabBar {background:transparent;}
QTabBar::tab {background:#171e20;color:#92a19b;border:1px solid #2d393c;padding:10px 16px;margin-bottom:9px;min-width:60px;}
QTabBar::tab:first {border-top-left-radius:8px;border-bottom-left-radius:8px;}
QTabBar::tab:last {border-top-right-radius:8px;border-bottom-right-radius:8px;}
QTabBar::tab:selected {background:#33362c;color:#ecd4ae;border-color:#716044;}
QTabBar::tab:hover {color:#efe8d8;}
QSlider {background:transparent;min-height:24px;}
QSlider::groove:horizontal {height:4px;background:#334044;border-radius:2px;}
QSlider::sub-page:horizontal {background:#cdb17f;border-radius:2px;}
QSlider::handle:horizontal {width:13px;margin:-5px 0;background:#e9c998;border:2px solid #77664a;border-radius:7px;}
QCheckBox {spacing:9px;padding:8px 0;}
QScrollArea {background:transparent;border:0;}
QMenu {background:#1c2528;color:#e5e9e2;border:1px solid #3e4b4d;padding:6px;}
QMenu::item {padding:9px 18px;}
QMenu::item:selected {background:#3a443c;}
'''.replace('ARROW',(ASSETS/'chevron-down.svg').as_posix())
