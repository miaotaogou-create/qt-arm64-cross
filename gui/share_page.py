"""部署与共享页：Hero + 地址/扫码双栏 + HTTP 日志 + 网卡管理。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.env_panel import PathInputField
from gui.icons import make_svg_icon

_SVG = {
    "globe": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>'
        '<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 '
        '15.3 15.3 0 0 1 4-10z"/></svg>'
    ),
    "network": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="2" y="2" width="6" height="6" rx="1"/>'
        '<rect x="16" y="2" width="6" height="6" rx="1"/>'
        '<rect x="9" y="16" width="6" height="6" rx="1"/>'
        '<path d="M5 8v4h14V8"/><path d="M12 12v4"/></svg>'
    ),
    "wifi": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M5 12.55a11 11 0 0 1 14.08 0"/>'
        '<path d="M1.42 9a16 16 0 0 1 21.16 0"/>'
        '<path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>'
        '<line x1="12" y1="20" x2="12.01" y2="20"/></svg>'
    ),
    "qr": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>'
        '<rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="3" height="3"/>'
        '<rect x="18" y="18" width="3" height="3"/></svg>'
    ),
    "terminal": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>'
    ),
}


class _Svg(QSvgWidget):
    def __init__(self, kind: str, color: str, size: int, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.load(_SVG[kind].format(c=color).encode("utf-8"))


def _prefix_to_mask(prefix: int) -> str:
    n = max(0, min(32, int(prefix)))
    bits = (0xFFFFFFFF << (32 - n)) & 0xFFFFFFFF if n else 0
    return ".".join(str((bits >> s) & 0xFF) for s in (24, 16, 8, 0))


def _fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _qr_pixmap(text: str, px: int = 168) -> QPixmap | None:
    """把 URL 渲成二维码图；缺依赖时返回 None（界面退回显示文字）。"""
    if not text or text == "—":
        return None
    try:
        import qrcode
        from qrcode.image.pil import PilImage
    except ImportError:
        return None
    img = qrcode.make(text, border=1, image_factory=PilImage)
    if hasattr(img, "get_image"):
        img = img.get_image()
    if hasattr(img, "convert"):
        img = img.convert("RGB")
    w, h = img.size
    data = img.tobytes("raw", "RGB")
    qimg = QImage(data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(qimg).scaled(
        px, px, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
    )


class SharePage(QWidget):
    """共享页主体。业务仍由 MainWindow 接线。"""

    remove_ip_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        root.addWidget(self._build_hero())
        root.addLayout(self._build_main_row(), 1)
        root.addWidget(self._build_log())
        root.addWidget(self._build_eth_toggle())
        root.addWidget(self._build_nic())

    def _build_hero(self) -> QFrame:
        hero = QFrame()
        hero.setObjectName("ShareHero")
        hero.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QHBoxLayout(hero)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(16)

        icon_wrap = QFrame()
        icon_wrap.setObjectName("ShareHeroIcon")
        icon_wrap.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        icon_wrap.setFixedSize(48, 48)
        iw = QHBoxLayout(icon_wrap)
        iw.setContentsMargins(0, 0, 0, 0)
        iw.addWidget(_Svg("globe", "#14B8A6", 28), 0, Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon_wrap)

        texts = QVBoxLayout()
        texts.setSpacing(4)
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        t1 = QLabel("嵌入式板端 HTTP 极速部署共享")
        t1.setObjectName("ShareHeroTitle")
        title_row.addWidget(t1)
        self._status_badge = QLabel("●  服务已停止")
        self._status_badge.setObjectName("ShareStatusOff")
        title_row.addWidget(self._status_badge)
        title_row.addStretch(1)
        texts.addLayout(title_row)
        t2 = QLabel("支持直接通过浏览器或 wget / curl 在麒麟、飞腾、树莓派等嵌入式 Linux 板端一键刷机或提货。")
        t2.setObjectName("ShareHeroDesc")
        t2.setWordWrap(True)
        texts.addWidget(t2)
        lay.addLayout(texts, 1)

        self.btn_toggle = QPushButton("一键启动 HTTP 共享")
        self.btn_toggle.setObjectName("BtnShareStart")
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setIcon(make_svg_icon("power", "#FFFFFF", 16, pad_right=6))
        self.btn_toggle.setIconSize(QSize(22, 16))
        self.btn_toggle.setMinimumHeight(40)
        lay.addWidget(self.btn_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        return hero

    def _build_main_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(self._build_left(), 3)
        right = QVBoxLayout()
        right.setSpacing(12)
        right.addWidget(self._build_qr())
        right.addWidget(self._build_manifest(), 1)
        row.addLayout(right, 2)
        return row

    def _build_left(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        dir_head = QHBoxLayout()
        dir_lbl = QLabel("共享文件目录")
        dir_lbl.setObjectName("ShareFieldLabel")
        dir_head.addWidget(dir_lbl)
        dir_head.addStretch(1)
        self.btn_sync = QPushButton("同步使用最新编译产物目录")
        self.btn_sync.setObjectName("ShareLinkBtn")
        self.btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        dir_head.addWidget(self.btn_sync)
        lay.addLayout(dir_head)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        self._path_field = PathInputField("", folder_color="#F59E0B")
        self.ed_share_dir = self._path_field.ed
        dir_row.addWidget(self._path_field, 1)
        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.setObjectName("EnvGhost")
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        dir_row.addWidget(self.btn_browse)
        lay.addLayout(dir_row)

        port_row = QHBoxLayout()
        port_row.setSpacing(10)
        port_lbl = QLabel("服务端口 (Port):")
        port_lbl.setObjectName("ShareFieldLabel")
        port_row.addWidget(port_lbl)
        self.sp_port = QSpinBox()
        self.sp_port.setObjectName("SharePort")
        self.sp_port.setRange(1, 65535)
        self.sp_port.setFixedWidth(110)
        port_row.addWidget(self.sp_port)
        port_hint = QLabel("提示：支持自定义端口，嵌入式开发板连入相同局域网即可下载。")
        port_hint.setObjectName("Muted")
        port_hint.setWordWrap(True)
        port_row.addWidget(port_hint, 1)
        lay.addLayout(port_row)

        lan_title = QLabel("局域网直连提货地址")
        lan_title.setObjectName("ShareFieldLabel")
        lay.addWidget(lan_title)

        lan = QFrame()
        lan.setObjectName("LanUrlCard")
        lan.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lan_lay = QHBoxLayout(lan)
        lan_lay.setContentsMargins(14, 12, 12, 12)
        lan_lay.setSpacing(12)
        lan_lay.addWidget(_Svg("wifi", "#14B8A6", 22), 0, Qt.AlignmentFlag.AlignVCenter)
        lan_texts = QVBoxLayout()
        lan_texts.setSpacing(2)
        sub = QLabel("局域网首选 IP (以太网 / Wi-Fi)")
        sub.setObjectName("Muted")
        lan_texts.addWidget(sub)
        self.ed_share_urls = QLineEdit("—")
        self.ed_share_urls.setObjectName("LanUrlEdit")
        self.ed_share_urls.setReadOnly(True)
        lan_texts.addWidget(self.ed_share_urls)
        lan_lay.addLayout(lan_texts, 1)
        self.btn_copy = QPushButton("复制地址")
        self.btn_copy.setObjectName("BtnCopyUrl")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setIcon(make_svg_icon("copy", "#14B8A6", 14, pad_right=4))
        self.btn_copy.setIconSize(QSize(18, 14))
        lan_lay.addWidget(self.btn_copy)
        self.btn_open = QPushButton()
        self.btn_open.setObjectName("IconGhost")
        self.btn_open.setToolTip("在浏览器打开本机地址")
        self.btn_open.setFixedSize(34, 34)
        self.btn_open.setIcon(make_svg_icon("external", "#E5E7EB", 15))
        self.btn_open.setIconSize(QSize(15, 15))
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        lan_lay.addWidget(self.btn_open)
        lay.addWidget(lan)

        loop = QHBoxLayout()
        self.ed_share_local = QLineEdit("—")
        self.ed_share_local.setVisible(False)
        loop_lbl = QLabel("本机 Loopback:")
        loop_lbl.setObjectName("Muted")
        loop.addWidget(loop_lbl)
        self._loop_url = QLabel("http://127.0.0.1:—")
        self._loop_url.setObjectName("LoopUrl")
        loop.addWidget(self._loop_url)
        loop.addStretch(1)
        self.btn_probe = QPushButton("执行自检 (Self-check)")
        self.btn_probe.setObjectName("ShareLinkBtn")
        self.btn_probe.setCursor(Qt.CursorShape.PointingHandCursor)
        loop.addWidget(self.btn_probe)
        lay.addLayout(loop)
        lay.addStretch(1)
        return card

    def _build_qr(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        head = QHBoxLayout()
        head.addWidget(_Svg("qr", "#14B8A6", 16))
        h = QLabel("扫码提货 / 扫码下载")
        h.setObjectName("CardTitle")
        head.addWidget(h)
        head.addStretch(1)
        hint = QLabel("摄像头对准扫码")
        hint.setObjectName("Muted")
        head.addWidget(hint)
        lay.addLayout(head)

        self._qr_lbl = QLabel("启动共享后显示二维码")
        self._qr_lbl.setObjectName("QrPlaceholder")
        self._qr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_lbl.setMinimumHeight(180)
        self._qr_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay.addWidget(self._qr_lbl, 1)

        foot = QLabel("平板或手机连接同一 Wi-Fi 即可扫码直接获取编译产物包。")
        foot.setObjectName("Muted")
        foot.setWordWrap(True)
        lay.addWidget(foot)
        return card

    def _build_manifest(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        head = QHBoxLayout()
        t = QLabel("待提货产物清单")
        t.setObjectName("CardTitle")
        head.addWidget(t)
        head.addStretch(1)
        self._pack_badge = QLabel("未打包")
        self._pack_badge.setObjectName("PackBadgeOff")
        head.addWidget(self._pack_badge)
        lay.addLayout(head)
        self._manifest_box = QVBoxLayout()
        self._manifest_box.setSpacing(6)
        lay.addLayout(self._manifest_box)
        lay.addStretch(1)
        return card

    def _build_log(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(8)
        head = QHBoxLayout()
        head.addWidget(_Svg("terminal", "#10B981", 16))
        t = QLabel("HTTP 服务传输日志")
        t.setObjectName("ShareLogTitle")
        head.addWidget(t)
        head.addStretch(1)
        lay.addLayout(head)
        self.share_log = QTextEdit()
        self.share_log.setObjectName("ShareLogEdit")
        self.share_log.setReadOnly(True)
        self.share_log.setFixedHeight(120)
        self.share_log.setPlainText("[HTTP] 服务器就绪，等待启动服务...\n")
        lay.addWidget(self.share_log)
        return card

    def _build_eth_toggle(self) -> QPushButton:
        self.btn_eth = QPushButton("网卡高级 ▸")
        self.btn_eth.setObjectName("ShareLinkBtn")
        self.btn_eth.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eth.setFlat(True)
        return self.btn_eth

    def _build_nic(self) -> QFrame:
        self.nic_card = QFrame()
        self.nic_card.setObjectName("Card")
        self.nic_card.setVisible(False)
        lay = QVBoxLayout(self.nic_card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        head = QHBoxLayout()
        head.addWidget(_Svg("network", "#0D9488", 18))
        titles = QVBoxLayout()
        titles.setSpacing(2)
        t = QLabel("有线网卡高级 IP 地址绑定与管理 (NIC Manager)")
        t.setObjectName("CardTitle")
        titles.addWidget(t)
        d = QLabel("支持向现有网卡快速追加辅助调试段 IP（例如 192.168.8.x），以便连接不同网段的 ARM 板，无需修改默认网关。")
        d.setObjectName("Muted")
        d.setWordWrap(True)
        titles.addWidget(d)
        head.addLayout(titles, 1)
        self.btn_uac = QPushButton("Windows UAC 提权管理")
        self.btn_uac.setObjectName("BtnUac")
        self.btn_uac.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_uac.setIcon(make_svg_icon("shield", "#F59E0B", 14, pad_right=4))
        self.btn_uac.setIconSize(QSize(18, 14))
        head.addWidget(self.btn_uac, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(head)

        bar = QFrame()
        bar.setObjectName("EthAddBar")
        bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(14, 12, 14, 12)
        bar_lay.setSpacing(12)
        col_ip = QVBoxLayout()
        col_ip.setSpacing(4)
        ip_lbl = QLabel("追加辅助 IP 地址:")
        ip_lbl.setObjectName("EthBarLabel")
        col_ip.addWidget(ip_lbl)
        self.ed_eth_ip = QLineEdit()
        self.ed_eth_ip.setObjectName("EthBarEdit")
        self.ed_eth_ip.setPlaceholderText("192.168.8.9")
        col_ip.addWidget(self.ed_eth_ip)
        bar_lay.addLayout(col_ip, 1)
        col_mask = QVBoxLayout()
        col_mask.setSpacing(4)
        mask_lbl = QLabel("子网掩码 (Subnet Mask):")
        mask_lbl.setObjectName("EthBarLabel")
        col_mask.addWidget(mask_lbl)
        self.ed_eth_mask = QLineEdit("255.255.255.0")
        self.ed_eth_mask.setObjectName("EthBarEdit")
        col_mask.addWidget(self.ed_eth_mask)
        bar_lay.addLayout(col_mask, 1)
        self.btn_add_ip = QPushButton("追加绑定 IP")
        self.btn_add_ip.setObjectName("BtnAddIp")
        self.btn_add_ip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_ip.setMinimumHeight(36)
        bar_lay.addWidget(self.btn_add_ip, 0, Qt.AlignmentFlag.AlignBottom)
        lay.addWidget(bar)

        cols = QHBoxLayout()
        for text, stretch in (("网卡与名称", 3), ("绑定 IP 地址", 2), ("子网掩码", 2), ("操作", 1)):
            h = QLabel(text)
            h.setObjectName("NicColHead")
            cols.addWidget(h, stretch)
        lay.addLayout(cols)

        self._nic_rows = QVBoxLayout()
        self._nic_rows.setSpacing(0)
        lay.addLayout(self._nic_rows)
        self._nic_empty = QLabel("（尚未刷新）")
        self._nic_empty.setObjectName("Muted")
        lay.addWidget(self._nic_empty)
        return self.nic_card

    def set_running(self, running: bool, state_text: str = "") -> None:
        if running:
            self._status_badge.setText("●  服务运行中")
            self._status_badge.setObjectName("ShareStatusOn")
            self.btn_toggle.setText("停止 HTTP 共享")
            self.btn_toggle.setObjectName("BtnShareStop")
            self.btn_toggle.setIcon(make_svg_icon("power", "#FCA5A5", 16, pad_right=6))
        else:
            self._status_badge.setText("●  服务已停止")
            self._status_badge.setObjectName("ShareStatusOff")
            self.btn_toggle.setText("一键启动 HTTP 共享")
            self.btn_toggle.setObjectName("BtnShareStart")
            self.btn_toggle.setIcon(make_svg_icon("power", "#FFFFFF", 16, pad_right=6))
        for w in (self._status_badge, self.btn_toggle):
            w.style().unpolish(w)
            w.style().polish(w)
        if state_text:
            self._status_badge.setToolTip(state_text)
        self.refresh_qr()

    def set_loop_url(self, url: str) -> None:
        self.ed_share_local.setText(url)
        self._loop_url.setText(url if url and url != "—" else "http://127.0.0.1:—")
        self.refresh_qr()

    def refresh_qr(self) -> None:
        url = self.ed_share_urls.text().strip()
        pix = _qr_pixmap(url)
        if pix is not None:
            self._qr_lbl.setPixmap(pix)
            self._qr_lbl.setText("")
            return
        if url and url != "—":
            self._qr_lbl.setPixmap(QPixmap())
            self._qr_lbl.setText(url)
        else:
            self._qr_lbl.setPixmap(QPixmap())
            self._qr_lbl.setText("启动共享后显示二维码")

    def refresh_manifest(self, directory: str) -> None:
        while self._manifest_box.count():
            item = self._manifest_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        root = Path(directory) if directory else None
        files: list[Path] = []
        if root is not None and root.is_dir():
            files = [p for p in root.iterdir() if p.is_file()]
            files.sort(key=lambda p: (0 if p.suffix in {".gz", ".zip", ".tgz", ".sh"} else 1, p.name.lower()))
            files = files[:6]
        if not files:
            empty = QLabel("目录为空，编译成功后产物会出现在这里。")
            empty.setObjectName("Muted")
            empty.setWordWrap(True)
            self._manifest_box.addWidget(empty)
            self._pack_badge.setText("未打包")
            self._pack_badge.setObjectName("PackBadgeOff")
        else:
            packed = any(p.suffix in {".gz", ".zip", ".tgz"} or p.name.endswith(".tar.gz") for p in files)
            self._pack_badge.setText("已打包" if packed else f"{len(files)} 个文件")
            self._pack_badge.setObjectName("PackBadgeOn" if packed else "PackBadgeOff")
            for p in files:
                self._manifest_box.addWidget(self._file_row(p))
        self._pack_badge.style().unpolish(self._pack_badge)
        self._pack_badge.style().polish(self._pack_badge)

    def _file_row(self, path: Path) -> QFrame:
        row = QFrame()
        row.setObjectName("ManifestRow")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(8, 6, 8, 6)
        kind = "archive" if path.suffix in {".gz", ".zip", ".tgz"} or path.name.endswith(".tar.gz") else "file_code"
        ico = QLabel()
        ico.setPixmap(make_svg_icon(kind, "#14B8A6", 16).pixmap(16, 16))
        lay.addWidget(ico)
        name = QLabel(path.name)
        name.setObjectName("ManifestName")
        lay.addWidget(name, 1)
        sz = QLabel(_fmt_size(path.stat().st_size))
        sz.setObjectName("Muted")
        lay.addWidget(sz)
        return row

    def refresh_nics(self, adapters) -> None:
        while self._nic_rows.count():
            item = self._nic_rows.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        rows = 0
        primary_done = False
        for ad in adapters or []:
            ips = list(ad.ips or [])
            if not ips:
                self._nic_rows.addWidget(self._nic_row(ad, None, protected=True, primary=not primary_done))
                primary_done = True
                rows += 1
                continue
            for i, ip in enumerate(ips):
                is_primary = (not primary_done) and i == 0
                protected = is_primary
                self._nic_rows.addWidget(self._nic_row(ad, ip, protected=protected, primary=is_primary))
                if is_primary:
                    primary_done = True
                rows += 1
        self._nic_empty.setVisible(rows == 0)
        if rows == 0:
            self._nic_empty.setText("未检测到物理以太网卡")

    def _nic_row(self, adapter, ip, *, protected: bool, primary: bool) -> QFrame:
        row = QFrame()
        row.setObjectName("NicRow")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(8)
        name_box = QHBoxLayout()
        name_box.setSpacing(8)
        dot = QLabel("●")
        dot.setStyleSheet("color:#34D399;" if primary else "color:#38BDF8;")
        name_box.addWidget(dot)
        label = adapter.name
        if str(getattr(adapter, "status", "")).lower() == "up":
            label = f"{label} (Up)"
        if primary:
            label += "  [Primary]"
        nl = QLabel(label)
        nl.setObjectName("NicName")
        name_box.addWidget(nl, 1)
        if primary:
            tag = QLabel("Primary")
            tag.setObjectName("PrimaryTag")
            name_box.addWidget(tag)
        name_w = QWidget()
        name_w.setLayout(name_box)
        lay.addWidget(name_w, 3)
        addr = ip.address if ip is not None else "—"
        mask = _prefix_to_mask(ip.prefix) if ip is not None else "—"
        al = QLabel(addr)
        al.setObjectName("NicIp")
        lay.addWidget(al, 2)
        ml = QLabel(mask)
        ml.setObjectName("Muted")
        lay.addWidget(ml, 2)
        if protected or ip is None:
            op = QLabel("主网卡保护")
            op.setObjectName("Muted")
            lay.addWidget(op, 1)
        else:
            btn = QPushButton()
            btn.setObjectName("IconGhost")
            btn.setFixedSize(30, 30)
            btn.setIcon(make_svg_icon("trash", "#F87171", 14))
            btn.setIconSize(QSize(14, 14))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"删除 {addr}")
            btn.clicked.connect(lambda _=False, a=addr: self.remove_ip_requested.emit(a))
            lay.addWidget(btn, 1, Qt.AlignmentFlag.AlignLeft)
        return row
