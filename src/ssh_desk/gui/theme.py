"""Theme definitions (dark/light) rendered as a Qt stylesheet."""

DARK = {
    "bg": "#14161b", "surface": "#1c1f26", "surface2": "#232730", "border": "#2e333d",
    "text": "#e7eaf0", "text_dim": "#9aa3b2", "accent": "#4f8cff", "accent_hover": "#6b9eff",
    "accent_text": "#ffffff", "ok": "#3ddc84", "warn": "#ffb454", "danger": "#ff5d5d",
    "selection": "#2b3a55", "input_bg": "#20242c", "tooltip_bg": "#101216",
}

LIGHT = {
    "bg": "#f3f5f9", "surface": "#ffffff", "surface2": "#eef1f6", "border": "#d8dee9",
    "text": "#1d2330", "text_dim": "#6a7482", "accent": "#2563eb", "accent_hover": "#3b76f2",
    "accent_text": "#ffffff", "ok": "#16a34a", "warn": "#d97706", "danger": "#dc2626",
    "selection": "#d3e0fb", "input_bg": "#ffffff", "tooltip_bg": "#1d2330",
}


def build_qss(p: dict) -> str:
    return f"""
* {{ font-size: 13px; }}
QMainWindow, QDialog {{ background: {p['bg']}; color: {p['text']}; }}
QWidget {{ color: {p['text']}; }}
QLabel {{ background: transparent; }}
QLabel[role="dim"] {{ color: {p['text_dim']}; }}
QLabel[role="title"] {{ font-size: 17px; font-weight: 600; }}
QLabel[role="subtitle"] {{ font-size: 12px; color: {p['text_dim']}; }}

QFrame[role="card"] {{
    background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 10px;
}}
QFrame[role="statCard"] {{
    background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 10px;
}}
QLabel[role="statValue"] {{ font-size: 26px; font-weight: 700; color: {p['accent']}; background: transparent; }}

QSidebar QListWidget, QListWidget[role="sidebar"] {{
    background: {p['surface']}; border: none; padding: 6px 4px; outline: 0;
}}
QListWidget[role="sidebar"]::item {{
    color: {p['text_dim']}; padding: 9px 14px; border-radius: 8px; margin: 2px 6px;
}}
QListWidget[role="sidebar"]::item:selected {{ background: {p['selection']}; color: {p['text']}; }}
QListWidget[role="sidebar"]::item:hover {{ background: {p['surface2']}; }}

QPushButton {{
    background: {p['surface2']}; color: {p['text']}; border: 1px solid {p['border']};
    border-radius: 7px; padding: 7px 14px;
}}
QPushButton:hover {{ background: {p['border']}; }}
QPushButton:disabled {{ color: {p['text_dim']}; background: {p['surface']}; }}
QPushButton[role="primary"] {{ background: {p['accent']}; color: {p['accent_text']}; border: none; font-weight: 600; }}
QPushButton[role="primary"]:hover {{ background: {p['accent_hover']}; }}
QPushButton[role="danger"] {{ background: transparent; color: {p['danger']}; border: 1px solid {p['danger']}; }}
QPushButton[role="danger"]:hover {{ background: {p['danger']}; color: #fff; }}
QPushButton[role="flat"] {{ background: transparent; border: none; color: {p['text_dim']}; padding: 6px; }}
QPushButton[role="flat"]:hover {{ color: {p['text']}; background: {p['surface2']}; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
    background: {p['input_bg']}; color: {p['text']}; border: 1px solid {p['border']};
    border-radius: 7px; padding: 6px 9px; selection-background-color: {p['selection']};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {p['accent']};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {p['surface']}; color: {p['text']}; border: 1px solid {p['border']};
    selection-background-color: {p['selection']};
}}

QTableWidget {{
    background: {p['surface']}; alternate-background-color: {p['surface2']};
    border: 1px solid {p['border']}; border-radius: 8px; gridline-color: transparent;
    selection-background-color: {p['selection']}; selection-color: {p['text']};
}}
QHeaderView::section {{
    background: {p['surface2']}; color: {p['text_dim']}; border: none;
    padding: 8px 10px; font-weight: 600;
}}
QTableWidget::item {{ padding: 6px; border: none; }}
QTableWidget::item:selected {{ background: {p['selection']}; }}

QTabWidget::pane {{ border: 1px solid {p['border']}; border-radius: 8px; background: {p['surface']}; }}
QTabBar::tab {{
    background: transparent; color: {p['text_dim']}; padding: 8px 16px;
    border: 1px solid transparent; border-bottom: none;
}}
QTabBar::tab:selected {{ color: {p['text']}; border: 1px solid {p['border']}; background: {p['surface']}; border-radius: 6px; }}

QToolTip {{ background: {p['tooltip_bg']}; color: {p['text']}; border: 1px solid {p['border']}; padding: 5px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {p['border']}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {p['text_dim']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: {p['border']}; border-radius: 5px; min-width: 30px; }}

QStatusBar {{ background: {p['surface']}; color: {p['text_dim']}; border-top: 1px solid {p['border']}; }}
QMenuBar {{ background: {p['surface']}; }}
QMenu {{ background: {p['surface']}; border: 1px solid {p['border']}; padding: 4px; }}
QMenu::item {{ padding: 6px 24px; border-radius: 5px; }}
QMenu::item:selected {{ background: {p['selection']}; }}
QProgressBar {{
    background: {p['surface2']}; border: none; border-radius: 4px; height: 8px; text-align: center;
}}
QProgressBar::chunk {{ background: {p['accent']}; border-radius: 4px; }}
QCheckBox, QRadioButton {{ background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; }}
QGroupBox {{
    border: 1px solid {p['border']}; border-radius: 8px; margin-top: 12px;
    background: {p['surface']}; font-weight: 600;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {p['text_dim']}; }}
"""
