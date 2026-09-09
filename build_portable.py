"""
Build Script for Telegram Video Downloader Pro
Compiles the application into a standalone portable Windows package using PyInstaller.
No Python installation required for end-users or community sharing.
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path

# Fix Windows CP1252 terminal encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def main():
    print("==================================================================")
    print("       * Building Telegram Video Downloader Pro Portable         ")
    print("==================================================================")

    project_dir = Path(__file__).parent.resolve()
    os.chdir(project_dir)

    dist_dir = project_dir / "dist"
    build_dir = project_dir / "build"
    portable_dir = dist_dir / "TelegramDownloader-Portable"

    # Clean previous builds
    print("\n[1/4] Cleaning previous build artifacts...")
    if portable_dir.exists():
        shutil.rmtree(portable_dir, ignore_errors=True)

    # PyInstaller command arguments
    print("\n[2/4] Compiling with PyInstaller (PySide6 + MTProto Engine)...")
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=TelegramDownloader",
        "--windowed",                 # No background cmd window
        "--onedir",                   # Instant startup portable folder
        "--clean",
        "--noconfirm",
        "--collect-all=telethon",
        "--collect-all=cryptg",
        "--collect-all=rich",
        "--collect-all=PySide6",
        "--add-data=.env.example;.",
        "--exclude-module=PyQt5",
        "--exclude-module=PyQt6",
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=scipy",
        "--exclude-module=pandas",
        "--exclude-module=torch",
        "--exclude-module=torchvision",
        "--exclude-module=torchaudio",
        "--exclude-module=IPython",
        "--exclude-module=notebook",
        "--exclude-module=jupyter",
        "--exclude-module=sympy",
        "--exclude-module=seaborn",
        "--exclude-module=scikit-learn",
        "main.py",
    ]

    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("\n[ERROR] PyInstaller compilation failed!")
        sys.exit(res.returncode)

    # Organize into clean portable folder
    print("\n[3/4] Organizing Portable distribution folder...")
    compiled_folder = dist_dir / "TelegramDownloader"
    if compiled_folder.exists():
        compiled_folder.rename(portable_dir)

    # Copy companion files
    if (project_dir / ".env.example").exists():
        shutil.copy(project_dir / ".env.example", portable_dir / ".env.example")
    if (project_dir / "README.md").exists():
        shutil.copy(project_dir / "README.md", portable_dir / "README.md")

    # Create user-friendly QuickStart README.txt
    readme_txt = (
        "==============================================================================\n"
        "                ⚡ TELEGRAM VIDEO DOWNLOADER PRO (PORTABLE)\n"
        "==============================================================================\n\n"
        "How to Run:\n"
        "  1. Double-click 'TelegramDownloader.exe' to launch the application.\n"
        "  2. On first run, the built-in Setup Wizard will guide you to connect\n"
        "     your Telegram account in under 30 seconds.\n"
        "  3. Paste any private channel link (e.g. https://t.me/c/3100538760/15),\n"
        "     ranges (15-30), or bulk URLs and click 'Start Download'!\n\n"
        "Requirements:\n"
        "  • Windows 10 or Windows 11 (64-bit).\n"
        "  • No Python installation or command line knowledge required.\n\n"
        "==============================================================================\n"
    )
    (portable_dir / "README.txt").write_text(readme_txt, encoding="utf-8")

    # Create empty downloads folder
    (portable_dir / "downloads").mkdir(exist_ok=True)

    # Create ZIP archive for easy sharing
    print("\n[4/4] Creating distribution ZIP archive for community sharing...")
    zip_output = dist_dir / "TelegramDownloader-v1.0-Portable-x64"
    shutil.make_archive(str(zip_output), "zip", root_dir=dist_dir, base_dir="TelegramDownloader-Portable")

    print("\n==================================================================")
    print(" [SUCCESS] Portable package built successfully!")
    print(f" Folder: {portable_dir}")
    print(f" ZIP:    {zip_output}.zip")
    print("==================================================================\n")

if __name__ == "__main__":
    main()
