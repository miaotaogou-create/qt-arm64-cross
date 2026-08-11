"""深色 Fluent 风格 QSS（对齐 AI Studio 设计稿）。"""
from __future__ import annotations

C = {
    "bg": "#0b0f19",
    "surface": "#111827",
    "surface2": "#1e293b",
    "border": "#334155",
    "border_active": "#14b8a6",
    "text": "#f1f5f9",
    "muted": "#94a3b8",
    "primary": "#10b981",
    "primary_hover": "#34d399",
    "accent": "#14b8a6",
    "ok": "#34d399",
    "warn": "#fbbf24",
    "err": "#f87171",
    "idle": "#64748b",
    "log_bg": "#020617",
    "log_fg": "#e2e8f0",
}


APP_QSS = f"""
QWidget {{
    background-color: {C["bg"]};
    color: {C["text"]};
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}}
QMainWindow, QDialog {{
    background-color: {C["bg"]};
}}
QLabel#Title {{
    font-size: 17px;
    font-weight: 700;
}}
QLabel#Subtitle {{
    color: {C["muted"]};
    font-size: 12px;
}}
QLabel#Muted {{
    color: {C["muted"]};
    font-size: 12px;
}}
QLabel#CardTitle {{
    font-weight: 600;
    font-size: 13px;
}}
QFrame#Card {{
    background-color: {C["surface"]};
    border: 1px solid {C["border"]};
    border-radius: 14px;
}}
QLabel#CardHeadTitle {{
    font-size: 13px;
    font-weight: 700;
    color: {C["text"]};
}}
QLabel#CardHeadRight {{
    font-size: 11px;
    color: {C["muted"]};
}}
QFrame#CardDivider, QFrame#SpecDivider {{
    background-color: {C["border"]};
    border: none;
    max-height: 1px;
}}
QLabel#FormSectionLabel {{
    color: {C["muted"]};
    font-size: 12px;
    font-weight: 500;
    padding-bottom: 2px;
}}
QFrame#PresetCard {{
    background-color: rgba(30, 41, 59, 0.55);
    border: 1px solid {C["border"]};
    border-radius: 12px;
}}
QFrame#PresetCard:hover {{
    background-color: #1e293b;
}}
QFrame#PresetCardActive {{
    background-color: rgba(19, 78, 74, 0.35);
    border: 1px solid rgba(20, 184, 166, 0.65);
    border-radius: 12px;
}}
QLabel#PresetTitle {{
    font-size: 12px;
    font-weight: 700;
    color: {C["text"]};
}}
QLabel#PresetMeta {{
    font-size: 11px;
    color: {C["muted"]};
}}
QLabel#PresetTag {{
    font-size: 10px;
    color: #cbd5e1;
    background-color: #334155;
    border-radius: 4px;
    padding: 2px 6px;
}}
QLabel#PresetTagActive {{
    font-size: 10px;
    color: #042f2e;
    background-color: {C["accent"]};
    border-radius: 4px;
    padding: 2px 6px;
    font-weight: 600;
}}
QLabel#SpecKey {{
    color: {C["muted"]};
    font-size: 12px;
}}
QLabel#SpecVal {{
    color: {C["text"]};
    font-size: 12px;
    font-family: Consolas, "Cascadia Mono", monospace;
}}
QLabel#SpecValAccent {{
    color: {C["accent"]};
    font-size: 12px;
    font-weight: 600;
    font-family: Consolas, "Cascadia Mono", monospace;
}}
QLabel#SpecValOk {{
    color: {C["ok"]};
    font-size: 12px;
    font-weight: 600;
}}
QLineEdit#PathEdit {{
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 12px;
    padding-left: 10px;
}}
QPushButton#EnvPrimary {{
    background-color: #0d9488;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 16px;
    font-weight: 700;
    font-size: 12px;
}}
QPushButton#EnvPrimary:hover {{
    background-color: #14b8a6;
}}
QPushButton#EnvPrimary:disabled {{
    background-color: #1f3a3a;
    color: #64748b;
}}
QPushButton#EnvGhost {{
    background-color: {C["surface2"]};
    border: 1px solid {C["border"]};
    border-radius: 10px;
    padding: 9px 12px;
    font-size: 12px;
}}
QPushButton#EnvAccent {{
    background-color: rgba(20, 184, 166, 0.12);
    color: {C["accent"]};
    border: 1px solid rgba(20, 184, 166, 0.4);
    border-radius: 10px;
    padding: 9px 12px;
    font-size: 12px;
}}
QFrame#ScratchCard {{
    background-color: {C["surface"]};
    border: 1px solid {C["border"]};
    border-radius: 14px;
}}
QToolButton#ScratchToggle {{
    background: transparent;
    border: none;
    color: {C["text"]};
    font-weight: 700;
    font-size: 12px;
    padding: 0;
    text-align: left;
}}

QFrame#Chrome {{
    background-color: {C["surface"]};
    border-bottom: 1px solid {C["border"]};
}}
QFrame#TitleBar {{
    background-color: #020617;
    border-bottom: 1px solid {C["border"]};
}}
QFrame#MainHeader {{
    background-color: {C["surface"]};
}}
QLabel#TitleLogo {{
    background-color: rgba(20, 184, 166, 0.2);
    color: {C["accent"]};
    border-radius: 5px;
    font-size: 10px;
    font-weight: 700;
}}
QLabel#TitleAppName {{
    color: #e2e8f0;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#TitleVerBadge {{
    color: {C["accent"]};
    background-color: rgba(20, 184, 166, 0.1);
    border: 1px solid rgba(20, 184, 166, 0.35);
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 10px;
    font-family: Consolas, monospace;
}}
QLabel#TitleCenter {{
    color: #94a3b8;
    font-size: 11px;
}}
QLabel#TitleDotOk {{
    color: {C["ok"]};
    font-size: 10px;
}}
QLabel#TitleDotWarn {{
    color: {C["warn"]};
    font-size: 10px;
}}
QLabel#AppIcon {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #14b8a6, stop:1 #059669);
    color: white;
    border-radius: 12px;
    font-size: 18px;
    font-weight: 700;
}}
QLabel#EnvBadgeOk {{
    color: {C["ok"]};
    background-color: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
}}
QLabel#EnvBadgeBad, QLabel#EnvBadgeIdle {{
    color: {C["warn"]};
    background-color: rgba(251, 191, 36, 0.1);
    border: 1px solid rgba(251, 191, 36, 0.3);
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#QuickPrimary {{
    background-color: #0d9488;
    color: white;
    border: none;
    border-radius: 9px;
    padding: 9px 16px;
    font-weight: 600;
    font-size: 12px;
}}
QPushButton#QuickPrimary:hover {{
    background-color: #14b8a6;
}}
QPushButton#QuickPrimary:disabled {{
    background-color: #1f3a3a;
    color: #64748b;
}}
QPushButton#WinDot, QPushButton#WinDotClose {{
    border: none;
    border-radius: 6px;
    padding: 0;
    min-width: 12px;
    max-width: 12px;
    min-height: 12px;
    max-height: 12px;
    background-color: #475569;
}}
QPushButton#WinDot:hover {{
    background-color: #94a3b8;
}}
QPushButton#WinDotClose {{
    background-color: #f87171;
}}
QPushButton#WinDotClose:hover {{
    background-color: #ef4444;
}}
QMainWindow {{
    border: 1px solid {C["border"]};
}}
QFrame#StepActive {{
    background-color: {C["surface2"]};
    border: 1px solid {C["border_active"]};
    border-radius: 12px;
}}
QFrame#StepIdle {{
    background-color: rgba(15, 23, 42, 0.6);
    border: 1px solid {C["border"]};
    border-radius: 12px;
}}
QLineEdit, QComboBox, QSpinBox {{
    background-color: {C["surface2"]};
    border: 1px solid {C["border"]};
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: {C["accent"]};
    min-height: 18px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {C["accent"]};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    color: {C["idle"]};
    background-color: #0f172a;
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox QAbstractItemView {{
    background-color: {C["surface2"]};
    border: 1px solid {C["border"]};
    selection-background-color: {C["accent"]};
}}
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {C["border"]};
    background: {C["surface2"]};
}}
QCheckBox::indicator:checked {{
    background: {C["primary"]};
    border-color: {C["primary"]};
}}
QCheckBox:disabled {{
    color: {C["idle"]};
}}
QPushButton {{
    background-color: {C["surface2"]};
    border: 1px solid {C["border"]};
    border-radius: 9px;
    padding: 8px 14px;
    min-height: 20px;
}}
QPushButton:hover {{
    border-color: {C["accent"]};
    background-color: #243044;
}}
QPushButton:disabled {{
    color: {C["idle"]};
    background-color: #1a2332;
    border-color: #2a3548;
}}
QPushButton#Primary {{
    background-color: {C["primary"]};
    color: #04140f;
    border: none;
    font-weight: 700;
    padding: 10px 22px;
}}
QPushButton#Primary:hover {{
    background-color: {C["primary_hover"]};
}}
QPushButton#Primary:disabled {{
    background-color: #1f3a32;
    color: #64748b;
}}
QPushButton#Accent {{
    background-color: rgba(20, 184, 166, 0.15);
    color: {C["accent"]};
    border: 1px solid rgba(20, 184, 166, 0.45);
}}
QPushButton#Ghost {{
    background-color: transparent;
    border: 1px solid {C["border"]};
}}
QTextEdit#Log {{
    background-color: {C["log_bg"]};
    color: {C["log_fg"]};
    border: 1px solid {C["border"]};
    border-radius: 10px;
    padding: 8px;
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 12px;
}}
QProgressBar {{
    border: none;
    background: {C["surface2"]};
    border-radius: 4px;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {C["accent"]};
    border-radius: 4px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #475569;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QLabel#FieldLabel {{
    color: {C["muted"]};
    font-size: 12px;
}}
QFrame#AppFooter {{
    background-color: #020617;
    border-top: 1px solid {C["border"]};
}}
QLabel#FooterBrand {{
    color: #64748b;
    font-size: 11px;
}}
QLabel#FooterMuted {{
    color: #64748b;
    font-size: 11px;
}}
QLabel#FooterSep {{
    color: #334155;
    font-size: 11px;
}}
QLabel#FooterWsl {{
    color: #94a3b8;
    font-size: 11px;
}}
QLabel#FlowHint {{
    color: #5eead4;
    background-color: rgba(20, 184, 166, 0.08);
    border: 1px solid rgba(20, 184, 166, 0.18);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 11px;
}}
QFrame#HeroBanner {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0f172a, stop:1 #042f2e);
    border: 1px solid rgba(20, 184, 166, 0.35);
    border-radius: 14px;
}}
QFrame#HeroBannerBad {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0f172a, stop:1 #3b1d1d);
    border: 1px solid rgba(248, 113, 113, 0.35);
    border-radius: 14px;
}}
QPushButton#FooterCancel {{
    background-color: transparent;
    border: 1px solid {C["border"]};
    border-radius: 6px;
    padding: 3px 10px;
    min-height: 16px;
    font-size: 11px;
    color: #cbd5e1;
}}
QPushButton#FooterCancel:disabled {{
    color: #475569;
    border-color: #1e293b;
}}
QStatusBar {{
    background: {C["surface"]};
    border-top: 1px solid {C["border"]};
    color: {C["muted"]};
}}
QToolTip {{
    background-color: {C["surface2"]};
    color: {C["text"]};
    border: 1px solid {C["border"]};
    padding: 4px;
}}
"""


def apply_theme(app) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(APP_QSS)
