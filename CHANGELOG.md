# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-09

### Added
- **Desktop Graphical User Interface (GUI):**
  - Modern PySide6 (Qt) dark theme styled with Telegram Desktop & Fluent aesthetics.
  - Multi-file live progress table showing filename, channel name, size, percentage, speed, and ETA.
  - Dynamic **Live Target Counter** badge with real-time video detection feedback.
  - **Drag-and-Drop** support for `.txt` link files directly onto the window.
  - **✨ Add Range Helper Dialog** for guided private and public channel range creation.
  - **📂 Open Folder** one-click Windows Explorer launcher.
  - **📋 Auto-Paste Clipboard** button for rapid URL importing.
  - In-App Setup Wizard with clickable `my.telegram.org` browser launcher.
- **High-Speed MTProto Streaming Engine:**
  - Parallel chunk pipeline supporting 10–20 concurrent connections.
  - Dynamic Exponential Moving Average (EMA) speed smoothing for rock-solid throughput reporting.
  - Chunk-level partial download resumption via JSON state files.
  - Channel subfolder organization (`M:\<Channel>\<Video>.mp4`).
  - Caption and post description preservation (`.txt`).
  - Subtle Windows completion chime on batch completion.
- **Standalone Windows Distribution:**
  - PyInstaller portable build system generating standalone `TelegramDownloader.exe` and `.zip` archive.
  - No Python runtime or terminal required for end users.
- **Developer & CI Infrastructure:**
  - Full GitHub Actions CI pipeline running unit tests on Python 3.10, 3.11, 3.12.
  - Automated Release workflow publishing portable ZIP archives to GitHub Releases on tag push.
  - Standard issue and PR templates, `CONTRIBUTING.md`, and `SECURITY.md`.
