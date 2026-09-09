# ⚡ Telegram Video Downloader Pro

A modern, high-performance Telegram video downloader with a **Desktop Graphical User Interface (GUI)** and an interactive **Terminal User Interface (TUI)** optimized for **Windows 10 & 11**.

Download videos from **public channels**, **private channels / supergroups** (e.g., `https://t.me/c/3100538760/15`), single posts, post ranges, or bulk links — including channels with **"Restrict Saving Content"** (protected content) enabled, via direct MTProto streaming.

---

## ✨ Key Features

- 🖥️ **Modern Desktop GUI**: Sleek dark interface built with PySide6 (Qt) featuring real-time multi-file progress, speed (MB/s), ETA, and status.
- 🧙 **In-App Setup Wizard**: Direct in-app guide showing where and how to get your `API_ID` and `API_HASH` from `my.telegram.org` with one click.
- 📦 **Portable Windows Standalone (.exe)**: Run anywhere without needing Python installed on the machine.
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
1. Run `build_portable.bat` to generate the portable package.
2. Open `dist\TelegramDownloader-Portable\` and double-click `TelegramDownloader.exe`.
3. The built-in Setup Wizard will guide you through connecting your account in 30 seconds!

### Option B: Run via Python

1. **Install Dependencies**:
   ```bash
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

When launched, the interactive dashboard presents:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               ⚡ TELEGRAM PRIVATE & BATCH VIDEO DOWNLOADER ⚡               │
│       Download Private Posts • Protected Content • Multi-Video Ranges       │
└────────────────────────── Active MTProto Session ───────────────────────────┘
```

1. **📥 Download Single Post Link**:
   Paste a private or public post URL, e.g.:
   - `https://t.me/c/3100538760/15`
   - `https://t.me/channel_name/42`
2. **🔢 Download Post Range**:
   Specify a message range to download multiple sequential videos:
   - `https://t.me/c/3100538760/15-30`
   - Or enter a link and specify start/end message IDs interactively.
3. **📋 Download Multiple Links**:
   Paste multiple URLs at once (separated by spaces or newlines) or provide a `links.txt` file.
4. **📁 Browse Joined Channels**:
   Interactively view your joined channels/groups, select one, and scan the last N messages or a specific range for videos.
5. **⚙️ Settings**:
   Change the default download folder (defaults to `downloads/`) or adjust concurrent download workers (default: 3).
6. **❌ Exit**:
   Disconnect safely.

---

## 🤖 Headless / Command-Line Mode

You can also run downloads directly from scripts or shortcuts without opening the menu:

```bash
# Download a single private post
python main.py --url https://t.me/c/3100538760/15

# Download a range from a private channel
python main.py --url https://t.me/c/3100538760/15-30 --out "my_videos"

# Download a batch of links listed in a text file
python main.py --file links.txt --concurrency 4
```

---

## ⚠️ Notes on Private Channels

- To download videos from private channel links (`https://t.me/c/...`), your Telegram account (`TG_PHONE`) **must already be a member** of that channel. Telegram's servers require account authorization before delivering message media.
- Telegram enforces server-side rate limits. Keeping concurrency between 2–5 avoids flood wait delays.
