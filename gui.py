"""
Telegram Video Downloader Pro - Desktop GUI
Modern Dark Theme built with PySide6 (Qt) for Windows.
Supports in-app credentials guide, clipboard auto-detection, channel subfolders,
caption saving, multi-file live progress table, and chunk-level resume.
"""

import sys
import os
import re
import time
import asyncio
import webbrowser
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar, QFileDialog,
    QCheckBox, QSpinBox, QDialog, QFormLayout, QMessageBox,
    QFrame, QSplitter, QInputDialog
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QColor, QIcon, QKeySequence, QShortcut

import config
from link_parser import parse_telegram_link, extract_targets_from_text, ParsedTarget, LinkTarget
from client_manager import TelegramManager, VideoInfo
from downloader_engine import DownloaderEngine, DownloadResult, sanitize_filename

logger = logging.getLogger("tg-downloader.gui")
logging.basicConfig(level=logging.INFO)

# ==============================================================================
# Modern Dark QSS Stylesheet (Telegram Desktop & Windows 11 Fluent Inspired)
# ==============================================================================
DARK_STYLE = """
QMainWindow, QDialog {
    background-color: #16171b;
    color: #e2e4e9;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

QWidget {
    color: #e2e4e9;
    font-family: 'Segoe UI', Arial, sans-serif;
}

QFrame.card {
    background-color: #1e2026;
    border: 1px solid #2d313c;
    border-radius: 8px;
    padding: 10px;
}

QFrame.info-card {
    background-color: #192538;
    border: 1px solid #264366;
    border-radius: 8px;
    padding: 12px;
}

QLabel {
    color: #c9ccd6;
}

QLabel.header-title {
    font-size: 18px;
    font-weight: bold;
    color: #ffffff;
}

QLabel.section-title {
    font-size: 14px;
    font-weight: bold;
    color: #4db3ff;
}

QLineEdit, QTextEdit {
    background-color: #121316;
    border: 1px solid #333742;
    border-radius: 6px;
    padding: 8px;
    color: #ffffff;
    selection-background-color: #2b7bc4;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #3a9aff;
    background-color: #14161a;
}

QPushButton {
    background-color: #2b313e;
    color: #ffffff;
    border: 1px solid #3d4556;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #384052;
    border-color: #4e586d;
}

QPushButton:pressed {
    background-color: #222630;
}

QPushButton.primary {
    background-color: #0088cc;
    border: 1px solid #0099e6;
    font-weight: bold;
    font-size: 14px;
    padding: 9px 18px;
}

QPushButton.primary:hover {
    background-color: #0099e6;
}

QPushButton.primary:pressed {
    background-color: #0077b3;
}

QPushButton.success {
    background-color: #0f8b48;
    border: 1px solid #14a254;
    font-weight: bold;
}

QPushButton.success:hover {
    background-color: #13a355;
}

QPushButton.danger {
    background-color: #a82e2e;
    border: 1px solid #c23737;
}

QPushButton.danger:hover {
    background-color: #be3535;
}

QCheckBox {
    color: #c9ccd6;
    spacing: 7px;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border: 1px solid #444a59;
    border-radius: 4px;
    background-color: #121316;
}

QCheckBox::indicator:checked {
    background-color: #0088cc;
    border-color: #0099e6;
}

QSpinBox {
    background-color: #121316;
    border: 1px solid #333742;
    border-radius: 6px;
    padding: 5px;
    color: #ffffff;
}

QTableWidget {
    background-color: #181a20;
    alternate-background-color: #1e2027;
    border: 1px solid #2d313c;
    border-radius: 8px;
    gridline-color: #262933;
    color: #e2e4e9;
    selection-background-color: #273b54;
}

QHeaderView::section {
    background-color: #22252e;
    color: #8f96a8;
    font-weight: bold;
    padding: 6px;
    border: none;
    border-right: 1px solid #2d313c;
    border-bottom: 1px solid #2d313c;
}

QProgressBar {
    border: 1px solid #333742;
    border-radius: 4px;
    text-align: center;
    background-color: #121316;
    color: #ffffff;
    font-weight: bold;
    font-size: 11px;
}

QProgressBar::chunk {
    background-color: #0088cc;
    border-radius: 3px;
}

QScrollBar:vertical {
    background: #16171b;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #333742;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #444a59;
}
"""


