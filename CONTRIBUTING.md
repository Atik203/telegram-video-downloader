# Contributing to Telegram Video Downloader

Thank you for your interest in contributing to Telegram Video Downloader! We welcome bug reports, feature requests, documentation improvements, and pull requests from the community.

---

## Development Setup

1. **Fork and Clone the Repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Telegram-Downloader.git
   cd Telegram-Downloader
   ```

2. **Create a Virtual Environment:**
   ```bash
   python -m venv venv
   # On Windows (PowerShell / Command Prompt):
   .\venv\Scripts\activate
   # On Linux / macOS:
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller  # Only needed if building portable binaries
   ```

4. **Environment Configuration:**
   Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
   Add your `TG_API_ID`, `TG_API_HASH`, and `TG_PHONE` from [my.telegram.org](https://my.telegram.org).

---

## Running the Application

- **Desktop GUI Mode:**
  ```bash
  python main.py
  # or run.bat
  ```

- **Interactive Terminal UI:**
  ```bash
  python main.py --cli
  ```

- **Headless Mode:**
  ```bash
  python main.py --url https://t.me/c/3100538760/15
  ```

---

## Running Tests

Before submitting any code changes, ensure all tests pass:

```bash
python -m unittest test_suite.py
```

If you add new features (e.g. parser patterns or engine capabilities), please add corresponding test cases in `test_suite.py`.

---

## Building the Portable Standalone Package

To test or build the Windows portable distribution:

```bash
python build_portable.py
```
This generates:
- Standalone folder: `dist\TelegramDownloader-Portable\`
- Distribution ZIP: `dist\TelegramDownloader-v1.0-Portable-x64.zip`

---

## Submitting Pull Requests

1. Create a feature branch:
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. Commit your changes with clear, descriptive messages:
   ```bash
   git commit -m "feat: add support for custom download naming templates"
   ```
3. Push to your fork and submit a Pull Request against `main`.
4. Ensure your PR description clearly explains the changes and confirms that tests pass.
