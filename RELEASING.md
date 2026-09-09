# 🚀 How to Release Telegram Video Downloader

This guide explains how to release a new version of Telegram Video Downloader for community sharing.

---

## 📋 Pre-Release Checklist

Before creating a new release:
1. **Ensure all tests pass**:
   ```bash
   python -m unittest test_suite.py
   ```
2. **Verify `.gitignore` is active**:
   Make sure neither `.env` nor `*.session` are staged:
   ```bash
   git status
   ```
3. **Update `CHANGELOG.md`**:
   Document changes under the new version header (e.g. `## [1.0.0] - YYYY-MM-DD`).
4. **Commit all clean changes**:
   ```bash
   git add .
   git commit -m "chore: prepare release v1.0.0"
   git push origin main
   ```

---

## Method 1: Automated Release via GitHub Actions (Recommended)

This repository includes an automated release workflow in [`.github/workflows/release.yml`](.github/workflows/release.yml).

Whenever a tag starting with `v` (e.g. `v1.0.0`) is pushed to GitHub:
1. GitHub Actions launches a fresh Windows runner.
2. Installs Python and PyInstaller.
3. Automatically compiles `TelegramDownloader.exe` and packages `TelegramDownloader-v1.0-Portable-x64.zip`.
4. Creates an official **GitHub Release** and uploads the ZIP archive automatically!

### Steps to Trigger Automated Release:
```bash
# 1. Create a version tag
git tag v1.0.0

# 2. Push the tag to GitHub
git push origin v1.0.0
```
*That's it!* Head over to your repository's **Actions** tab to watch the build finish and publish your release.

---

## Method 2: Manual Release via GitHub Web Interface

If you prefer to build locally on your own machine and upload manually:

### 1. Build the Portable Package Locally:
Run the build script in your terminal:
```bash
python build_portable.py
```
This produces:
- `dist\TelegramDownloader-v1.0-Portable-x64.zip` (~72 MB)

### 2. Create the GitHub Release:
1. Go to your GitHub repository in your browser:
   `https://github.com/<YOUR_USERNAME>/<YOUR_REPO>/releases`
2. Click **"Draft a new release"** (or **"Create a new release"**).
3. In **"Choose a tag"**, type `v1.0.0` and click **"Create new tag: v1.0.0 on publish"**.
4. Set **Release title**:
   ```
   ⚡ Telegram Video Downloader Pro v1.0.0 (Portable Standalone)
   ```
5. In the description box, click **"Generate release notes"** or paste highlights from `CHANGELOG.md`:
   ```markdown
   ### Highlights:
   - 🖥️ Modern Dark Desktop GUI with PySide6 (Qt)
   - 🎯 Live Target Counter Badge & Real-Time Parsing Feedback
   - 📁 Drag-and-Drop .txt File Support & "Open Folder" Explorer Button
   - ✨ Interactive Message Range Generator Dialog
   - 🚀 Direct MTProto Streaming Engine with 10+ MB/s download speeds
   - 📦 Standalone Portable Windows binary (no Python needed)

   ### Download:
   Download `TelegramDownloader-v1.0-Portable-x64.zip` below, extract, and double-click `TelegramDownloader.exe`.
   ```
6. **Attach the Binary**:
   Drag and drop `dist\TelegramDownloader-v1.0-Portable-x64.zip` into the **"Attach binaries by dropping them here or selecting them"** box.
7. Click **"Publish release"**!

---

## 👥 How Community Users Install It

Once published, you can share the direct download link with anyone:
```
https://github.com/<YOUR_USERNAME>/<YOUR_REPO>/releases/latest
```
End users simply:
1. Download `TelegramDownloader-v1.0-Portable-x64.zip`.
2. Right-click -> Extract All.
3. Double-click **`TelegramDownloader.exe`**.
4. The built-in setup wizard guides them to connect their Telegram credentials in under 30 seconds!