# ==============================================================================
# Setup & Credentials Guide Dialog
# ==============================================================================
class CredentialsGuideDialog(QDialog):
    """
    Interactive guided setup dialog that visually guides the user
    on how to get their Telegram API credentials from my.telegram.org.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ Telegram API Setup Wizard")
        self.setMinimumWidth(560)
        self.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Header Title
        title = QLabel("Connect Your Telegram Account")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        layout.addWidget(title)

        # Step-by-Step Educational Box
        guide_card = QFrame()
        guide_card.setProperty("class", "info-card")
        g_layout = QVBoxLayout(guide_card)
        g_layout.setSpacing(8)

        g_title = QLabel("📖 Where to get your API credentials (Free & Instant)")
        g_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        g_title.setStyleSheet("color: #4db3ff;")
        g_layout.addWidget(g_title)

        instructions = (
            "1. Visit <b>my.telegram.org</b> and log in with your phone number.<br>"
            "2. Click on <b>'API development tools'</b>.<br>"
            "3. Create an application (any title, e.g. <i>Downloader</i>).<br>"
            "4. Copy your <b>API ID</b> and <b>API Hash</b> into the fields below."
        )
        lbl_inst = QLabel(instructions)
        lbl_inst.setWordWrap(True)
        lbl_inst.setStyleSheet("color: #b0c2de; line-height: 1.4;")
        g_layout.addWidget(lbl_inst)

        btn_open_browser = QPushButton("🌐 Open my.telegram.org in Browser")
        btn_open_browser.setStyleSheet("background-color: #1e3552; border-color: #2b5080; color: #66b2ff;")
        btn_open_browser.clicked.connect(lambda: webbrowser.open("https://my.telegram.org"))
        g_layout.addWidget(btn_open_browser)

        layout.addWidget(guide_card)

        # Form fields
        form_card = QFrame()
        form_card.setProperty("class", "card")
        f_layout = QFormLayout(form_card)
        f_layout.setSpacing(10)

        self.input_api_id = QLineEdit()
        self.input_api_id.setPlaceholderText("e.g. 1234567")
        if config.TG_API_ID:
            self.input_api_id.setText(str(config.TG_API_ID))
        f_layout.addRow("<b>API ID:</b>", self.input_api_id)

        self.input_api_hash = QLineEdit()
        self.input_api_hash.setPlaceholderText("e.g. 893cafd78a2aa537006ae69bc2eb3348")
        if config.TG_API_HASH:
            self.input_api_hash.setText(config.TG_API_HASH)
        f_layout.addRow("<b>API Hash:</b>", self.input_api_hash)

        self.input_phone = QLineEdit()
        self.input_phone.setPlaceholderText("e.g. +8801723383575")
        if config.TG_PHONE:
            self.input_phone.setText(config.TG_PHONE)
        f_layout.addRow("<b>Phone Number:</b>", self.input_phone)

        # Output folder row
        folder_row = QHBoxLayout()
        self.input_dir = QLineEdit()
        self.input_dir.setText(str(config.DEFAULT_DOWNLOAD_DIR))
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_dir)
        folder_row.addWidget(self.input_dir)
        folder_row.addWidget(btn_browse)
        f_layout.addRow("<b>Download Directory:</b>", folder_row)

        layout.addWidget(form_card)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Save & Connect")
        btn_save.setProperty("class", "primary")
        btn_save.clicked.connect(self._save_and_accept)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

    def _browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", self.input_dir.text())
        if folder:
            self.input_dir.setText(folder)

    def _save_and_accept(self):
        api_id_str = self.input_api_id.text().strip()
        api_hash = self.input_api_hash.text().strip()
        phone = self.input_phone.text().strip()
        d_dir = self.input_dir.text().strip()

        if not api_id_str or not api_id_str.isdigit():
            QMessageBox.warning(self, "Validation Error", "Please enter a valid numeric API ID.")
            return
        if not api_hash:
            QMessageBox.warning(self, "Validation Error", "Please enter your API Hash.")
            return
        if not phone or not phone.startswith("+"):
            QMessageBox.warning(self, "Validation Error", "Please enter your phone number with country code (e.g. +1... or +880...).")
            return

        config.save_env_credentials(
            api_id=int(api_id_str),
            api_hash=api_hash,
            phone=phone,
            download_dir=d_dir,
        )
        self.accept()


# ==============================================================================
# Background Async Worker (Downloads & Telegram Lifecycle via Qt Signals)
# ==============================================================================
class DownloadWorker(QThread):
    sig_status = Signal(str)
    sig_auth_code_required = Signal(str)      # Prompt code: sends phone number
    sig_auth_password_required = Signal()    # Prompt 2FA password
    sig_authenticated = Signal(str, str)     # User name, username
    sig_auth_failed = Signal(str)
    sig_batch_started = Signal(int)          # total items
    sig_item_started = Signal(int, str, str, int) # task_idx, filename, channel, size
    sig_item_progress = Signal(int, int, int, str, str) # task_idx, done, total, speed, eta
    sig_item_completed = Signal(int, str, str) # task_idx, status, msg
    sig_batch_completed = Signal(list)       # list of results

    def __init__(self, targets: List[LinkTarget], engine: DownloaderEngine):
        super().__init__()
        self.targets = targets
        self.engine = engine
        self.is_cancelled = False
        self.manager: Optional[TelegramManager] = None
        self._code_response: Optional[str] = None
        self._password_response: Optional[str] = None
        self._code_event = asyncio.Event()
        self._password_event = asyncio.Event()

    def set_auth_code(self, code: str):
        self._code_response = code
        self._code_event.set()

    def set_auth_password(self, password: str):
        self._password_response = password
        self._password_event.set()

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        """Runs the asyncio event loop inside this worker thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._execute())
        finally:
            loop.close()

    async def _code_callback(self) -> str:
        self._code_event.clear()
        self.sig_auth_code_required.emit(config.TG_PHONE)
        await self._code_event.wait()
        return self._code_response or ""

    async def _password_callback(self) -> str:
        self._password_event.clear()
        self.sig_auth_password_required.emit()
        await self._password_event.wait()
        return self._password_response or ""

    async def _execute(self):
        self.sig_status.emit("Connecting to Telegram MTProto session...")
        self.manager = TelegramManager()

        try:
            await self.manager.initialize(
                code_callback=self._code_callback,
                password_callback=self._password_callback,
            )
            me = await self.manager.get_me()
            first = me.get("first_name", "") if isinstance(me, dict) else getattr(me, "first_name", "")
            last = me.get("last_name", "") if isinstance(me, dict) else getattr(me, "last_name", "")
            name = f"{first} {last}".strip() or "Telegram User"
            uname = (me.get("username", "") if isinstance(me, dict) else getattr(me, "username", "")) or ""
            self.sig_authenticated.emit(name, uname)
        except Exception as e:
            self.sig_auth_failed.emit(str(e))
            if self.manager:
                try:
                    await self.manager.disconnect()
                except Exception:
                    pass
            return

        if not self.targets:
            self.sig_status.emit("Ready. Enter links to download.")
            if self.manager:
                try:
                    await self.manager.disconnect()
                except Exception:
                    pass
            return

        try:
            self.sig_status.emit(f"Resolving {len(self.targets)} link target(s)...")
            video_items: List[VideoInfo] = []

            for target in self.targets:
                if self.is_cancelled:
                    break
                try:
                    items = await self.manager.fetch_videos_from_target(target)
                    video_items.extend(items)
                except Exception as err:
                    logger.error(f"Failed to fetch videos for target {target}: {err}")

            if self.is_cancelled:
                self.sig_status.emit("Download cancelled.")
                return

            if not video_items:
                self.sig_status.emit("No downloadable videos found in the provided links.")
                self.sig_batch_completed.emit([])
                return

            self.sig_batch_started.emit(len(video_items))
            self.sig_status.emit(f"Starting download of {len(video_items)} video(s)...")

            # Map each item to a row index
            item_indices = {id(item): idx for idx, item in enumerate(video_items)}
            last_progress_time: Dict[int, float] = {}
            last_bytes: Dict[int, int] = {}

            def make_callback(v_info: VideoInfo):
                row_idx = item_indices[id(v_info)]
                last_progress_time[row_idx] = time.time()
                last_bytes[row_idx] = 0

                def cb(downloaded: int, total: int):
                    if self.is_cancelled:
                        raise asyncio.CancelledError("User cancelled download")

                    now = time.time()
                    dt = now - last_progress_time.get(row_idx, now)
                    # Throttle UI signal to 5-10 Hz to keep GUI silky smooth
                    if dt >= 0.15 or downloaded == total:
                        db = downloaded - last_bytes.get(row_idx, 0)
                        speed_mb = (db / dt) / (1024 * 1024) if dt > 0 else 0
                        speed_str = f"{speed_mb:.1f} MB/s" if speed_mb > 0 else "-- MB/s"

                        remaining_bytes = total - downloaded
                        if speed_mb > 0.05 and remaining_bytes > 0:
                            eta_secs = int(remaining_bytes / (speed_mb * 1024 * 1024))
                            m, s = divmod(eta_secs, 60)
                            h, m = divmod(m, 60)
                            eta_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
                        else:
                            eta_str = "--:--"

                        last_progress_time[row_idx] = now
                        last_bytes[row_idx] = downloaded
                        self.sig_item_progress.emit(row_idx, downloaded, total, speed_str, eta_str)

                return cb

            for idx, item in enumerate(video_items):
                self.sig_item_started.emit(idx, item.filename, item.chat_title, item.file_size)

            def on_completed(res: DownloadResult):
                row_idx = item_indices.get(id(res.info), 0)
                err = res.error_message or ""
                self.sig_item_completed.emit(row_idx, res.status, err)

            results = await self.engine.download_batch(
                video_list=video_items,
                item_callback_factory=make_callback,
                on_item_completed=on_completed,
            )

            self.sig_batch_completed.emit(results)
        except Exception as e:
            self.sig_status.emit(f"Error during execution: {e}")
        finally:
            if self.manager:
                try:
                    await self.manager.disconnect()
                except Exception:
                    pass


