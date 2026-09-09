"""
Configuration and Environment Management
"""

import re
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TG_API_ID = int(os.getenv("TG_API_ID", "0") or "0")
TG_API_HASH = os.getenv("TG_API_HASH", "").strip()
TG_PHONE = os.getenv("TG_PHONE", "").strip()

# Internal session database name (stored locally as tg_session.session)
SESSION_NAME = "tg_session"


def parse_download_dir(raw: str | None = None) -> Path:
    r"""
    Parses and normalizes download directory path from .env or argument.
    Supports Windows drive letters (e.g., M:\, D:/Videos, C:), relative paths,
    and quoted strings.
    """
    if not raw:
        raw = (
            os.getenv("DOWNLOAD_DIR")
            or os.getenv("DOWNLOAD_PATH")
            or os.getenv("DOWNLOAD_FOLDER")
            or os.getenv("TG_DOWNLOAD_DIR")
            or "downloads"
        )
    
    clean = str(raw).strip().strip("\"'")
    
    # Handle single drive letters like "M:" -> "M:\"
    if re.match(r"^[a-zA-Z]:$", clean):
        clean += "\\"

    # Expand user directory (e.g., ~/Downloads)
    clean = os.path.expanduser(clean)
    
    return Path(clean)


DEFAULT_DOWNLOAD_DIR = parse_download_dir()
DEFAULT_CONCURRENCY = int(os.getenv("CONCURRENCY", "10"))
SUBFOLDERS_BY_CHANNEL = os.getenv("SUBFOLDERS_BY_CHANNEL", "true").lower() in ("true", "1", "yes")
SAVE_CAPTIONS = os.getenv("SAVE_CAPTIONS", "true").lower() in ("true", "1", "yes")
PLAY_CHIME = os.getenv("PLAY_CHIME", "true").lower() in ("true", "1", "yes")


def validate_config() -> tuple[bool, str]:
    """Check if the required Telegram API credentials are provided in .env"""
    if not TG_API_ID:
        return False, "TG_API_ID is missing or invalid in .env"
    if not TG_API_HASH:
        return False, "TG_API_HASH is missing in .env"
    if not TG_PHONE:
        return False, "TG_PHONE is missing in .env"
    return True, "Configuration valid"


def save_env_credentials(
    api_id: int | str,
    api_hash: str,
    phone: str,
    download_dir: str | None = None,
    env_path: str = ".env",
) -> None:
    """Writes credentials to .env file and reloads the active configuration."""
    global TG_API_ID, TG_API_HASH, TG_PHONE, DEFAULT_DOWNLOAD_DIR

    lines = [
        f"TG_API_ID={api_id}",
        f"TG_API_HASH={str(api_hash).strip()}",
        f"TG_PHONE={str(phone).strip()}",
    ]
    if download_dir:
        lines.append(f"DOWNLOAD_DIR={str(download_dir).strip()}")

    Path(env_path).write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Reload into active memory
    load_dotenv(override=True)
    TG_API_ID = int(os.getenv("TG_API_ID", "0") or "0")
    TG_API_HASH = os.getenv("TG_API_HASH", "").strip()
    TG_PHONE = os.getenv("TG_PHONE", "").strip()
    if download_dir:
        DEFAULT_DOWNLOAD_DIR = parse_download_dir()


