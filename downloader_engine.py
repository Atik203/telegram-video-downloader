"""
Downloader Engine
Handles chunked MTProto streaming, progress callbacks, FloodWait handling,
Windows filename sanitization, and concurrent batch processing.
"""

import asyncio
import os
import re
import time
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, List

from telethon.errors import FloodWaitError
from client_manager import VideoInfo
from fast_download import fast_download_file

logger = logging.getLogger("tg-downloader.engine")


def sanitize_filename(name: str, max_length: int = 150) -> str:
    r"""
    Sanitize filename for Windows filesystem compatibility.
    Removes invalid characters: < > : " / \ | ? * and ASCII control characters.
    """
    # Replace invalid chars with underscore
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    # Remove leading/trailing spaces and dots (problematic on Windows)
    sanitized = sanitized.strip(" .")
    if not sanitized:
        sanitized = "telegram_video.mp4"

    # Clean double extensions (e.g., .mp4.mp4, .mkv.mkv)
    for ext in [".mp4", ".mkv", ".webm", ".avi", ".mov", ".ts"]:
        double_ext = f"{ext}{ext}"
        while sanitized.lower().endswith(double_ext):
            sanitized = sanitized[:-len(ext)]

    if len(sanitized) > max_length:
        stem = Path(sanitized).stem[:max_length - 8]
        ext = Path(sanitized).suffix
        sanitized = f"{stem}{ext}"
    return sanitized


@dataclass
class DownloadResult:
    info: VideoInfo
    status: str  # "SUCCESS", "SKIPPED", "FAILED"
    file_path: Optional[Path] = None
    bytes_downloaded: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None


