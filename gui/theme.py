"""深色主题 QSS（对齐全局参考样式）。"""
from __future__ import annotations

C = {
    "bg": "#0B0F17",
    "surface": "#111827",
    "surface2": "#1F2937",
    "border": "#1F2937",
    "border_input": "#374151",
    "border_active": "#0D9488",
    "text": "#E2E8F0",
    "text_bright": "#F9FAFB",
    "muted": "#9CA3AF",
    "muted2": "#64748B",
    "primary": "#0D9488",
    "primary_hover": "#0F766E",
    "primary_pressed": "#115E59",
    "accent": "#14B8A6",
    "ok": "#34d399",
    "warn": "#fbbf24",
    "err": "#f87171",
    "idle": "#4B5563",
    "log_bg": "#030712",
    "log_fg": "#A7F3D0",
}


APP_QSS = f"""
/* ---- 1. 全局 ---- */
QWidget {{
    background-color: transparent;
    font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    color: {C["text"]};
    font-size: 13px;
    outline: none;
}}
QMainWindow, QDialog {{
    background-color: {C["bg"]};
}}
QMainWindow {{
    border: 1px solid {C["border"]};
}}
QScrollArea, QScrollArea > QWidget > QWidget, QStackedWidget {{
    background-color: transparent;
    border: none;
}}

/* ---- 2. 顶栏 / 卡片 ---- */
QFrame#Chrome, QFrame#MainHeader, QFrame#HeaderFrame {{
    background-color: {C["surface"]};
    border-bottom: 1px solid {C["border"]};
}}
QFrame#TitleBar {{
    background-color: #020617;
    border-bottom: 1px solid {C["border"]};
}}
QFrame#Card, QFrame#CardFrame, QFrame#ScratchCard {{
    background-color: {C["surface"]};
    border: 1px solid {C["border"]};
    border-radius: 12px;
}}
QFrame#CardDivider, QFrame#SpecDivider {{
    background-color: {C["border"]};
    border: none;
    max-height: 1px;
}}
QLabel#Title {{
    font-size: 17px;
    font-weight: 700;
    color: {C["text_bright"]};
    background: transparent;
}}
QLabel#Subtitle {{
    color: {C["muted"]};
    font-size: 12px;
    background: transparent;
}}
QLabel#Muted, QLabel#FieldLabel, QLabel#FormSectionLabel {{
    color: {C["muted"]};
    font-size: 12px;
    background: transparent;
    border: none;
}}
QLabel#CardTitle, QLabel#CardHeadTitle {{
    font-weight: 700;
    font-size: 16px;
    color: {C["text_bright"]};
    background: transparent;
    border: none;
}}
QLabel#CardHeadRight {{
    font-size: 12px;
    color: {C["muted2"]};
    background: transparent;
    border: none;
}}
QLabel#CardHeadIcon {{
    background: transparent;
    border: none;
}}

/* ---- 预设子卡 ---- */
QFrame#PresetCard, QFrame#InnerSubCard {{
    background-color: #030712;
    border: 1px solid {C["border"]};
    border-radius: 8px;
}}
QFrame#PresetCard:hover {{
    border: 1px solid #4B5563;
}}
QFrame#PresetCardActive {{
    background-color: #030712;
    border: 2px solid {C["primary"]};
    border-radius: 8px;
}}
QLabel#PresetTitle {{
    font-size: 14px;
    font-weight: 700;
    color: {C["text_bright"]};
    background: transparent;
    border: none;
}}
QLabel#PresetMeta {{
    font-size: 11px;
    color: {C["muted2"]};
    background: transparent;
    border: none;
}}
QLabel#PresetTag {{
    font-size: 10px;
    color: {C["muted"]};
    background-color: {C["surface2"]};
    border: 1px solid #4B5563;
    border-radius: 4px;
    padding: 2px 8px;
}}
QLabel#PresetTagActive {{
    font-size: 10px;
    color: #FFFFFF;
    background-color: {C["primary"]};
    border: none;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 700;
}}
QLabel#SpecKey {{
    color: {C["muted"]};
    font-size: 12px;
    background: transparent;
}}
QLabel#SpecVal {{
    color: {C["text"]};
    font-size: 12px;
    font-family: "Cascadia Code", Consolas, monospace;
    background: transparent;
}}
QLabel#SpecValAccent {{
    color: {C["accent"]};
    font-size: 12px;
    font-weight: 600;
    font-family: "Cascadia Code", Consolas, monospace;
    background: transparent;
}}
QLabel#SpecValOk {{
    color: {C["ok"]};
    font-size: 12px;
    font-weight: 600;
    background: transparent;
}}

/* ---- 3. 输入 / 下拉 ---- */
QLineEdit, QComboBox, QSpinBox, QLineEdit#PathEdit {{
    background-color: #030712;
    border: 1px solid {C["border_input"]};
    border-radius: 8px;
    padding: 8px 12px;
    color: {C["text_bright"]};
    font-size: 13px;
    font-family: "Cascadia Code", Consolas, "Segoe UI", monospace;
    selection-background-color: {C["primary"]};
    min-height: 18px;
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{
    border-color: #4B5563;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QLineEdit#PathEdit:focus {{
    border: 1px solid {C["primary"]};
    background-color: #0B0F17;
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    color: {C["idle"]};
    background-color: #111827;
    border-color: {C["border"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {C["surface"]};
    border: 1px solid {C["border_input"]};
    selection-background-color: {C["primary"]};
    selection-color: #FFFFFF;
    color: {C["text_bright"]};
}}

/* ---- 4. 按钮 ---- */
QPushButton {{
    background-color: {C["surface2"]};
    border: 1px solid {C["border_input"]};
    border-radius: 8px;
    padding: 8px 16px;
    color: #E5E7EB;
    font-weight: 600;
    font-size: 13px;
    min-height: 20px;
}}
QPushButton:hover {{
    background-color: {C["border_input"]};
    border-color: #4B5563;
    color: #FFFFFF;
}}
QPushButton:pressed {{
    background-color: #111827;
}}
QPushButton:disabled {{
    background-color: #111827;
    border-color: {C["border"]};
    color: {C["idle"]};
}}
QPushButton#Primary, QPushButton#PrimaryBtn, QPushButton#EnvPrimary,
QPushButton#HeroPrimary, QPushButton#QuickPrimary {{
    background-color: {C["primary"]};
    border: 1px solid {C["accent"]};
    color: #FFFFFF;
    font-weight: 600;
}}
QPushButton#Primary:hover, QPushButton#PrimaryBtn:hover, QPushButton#EnvPrimary:hover,
QPushButton#HeroPrimary:hover, QPushButton#QuickPrimary:hover {{
    background-color: {C["primary_hover"]};
    border-color: #2DD4BF;
}}
QPushButton#Primary:pressed, QPushButton#PrimaryBtn:pressed, QPushButton#EnvPrimary:pressed,
QPushButton#HeroPrimary:pressed, QPushButton#QuickPrimary:pressed {{
    background-color: {C["primary_pressed"]};
}}
QPushButton#Primary:disabled, QPushButton#PrimaryBtn:disabled, QPushButton#EnvPrimary:disabled,
QPushButton#HeroPrimary:disabled, QPushButton#QuickPrimary:disabled {{
    background-color: #111827;
    border-color: {C["border"]};
    color: {C["idle"]};
}}
QPushButton#EnvGhost, QPushButton#EnvAccent, QPushButton#Ghost, QPushButton#Accent {{
    background-color: {C["surface2"]};
    border: 1px solid {C["border_input"]};
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    color: #E5E7EB;
}}
QPushButton#EnvGhost:hover, QPushButton#EnvAccent:hover, QPushButton#Ghost:hover, QPushButton#Accent:hover {{
    background-color: {C["border_input"]};
    border-color: #4B5563;
    color: #FFFFFF;
}}
QPushButton#HeroGhost {{
    background-color: {C["surface2"]};
    border: 1px solid {C["border_input"]};
    border-radius: 999px;
    padding: 8px 14px;
    font-size: 12px;
    color: #E5E7EB;
    min-height: 18px;
}}
QPushButton#HeroGhost:hover {{
    background-color: {C["border_input"]};
    border-color: #4B5563;
}}
QPushButton#HeroPrimary {{
    border-radius: 999px;
    padding: 8px 16px;
    font-size: 12px;
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
    color: {C["idle"]};
    border-color: {C["border"]};
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

/* ---- 5. 复选框 ---- */
QCheckBox {{
    spacing: 8px;
    color: {C["muted"]};
    font-size: 13px;
}}
QCheckBox:hover {{
    color: #E5E7EB;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #4B5563;
    background-color: #030712;
}}
QCheckBox::indicator:hover {{
    border-color: {C["primary"]};
}}
QCheckBox::indicator:checked {{
    background-color: {C["primary"]};
    border-color: {C["accent"]};
}}
QCheckBox:disabled {{
    color: {C["idle"]};
}}

/* ---- 6. 进度条 ---- */
QProgressBar {{
    border: none;
    background-color: {C["surface2"]};
    border-radius: 4px;
    text-align: center;
    color: transparent;
    height: 8px;
}}
QProgressBar::chunk {{
    background-color: {C["primary"]};
    border-radius: 4px;
}}

/* ---- 7. 日志控制台 ---- */
QTextEdit#Log, QTextEdit#TerminalLog, QTextEdit#ConsoleEdit {{
    background-color: #030712;
    border: 1px solid {C["border"]};
    border-radius: 10px;
    font-family: "Cascadia Code", Consolas, "Courier New", monospace;
    font-size: 12px;
    color: {C["log_fg"]};
    padding: 12px;
}}
QFrame#TerminalCard {{
    background-color: #030712;
    border: 1px solid {C["border"]};
    border-radius: 12px;
}}

/* ---- 8. 表格 ---- */
QTableWidget {{
    background-color: #030712;
    border: 1px solid {C["border"]};
    gridline-color: {C["border"]};
    border-radius: 8px;
    color: {C["text"]};
}}
QHeaderView::section {{
    background-color: {C["surface"]};
    color: {C["muted"]};
    padding: 8px;
    border: none;
    font-weight: 600;
}}
QTableWidget::item {{
    padding: 6px;
}}
QTableWidget::item:selected {{
    background-color: {C["primary_hover"]};
    color: #FFFFFF;
}}

/* ---- 9. 滚动条 ---- */
QScrollBar:vertical {{
    border: none;
    background: #030712;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C["border_input"]};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: #4B5563;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* ---- 10. 标题栏细节 ---- */
QLabel#TitleLogo {{
    background-color: rgba(20, 184, 166, 0.2);
    color: {C["accent"]};
    border-radius: 5px;
    font-size: 10px;
    font-weight: 700;
}}
QLabel#TitleAppName {{
    color: #f8fafc;
    font-size: 12px;
    font-weight: 700;
    background: transparent;
}}
QLabel#TitleVerBadge {{
    color: {C["accent"]};
    background-color: rgba(20, 184, 166, 0.1);
    border: 1px solid rgba(20, 184, 166, 0.2);
    border-radius: 3px;
    padding: 1px 6px;
    margin: 0px;
    font-size: 10px;
    font-family: Consolas, monospace;
}}
QLabel#TitleCenter {{
    color: #94a3b8;
    font-size: 11px;
    background: transparent;
}}
QLabel#TitleDotOk {{
    background-color: {C["ok"]};
    border-radius: 4px;
    min-width: 8px; max-width: 8px;
    min-height: 8px; max-height: 8px;
}}
QLabel#TitleDotWarn {{
    background-color: {C["warn"]};
    border-radius: 4px;
    min-width: 8px; max-width: 8px;
    min-height: 8px; max-height: 8px;
}}
QLabel#TitleCenterSep {{
    color: #334155;
    font-size: 11px;
    background: transparent;
}}
QLabel#AppIcon {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #14b8a6, stop:1 #059669);
    color: white;
    border-radius: 16px;
    font-size: 22px;
    font-weight: 700;
}}
QFrame#ReadyPillOk {{
    background-color: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 14px;
}}
QFrame#ReadyPillBad {{
    background-color: rgba(251, 191, 36, 0.12);
    border: 1px solid rgba(251, 191, 36, 0.3);
    border-radius: 14px;
}}
QLabel#ReadyPillCircleOk {{
    background-color: transparent;
    color: {C["ok"]};
    border: 1.5px solid {C["ok"]};
    border-radius: 9px;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#ReadyPillCircleBad {{
    background-color: transparent;
    color: {C["warn"]};
    border: 1.5px solid {C["warn"]};
    border-radius: 9px;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#ReadyPillTextOk {{
    background: transparent;
    border: none;
    color: {C["ok"]};
    font-size: 12px;
    font-weight: 600;
}}
QLabel#ReadyPillTextBad {{
    background: transparent;
    border: none;
    color: {C["warn"]};
    font-size: 12px;
    font-weight: 600;
}}
QLabel#HeroCheckCircle {{
    background-color: white;
    color: {C["accent"]};
    border-radius: 11px;
    font-size: 14px;
    font-weight: 700;
}}
QLabel#HeroWarnMark {{
    background-color: transparent;
    color: {C["warn"]};
    font-size: 20px;
    font-weight: 700;
}}
QFrame#HeroIconOk {{
    background-color: {C["accent"]};
    border-radius: 12px;
}}
QFrame#HeroIconBad {{
    background-color: {C["surface2"]};
    border-radius: 12px;
}}

/* ---- 步骤导航 ---- */
QFrame#StepNavBar {{
    background-color: rgba(17, 24, 39, 0.85);
    border-bottom: 1px solid {C["border"]};
}}
QFrame#StepActive {{
    background-color: {C["surface2"]};
    border: 1px solid rgba(20, 184, 166, 0.5);
    border-radius: 12px;
}}
QFrame#StepIdle {{
    background-color: rgba(17, 24, 39, 0.55);
    border: 1px solid {C["border"]};
    border-radius: 12px;
}}
QFrame#StepIdle:hover {{
    background-color: {C["surface2"]};
}}
QFrame#StepActive QLabel, QFrame#StepIdle QLabel {{
    background: transparent;
    border: none;
}}
QLabel#StepTitle {{
    background: transparent;
    border: none;
    color: {C["text_bright"]};
    font-weight: 700;
    font-size: 13px;
}}
QLabel#StepDesc {{
    background: transparent;
    border: none;
    color: {C["muted"]};
    font-size: 11px;
}}
QLabel#StepChevron {{
    background: transparent;
    border: none;
    color: {C["muted2"]};
    font-size: 16px;
    font-weight: 300;
}}
QFrame#FlowHintBox {{
    background-color: rgba(20, 184, 166, 0.05);
    border: 1px solid rgba(20, 184, 166, 0.1);
    border-radius: 8px;
}}
QFrame#FlowHintBox QLabel {{
    background: transparent;
    border: none;
}}
QLabel#FlowHintKey {{
    color: #5eead4;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#FlowHintVal {{
    color: #94a3b8;
    font-size: 11px;
    font-family: "Cascadia Code", Consolas, monospace;
}}
QFrame#SectionHero, QFrame#ActionBar {{
    background-color: {C["surface"]};
    border: 1px solid {C["border"]};
    border-radius: 12px;
}}
QLabel#SectionHeroTitle {{
    color: {C["text_bright"]};
    font-size: 14px;
    font-weight: 700;
    background: transparent;
    border: none;
}}
QLabel#SectionHeroDesc {{
    color: {C["muted"]};
    font-size: 12px;
    background: transparent;
    border: none;
}}
QFrame#AppFooter {{
    background-color: #020617;
    border-top: 1px solid {C["border"]};
}}
QLabel#FooterBrand, QLabel#FooterMuted {{
    color: {C["muted2"]};
    font-size: 11px;
    background: transparent;
}}
QLabel#FooterSep {{
    color: #334155;
    font-size: 11px;
    background: transparent;
}}
QLabel#FooterWsl {{
    color: #94a3b8;
    font-size: 11px;
    background: transparent;
}}
QFrame#HeroBanner {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0b1220, stop:1 #042f2e);
    border: 1px solid rgba(20, 184, 166, 0.3);
    border-radius: 12px;
}}
QFrame#HeroBannerBad {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0b1220, stop:1 #3b1d1d);
    border: 1px solid rgba(248, 113, 113, 0.35);
    border-radius: 12px;
}}
QLabel#HeroTitle {{
    color: {C["text_bright"]};
    font-size: 15px;
    font-weight: 700;
    background: transparent;
    border: none;
}}
QLabel#HeroDesc {{
    color: {C["muted"]};
    font-size: 12px;
    background: transparent;
    border: none;
}}
QFrame#ScratchHeader {{
    background: transparent;
    border: none;
}}
QLabel#ScratchTitle {{
    background: transparent;
    border: none;
    color: #E2E8F0;
    font-weight: 700;
    font-size: 13px;
}}
QLabel#ScratchDesc {{
    background: transparent;
    border: none;
    color: #64748B;
    font-size: 11px;
}}
QToolButton#ScratchToggle {{
    background: transparent;
    border: none;
    color: {C["text_bright"]};
    font-weight: 700;
    font-size: 14px;
    padding: 0;
    text-align: left;
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
