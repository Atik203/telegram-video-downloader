# ⚡ Telegram Video Downloader Pro

[![CI Tests](https://github.com/Atik203/Telegram-Video-Downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/Atik203/Telegram-Video-Downloader/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078d7.svg)](https://microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A modern, high-performance Telegram video downloader featuring a **Desktop Graphical User Interface (GUI)**, interactive **Terminal User Interface (TUI)**, and **Headless CLI** optimized for Windows 10 & 11.

Download videos from **public channels**, **private channels / supergroups** (e.g., `https://t.me/c/3100538760/15`), single posts, post ranges, or bulk links — including channels with **"Restrict Saving Content"** (protected content) enabled, via direct MTProto streaming.

---

## ✨ Key Features

- 🖥️ **Modern Desktop GUI**: Sleek dark interface built with PySide6 (Qt) featuring real-time multi-file progress, smoothed transfer speed (MB/s), ETA, and status.
- 🎯 **Live Target Counter Badge**: Real-time link parsing and video count validation as you type or paste (`🎯 2 targets • 16 videos detected`).
- 📂 **Drag-and-Drop Import**: Simply drag and drop any `.txt` link file directly into the application window.
- ✨ **Interactive Range Generator**: Guided helper dialog to build sequential private or public message ranges (e.g. `15-30`) with live previews.
- 📂 **One-Click Folder Access**: "Open Folder" button right beside the destination field opens downloads directly in Windows File Explorer.
- 🧙 **In-App Setup Wizard**: Direct in-app guide showing where and how to get your `API_ID` and `API_HASH` from `my.telegram.org` with one click.
- 📦 **Portable Standalone Package (.exe)**: Run anywhere without needing Python installed on the machine.
- 📁 **Channel Subfolder Organization**: Automatically organizes downloads into subfolders by channel name (e.g. `M:\<Course_Name>\lesson.mp4`).
- 📝 **Caption & Lecture Notes Preservation**: Saves accompanying post text and descriptions into a `.txt` file alongside each video.
- 🔒 **Private Channel & Protected Content**: Direct MTProto streaming bypasses client-side saving restrictions (`noforwards`).
- 🚀 **10+ MB/s Fast Download Engine**: Parallel chunk pipeline saturating full broadband connection.
- 🔁 **Chunk-Level Partial Resume**: If an interrupted download stopped at 800MB out of 1GB, restarting downloads only the remaining 200MB!
- 📋 **Auto-Paste Clipboard**: Instantly detect and insert Telegram links copied to your Windows clipboard.
- 🔔 **Completion Chime**: Plays a subtle Windows notification chime when batch downloads finish.
- 💻 **Dual Mode**: Runs with modern Desktop GUI by default, with full headless CLI and Rich Terminal UI (`--cli`) support.

---

## 🚀 Quick Start

### Option A: Portable Standalone Executable (No Python Required)

1. Download the latest `TelegramDownloader-v1.0-Portable-x64.zip` from [Releases](https://github.com/Atik203/Telegram-Video-Downloader/releases).
2. Extract the archive and double-click **`TelegramDownloader.exe`**.
3. On first run, the built-in Setup Wizard will guide you through connecting your Telegram account in under 30 seconds!

### Option B: Run from Source via Python

1. **Clone and Install Dependencies**:
   ```bash
   git clone https://github.com/Atik203/Telegram-Video-Downloader.git
   cd Telegram-Video-Downloader
   pip install -r requirements.txt
   ```

2. **Launch Desktop GUI**:
   ```bash
   python main.py
   # or double-click run.bat
   ```

3. **Terminal Mode (Optional)**:
   ```bash
   # Launch Rich interactive terminal UI
   python main.py --cli

   # Or direct headless automation
   python main.py --url https://t.me/c/3100538760/15-20 --concurrency 10
   ```

---

## 🖥️ Interactive Terminal Menu Options

When launched in CLI mode (`python main.py --cli`), the interactive dashboard presents:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               ⚡ TELEGRAM PRIVATE & BATCH VIDEO DOWNLOADER ⚡               │
│       Download Private Posts • Protected Content • Multi-Video Ranges       │
└────────────────────────── Active MTProto Session ───────────────────────────┘
```

1. **📥 Download Single Post Link**:
   Paste a private or public post URL (e.g. `https://t.me/c/3100538760/15`).
2. **🔢 Download Post Range**:
   Specify a message range to download multiple sequential videos (e.g. `https://t.me/c/3100538760/15-30`).
3. **📋 Download Multiple Links**:
   Paste multiple URLs at once or provide a `links.txt` file.
4. **📁 Browse Joined Channels**:
   Interactively view your joined channels/groups and select messages to download.
5. **⚙️ Settings**:
   Change download directory or adjust concurrent worker threads.
6. **❌ Exit**:
   Disconnect MTProto session safely.

---

## 🤖 Headless / Command-Line Mode

Run downloads directly from scripts, batch files, or automated tasks:

```bash
# Download a single private post
python main.py --url https://t.me/c/3100538760/15

# Download a range from a private channel to a custom folder
python main.py --url https://t.me/c/3100538760/15-30 --out "my_videos"

# Download a batch of links listed in a text file with 5 workers
python main.py --file links.txt --concurrency 5
```

---

## 🛠️ Building the Standalone Executable

To compile your own portable Windows package:

```bash
python build_portable.py
# or double-click build_portable.bat
```

Outputs:
- Standalone Folder: `dist\TelegramDownloader-Portable\TelegramDownloader.exe`
- Distribution ZIP: `dist\TelegramDownloader-v1.0-Portable-x64.zip`

For automated and manual release steps, see [RELEASING.md](RELEASING.md).

---

## ⚠️ Important Notes

- **Private Channel Membership**: To download videos from private channel links (`https://t.me/c/...`), your Telegram account (`TG_PHONE`) **must already be a member** of that channel.
- **Security**: Never commit or share your `.env` or `*.session` files. See [SECURITY.md](SECURITY.md) for details.

---

## 🤝 Community & Contributing

- [CONTRIBUTING.md](CONTRIBUTING.md) — Development setup, testing, and pull request guidelines.
- [SECURITY.md](SECURITY.md) — Security policy and vulnerability reporting.
- [CHANGELOG.md](CHANGELOG.md) — Detailed version history and release notes.
- [RELEASING.md](RELEASING.md) — Release instructions and GitHub Actions automation.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