class DownloaderEngine:
    def __init__(
        self,
        out_dir: Path | str,
        concurrency: int = 10,
        organize_by_channel: bool = True,
        save_captions: bool = True,
        play_chime: bool = True,
    ):
        self.out_dir = Path(out_dir)
        self.concurrency = concurrency
        self.semaphore = asyncio.Semaphore(concurrency)
        self.organize_by_channel = organize_by_channel
        self.save_captions = save_captions
        self.play_chime = play_chime

    def check_free_space(self, required_bytes: int) -> tuple[bool, int, int]:
        """Returns (has_enough_space, free_bytes, total_bytes)"""
        import shutil
        try:
            check_dir = self.out_dir if self.out_dir.exists() else self.out_dir.parent
            usage = shutil.disk_usage(check_dir)
            return (usage.free >= required_bytes, usage.free, usage.total)
        except Exception:
            return (True, 0, 0)

    def get_dest_path(self, info: VideoInfo) -> Path:
        """Computes a unique, sanitized target filepath, optionally nested by channel."""
        clean_name = sanitize_filename(info.filename)
        unique_name = f"{info.chat_id}_{info.message_id}_{clean_name}"

        target_dir = self.out_dir
        if self.organize_by_channel and info.chat_title:
            safe_channel = sanitize_filename(info.chat_title)
            if safe_channel:
                target_dir = self.out_dir / safe_channel

        return target_dir / unique_name

    async def download_video(
        self,
        info: VideoInfo,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        retries: int = 3,
    ) -> DownloadResult:
        """
        Download a single video file using direct MTProto streaming with resume support.
        Bypasses client-side 'restrict saving content' restrictions.
        """
        target_path = self.get_dest_path(info)

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to access/create directory {target_path.parent}: {e}")
            return DownloadResult(
                info=info,
                status="FAILED",
                error_message=f"Cannot access output directory '{target_path.parent}': {e}",
            )

        # Check if already fully downloaded
        if target_path.exists():
            disk_size = target_path.stat().st_size
            if info.file_size > 0 and disk_size == info.file_size:
                logger.info(f"Skipping already downloaded file: {target_path.name}")
                if progress_callback and info.file_size:
                    progress_callback(info.file_size, info.file_size)
                return DownloadResult(
                    info=info,
                    status="SKIPPED",
                    file_path=target_path,
                    bytes_downloaded=disk_size,
                )

        start_time = time.time()
        temp_path = target_path.with_suffix(target_path.suffix + ".part")
        state_path = target_path.with_suffix(target_path.suffix + ".part.json")

        async with self.semaphore:
            for attempt in range(1, retries + 1):
                try:
                    # Attempt high-speed parallel chunk download with resume
                    downloaded_file = None
                    msg = info.message_obj
                    media = getattr(msg, "document", None) or getattr(msg, "video", None)
                    client = getattr(msg, "_client", None)

                    if client and media and getattr(media, "size", 0) > 256 * 1024:
                        try:
                            file_mode = "r+b" if temp_path.exists() else "w+b"
                            with open(temp_path, file_mode) as f:
                                await fast_download_file(
                                    client=client,
                                    location=media,
                                    out_file=f,
                                    file_size=media.size,
                                    progress_callback=progress_callback,
                                    state_file=state_path,
                                )
                            if temp_path.exists() and temp_path.stat().st_size >= media.size:
                                downloaded_file = str(temp_path)
                        except asyncio.CancelledError:
                            raise
                        except Exception as fast_err:
                            logger.warning(
                                f"Parallel download interrupted/failed for msg {info.message_id} ({fast_err}); attempting fallback..."
                            )

                    # Fallback to standard MTProto download if fast stream was not used or failed
                    if not downloaded_file:
                        downloaded_file = await info.message_obj.download_media(
                            file=str(temp_path),
                            progress_callback=progress_callback,
                        )

                    if downloaded_file and Path(downloaded_file).exists():
                        # Clean up resume state file upon completion
                        if state_path.exists():
                            try:
                                state_path.unlink()
                            except Exception:
                                pass

                        # Rename part file to final file
                        if target_path.exists():
                            target_path.unlink()
                        Path(downloaded_file).rename(target_path)

                        # Save accompanying caption / notes if present
                        if self.save_captions and info.caption and info.caption.strip():
                            try:
                                caption_path = target_path.with_suffix(".txt")
                                content = (
                                    f"Channel: {info.chat_title or info.chat_id}\n"
                                    f"Message ID: {info.message_id}\n"
                                    f"File: {target_path.name}\n"
                                    f"{'-' * 50}\n\n"
                                    f"{info.caption.strip()}\n"
                                )
                                caption_path.write_text(content, encoding="utf-8")
                            except Exception as cap_err:
                                logger.warning(f"Could not save caption for msg {info.message_id}: {cap_err}")

                        duration = time.time() - start_time
                        file_size = target_path.stat().st_size

                        return DownloadResult(
                            info=info,
                            status="SUCCESS",
                            file_path=target_path,
                            bytes_downloaded=file_size,
                            duration_seconds=duration,
                        )
                    else:
                        raise RuntimeError("Download finished but target file not found.")

                except asyncio.CancelledError:
                    raise
                except FloodWaitError as e:
                    logger.warning(
                        f"Telegram FloodWaitError: waiting {e.seconds}s before retrying msg {info.message_id}..."
                    )
                    await asyncio.sleep(e.seconds + 1)
                except Exception as e:
                    logger.error(
                        f"Attempt {attempt}/{retries} failed for msg {info.message_id}: {e}"
                    )
                    # Note: We intentionally preserve temp_path and state_path for future resumption
                    if attempt == retries:
                        return DownloadResult(
                            info=info,
                            status="FAILED",
                            error_message=str(e),
                            duration_seconds=time.time() - start_time,
                        )
                    await asyncio.sleep(2)

        return DownloadResult(
            info=info,
            status="FAILED",
            error_message="Unknown download failure",
        )

    async def download_batch(
        self,
        video_list: List[VideoInfo],
        item_callback_factory: Optional[Callable[[VideoInfo], Callable[[int, int], None]]] = None,
        on_item_completed: Optional[Callable[[DownloadResult], None]] = None,
    ) -> List[DownloadResult]:
        """
        Download multiple videos concurrently governed by self.semaphore.
        """
        results: List[DownloadResult] = []

        async def worker(v_info: VideoInfo):
            cb = item_callback_factory(v_info) if item_callback_factory else None
            res = await self.download_video(v_info, progress_callback=cb)
            if on_item_completed:
                on_item_completed(res)
            return res

        tasks = [asyncio.create_task(worker(v)) for v in video_list]
        if tasks:
            try:
                results = await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                for t in tasks:
                    if not t.done():
                        t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise

        if self.play_chime:
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

        return results