# ==============================================================================
# Main Desktop GUI Window
# ==============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚡ Telegram Video Downloader Pro")
        self.resize(1020, 720)
        self.setMinimumSize(850, 600)
        self.setStyleSheet(DARK_STYLE)

        self.worker: Optional[DownloadWorker] = None
        self.results_cache: List[DownloadResult] = []
        self.failed_links_cache: List[str] = []

        self._build_ui()
        self._check_initial_auth()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # ----------------------------------------------------------------------
        # Header Bar
        # ----------------------------------------------------------------------
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("⚡ Telegram Video Downloader Pro")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_title.setStyleSheet("color: #ffffff;")
        title_box.addWidget(lbl_title)

        lbl_sub = QLabel("Direct MTProto Streaming • Private Channels • Batch & Ranges")
        lbl_sub.setStyleSheet("color: #7b8396; font-size: 11px;")
        title_box.addWidget(lbl_sub)
        header.addLayout(title_box)

        header.addStretch()

        # Account status pill
        self.lbl_account = QLabel("Checking session...")
        self.lbl_account.setStyleSheet(
            "background-color: #1e2430; border: 1px solid #2b3b52; "
            "border-radius: 12px; padding: 5px 12px; color: #5dade2; font-weight: bold;"
        )
        header.addWidget(self.lbl_account)

        self.btn_switch_acc = QPushButton("⚙️ Setup / Account")
        self.btn_switch_acc.clicked.connect(self._open_setup_dialog)
        header.addWidget(self.btn_switch_acc)

        main_layout.addLayout(header)

        # ----------------------------------------------------------------------
        # Links Input Card
        # ----------------------------------------------------------------------
        input_card = QFrame()
        input_card.setProperty("class", "card")
        in_layout = QVBoxLayout(input_card)
        in_layout.setSpacing(8)

        in_header = QHBoxLayout()
        lbl_in = QLabel("📥 Telegram Links or Ranges")
        lbl_in.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lbl_in.setStyleSheet("color: #4db3ff;")
        in_header.addWidget(lbl_in)
        in_header.addStretch()

        # Action buttons
        btn_paste_clip = QPushButton("📋 Auto-Paste Clipboard")
        btn_paste_clip.setStyleSheet("background-color: #1e3552; border-color: #2b5080; color: #66b2ff;")
        btn_paste_clip.clicked.connect(self._paste_clipboard)
        in_header.addWidget(btn_paste_clip)

        btn_import = QPushButton("📂 Import File (.txt)")
        btn_import.clicked.connect(self._import_file)
        in_header.addWidget(btn_import)

        btn_clear = QPushButton("🧹 Clear")
        btn_clear.clicked.connect(self._clear_input)
        in_header.addWidget(btn_clear)

        in_layout.addLayout(in_header)

        self.txt_links = QTextEdit()
        self.txt_links.setPlaceholderText(
            "Paste Telegram post links here...\n"
            "Supported formats:\n"
            "  • Single private link:  https://t.me/c/3100538760/15\n"
            "  • Range of messages:    https://t.me/c/3100538760/15-30\n"
            "  • Public channel post:  https://t.me/channel_name/42\n"
            "  • Multiple links separated by newlines, spaces, or commas"
        )
        self.txt_links.setMaximumHeight(105)
        in_layout.addWidget(self.txt_links)

        main_layout.addWidget(input_card)

        # ----------------------------------------------------------------------
        # Preferences Bar Card
        # ----------------------------------------------------------------------
        pref_card = QFrame()
        pref_card.setProperty("class", "card")
        pref_layout = QVBoxLayout(pref_card)
        pref_layout.setSpacing(8)

        # Directory Row
        dir_row = QHBoxLayout()
        lbl_dir = QLabel("📁 Download To:")
        lbl_dir.setFont(QFont("Segoe UI", 10, QFont.Bold))
        dir_row.addWidget(lbl_dir)

        self.input_download_dir = QLineEdit()
        self.input_download_dir.setText(str(config.DEFAULT_DOWNLOAD_DIR))
        dir_row.addWidget(self.input_download_dir)

        btn_browse_dest = QPushButton("Browse...")
        btn_browse_dest.clicked.connect(self._browse_dest)
        dir_row.addWidget(btn_browse_dest)
        pref_layout.addLayout(dir_row)

        # Checkboxes & Concurrency Row
        opt_row = QHBoxLayout()
        self.chk_subfolders = QCheckBox("📁 Organize by Channel Subfolders")
        self.chk_subfolders.setChecked(config.SUBFOLDERS_BY_CHANNEL)
        opt_row.addWidget(self.chk_subfolders)

        self.chk_captions = QCheckBox("📝 Save Post Captions (.txt)")
        self.chk_captions.setChecked(config.SAVE_CAPTIONS)
        opt_row.addWidget(self.chk_captions)

        self.chk_chime = QCheckBox("🔔 Completion Chime")
        self.chk_chime.setChecked(config.PLAY_CHIME)
        opt_row.addWidget(self.chk_chime)

        opt_row.addStretch()

        lbl_threads = QLabel("⚡ Parallel Videos:")
        opt_row.addWidget(lbl_threads)
        self.spin_concurrency = QSpinBox()
        self.spin_concurrency.setRange(1, 20)
        self.spin_concurrency.setValue(config.DEFAULT_CONCURRENCY)
        opt_row.addWidget(self.spin_concurrency)

        pref_layout.addLayout(opt_row)
        main_layout.addWidget(pref_card)

        # ----------------------------------------------------------------------
        # Big Start Action Button
        # ----------------------------------------------------------------------
        action_row = QHBoxLayout()
        self.btn_start = QPushButton("⚡ Start Download")
        self.btn_start.setProperty("class", "primary")
        self.btn_start.setFixedHeight(42)
        self.btn_start.clicked.connect(self._start_download)
        action_row.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("⏹️ Cancel")
        self.btn_cancel.setProperty("class", "danger")
        self.btn_cancel.setFixedHeight(42)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_download)
        action_row.addWidget(self.btn_cancel)

        main_layout.addLayout(action_row)

        # ----------------------------------------------------------------------
        # Multi-File Downloads Table
        # ----------------------------------------------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Status", "File Name", "Channel", "Size", "Progress", "Speed", "ETA"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 180)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        main_layout.addWidget(self.table)

        # ----------------------------------------------------------------------
        # Bottom Status & Failed Retry Bar
        # ----------------------------------------------------------------------
        self.footer_card = QFrame()
        self.footer_card.setProperty("class", "card")
        footer_layout = QHBoxLayout(self.footer_card)
        footer_layout.setContentsMargins(8, 6, 8, 6)

        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setStyleSheet("color: #a0a8ba; font-weight: 500;")
        footer_layout.addWidget(self.lbl_status)

        footer_layout.addStretch()

        self.btn_retry_failed = QPushButton("🔁 Retry Failed (0)")
        self.btn_retry_failed.setStyleSheet("background-color: #8c2a2a; border-color: #a63232; color: #ffffff;")
        self.btn_retry_failed.setVisible(False)
        self.btn_retry_failed.clicked.connect(self._retry_failed)
        footer_layout.addWidget(self.btn_retry_failed)

        main_layout.addWidget(self.footer_card)

    # --------------------------------------------------------------------------
    # Initial Auth & Setup
    # --------------------------------------------------------------------------
    def _check_initial_auth(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1500)

        valid, msg = config.validate_config()
        if not valid:
            self.lbl_account.setText("🔴 Not Configured")
            self.lbl_status.setText("Configuration missing. Please set up your Telegram credentials.")
            QTimer.singleShot(400, self._open_setup_dialog)
        else:
            self.lbl_status.setText("Initializing session...")
            # Run quick connect worker
            self.worker = DownloadWorker(targets=[], engine=DownloaderEngine(self.input_download_dir.text()))
            self.worker.sig_authenticated.connect(self._on_auth_success)
            self.worker.sig_auth_failed.connect(self._on_auth_failed)
            self.worker.sig_auth_code_required.connect(self._prompt_code)
            self.worker.sig_auth_password_required.connect(self._prompt_password)
            self.worker.start()

    def _open_setup_dialog(self):
        dlg = CredentialsGuideDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.input_download_dir.setText(str(config.DEFAULT_DOWNLOAD_DIR))
            self._check_initial_auth()

    # --------------------------------------------------------------------------
    # Auth Callback Slots
    # --------------------------------------------------------------------------
    @Slot(str, str)
    def _on_auth_success(self, name: str, username: str):
        uname_str = f" (@{username})" if username else ""
        self.lbl_account.setText(f"🟢 {name}{uname_str}")
        self.lbl_status.setText("Connected to Telegram MTProto session.")

    @Slot(str)
    def _on_auth_failed(self, error_msg: str):
        self.lbl_account.setText("🔴 Auth Failed")
        self.lbl_status.setText(f"Authentication error: {error_msg}")
        QMessageBox.critical(
            self, "Telegram Authentication Failed",
            f"Could not connect with current credentials:\n\n{error_msg}\n\nPlease verify your API ID, Hash, and Phone."
        )

    @Slot(str)
    def _prompt_code(self, phone: str):
        code, ok = QInputDialog.getText(
            self, "Telegram Verification Code",
            f"Telegram sent an official login code to your Telegram app / SMS ({phone}):\n\nEnter code:"
        )
        if ok and code.strip():
            self.worker.set_auth_code(code.strip())
        else:
            self.worker.set_auth_code("")

    @Slot()
    def _prompt_password(self):
        pwd, ok = QInputDialog.getText(
            self, "Two-Step Verification (2FA)",
            "Your Telegram account has 2FA enabled.\nEnter your cloud password:",
            QLineEdit.Password
        )
        if ok and pwd:
            self.worker.set_auth_password(pwd)
        else:
            self.worker.set_auth_password("")

    # --------------------------------------------------------------------------
    # Clipboard & File Helpers
    # --------------------------------------------------------------------------
    def _paste_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if not text:
            QMessageBox.information(self, "Clipboard Empty", "Your clipboard is currently empty.")
            return

        targets = extract_targets_from_text(text)
        if targets:
            current = self.txt_links.toPlainText().strip()
            new_text = f"{current}\n{text}".strip() if current else text
            self.txt_links.setPlainText(new_text)
            self.lbl_status.setText(f"Pasted from clipboard ({len(targets)} Telegram target(s) detected).")
        else:
            current = self.txt_links.toPlainText().strip()
            self.txt_links.setPlainText(f"{current}\n{text}".strip() if current else text)
            self.lbl_status.setText("Pasted clipboard text.")

    def _import_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Links File", "", "Text Files (*.txt);;All Files (*.*)"
        )
        if file_path:
            try:
                content = Path(file_path).read_text(encoding="utf-8")
                self.txt_links.setPlainText(content)
                targets = extract_targets_from_text(content)
                self.lbl_status.setText(f"Loaded {len(targets)} target(s) from {Path(file_path).name}.")
            except Exception as e:
                QMessageBox.warning(self, "Import Error", f"Could not read file: {e}")

    def _clear_input(self):
        self.txt_links.clear()
        self.table.setRowCount(0)
        self.lbl_status.setText("Cleared.")
        self.btn_retry_failed.setVisible(False)

    def _browse_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", self.input_download_dir.text())
        if folder:
            self.input_download_dir.setText(folder)

    # --------------------------------------------------------------------------
    # Start / Cancel Download Handlers
    # --------------------------------------------------------------------------
    def _start_download(self):
        raw_text = self.txt_links.toPlainText().strip()
        if not raw_text:
            QMessageBox.information(self, "No Links", "Please paste or import Telegram post links first.")
            return

        targets = extract_targets_from_text(raw_text)
        if not targets:
            QMessageBox.warning(
                self, "Invalid Links",
                "No valid Telegram message links found.\n\n"
                "Example format: https://t.me/c/3100538760/15"
            )
            return

        out_path = Path(self.input_download_dir.text().strip())
        concurrency = self.spin_concurrency.value()
        subfolders = self.chk_subfolders.isChecked()
        captions = self.chk_captions.isChecked()
        chime = self.chk_chime.isChecked()

        engine = DownloaderEngine(
            out_dir=out_path,
            concurrency=concurrency,
            organize_by_channel=subfolders,
            save_captions=captions,
            play_chime=chime,
        )

        self.table.setRowCount(0)
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_retry_failed.setVisible(False)
        self.failed_links_cache.clear()

        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1500)

        self.worker = DownloadWorker(targets=targets, engine=engine)
        self.worker.sig_status.connect(self._on_status)
        self.worker.sig_authenticated.connect(self._on_auth_success)
        self.worker.sig_auth_failed.connect(self._on_auth_failed)
        self.worker.sig_auth_code_required.connect(self._prompt_code)
        self.worker.sig_auth_password_required.connect(self._prompt_password)
        self.worker.sig_batch_started.connect(self._on_batch_started)
        self.worker.sig_item_started.connect(self._on_item_started)
        self.worker.sig_item_progress.connect(self._on_item_progress)
        self.worker.sig_item_completed.connect(self._on_item_completed)
        self.worker.sig_batch_completed.connect(self._on_batch_completed)
        self.worker.start()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1500)
        event.accept()

    def _cancel_download(self):
        if self.worker:
            self.lbl_status.setText("Cancelling downloads...")
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)


    def _retry_failed(self):
        if not self.failed_links_cache:
            return
        self.txt_links.setPlainText("\n".join(self.failed_links_cache))
        self._start_download()

    # --------------------------------------------------------------------------
    # Progress & Completion Slots
    # --------------------------------------------------------------------------
    @Slot(str)
    def _on_status(self, msg: str):
        self.lbl_status.setText(msg)

    @Slot(int)
    def _on_batch_started(self, count: int):
        self.table.setRowCount(count)
        for i in range(count):
            self.table.setItem(i, 0, QTableWidgetItem("⏳ Queued"))
            self.table.setItem(i, 1, QTableWidgetItem("Resolving..."))
            self.table.setItem(i, 2, QTableWidgetItem("--"))
            self.table.setItem(i, 3, QTableWidgetItem("--"))

            pbar = QProgressBar()
            pbar.setRange(0, 100)
            pbar.setValue(0)
            self.table.setCellWidget(i, 4, pbar)

            self.table.setItem(i, 5, QTableWidgetItem("--"))
            self.table.setItem(i, 6, QTableWidgetItem("--"))

    @Slot(int, str, str, int)
    def _on_item_started(self, row: int, filename: str, channel: str, size: int):
        self.table.setItem(row, 0, QTableWidgetItem("⚡ Downloading"))
        self.table.setItem(row, 1, QTableWidgetItem(filename))
        self.table.setItem(row, 2, QTableWidgetItem(channel))
        size_mb = f"{size / (1024 * 1024):.1f} MB" if size else "Unknown"
        self.table.setItem(row, 3, QTableWidgetItem(size_mb))

    @Slot(int, int, int, str, str)
    def _on_item_progress(self, row: int, done: int, total: int, speed: str, eta: str):
        pbar = self.table.cellWidget(row, 4)
        if isinstance(pbar, QProgressBar) and total > 0:
            percent = int((done / total) * 100)
            pbar.setValue(percent)
            pbar.setFormat(f"{percent}% ({done / (1024*1024):.1f}MB)")

        self.table.setItem(row, 5, QTableWidgetItem(speed))
        self.table.setItem(row, 6, QTableWidgetItem(eta))

    @Slot(int, str, str)
    def _on_item_completed(self, row: int, status: str, err: str):
        pbar = self.table.cellWidget(row, 4)
        if status == "SUCCESS":
            self.table.setItem(row, 0, QTableWidgetItem("✅ Done"))
            if isinstance(pbar, QProgressBar):
                pbar.setValue(100)
                pbar.setStyleSheet("QProgressBar::chunk { background-color: #00c853; }")
            self.table.setItem(row, 5, QTableWidgetItem("Finished"))
            self.table.setItem(row, 6, QTableWidgetItem("00:00"))
        elif status == "SKIPPED":
            self.table.setItem(row, 0, QTableWidgetItem("⏩ Skipped (Exists)"))
            if isinstance(pbar, QProgressBar):
                pbar.setValue(100)
                pbar.setStyleSheet("QProgressBar::chunk { background-color: #5dade2; }")
            self.table.setItem(row, 5, QTableWidgetItem("--"))
            self.table.setItem(row, 6, QTableWidgetItem("--"))
        else:
            self.table.setItem(row, 0, QTableWidgetItem("❌ Failed"))
            if isinstance(pbar, QProgressBar):
                pbar.setStyleSheet("QProgressBar::chunk { background-color: #ff5252; }")
            self.table.setItem(row, 5, QTableWidgetItem("Failed"))
            self.table.setItem(row, 6, QTableWidgetItem(err[:25] if err else "Error"))

    @Slot(list)
    def _on_batch_completed(self, results: List[DownloadResult]):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.results_cache = results

        success_count = sum(1 for r in results if r.status in ("SUCCESS", "SKIPPED"))
        failed_items = [r for r in results if r.status == "FAILED"]

        total_bytes = sum(r.bytes_downloaded for r in results)
        mb = total_bytes / (1024 * 1024)

        if failed_items:
            self.failed_links_cache = [
                f"https://t.me/c/{abs(r.info.chat_id)}/{r.info.message_id}"
                for r in failed_items if r.info
            ]
            self.btn_retry_failed.setText(f"🔁 Retry Failed ({len(failed_items)})")
            self.btn_retry_failed.setVisible(True)
            self.lbl_status.setText(
                f"Batch finished: {success_count} succeeded, {len(failed_items)} failed. Total: {mb:.1f} MB."
            )
        else:
            self.btn_retry_failed.setVisible(False)
            self.lbl_status.setText(
                f"🎉 All {success_count} video(s) completed successfully! Total transferred: {mb:.1f} MB."
            )


def main():
    # Enable high-DPI scaling on Windows
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
