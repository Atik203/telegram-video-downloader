#!/usr/bin/env python3
"""
Telegram Video Downloader
--------------------------
Legacy entrypoint and CLI runner.
To run the full Interactive Terminal UI (TUI) in CMD or PowerShell, simply run:
    python main.py
or
    python downloader.py
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows CMD / PowerShell
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

import config
from main import interactive_loop, cli_mode
from client_manager import TelegramManager
from downloader_engine import DownloaderEngine


async def legacy_channel_run(channel: str, limit: int, out_dir: str, concurrency: int):
    manager = TelegramManager()
    await manager.initialize()
    target_out = config.parse_download_dir(out_dir) if out_dir else config.DEFAULT_DOWNLOAD_DIR
    engine = DownloaderEngine(out_dir=target_out, concurrency=concurrency)

    try:
        from ui import console, display_results_summary, create_progress_display
        console.print(f"[bold cyan]Scanning last {limit} messages in '{channel}'...[/bold cyan]")
        entity = await manager.resolve_entity(channel)
        title = getattr(entity, "title", str(channel))

        videos = []
        async for message in manager.client.iter_messages(entity, limit=limit):
            vinfo = manager.extract_video_info(message, title)
            if vinfo:
                videos.append(vinfo)

        if not videos:
            console.print(f"[yellow]No videos found in recent {limit} messages of '{channel}'.[/yellow]")
            return

        console.print(f"[green]Found {len(videos)} video(s). Starting download...[/green]")
        progress = create_progress_display()
        with progress:
            overall_task = progress.add_task("[bold green]Total", filename=f"{len(videos)} videos", total=len(videos))

            def make_cb(tid):
                return lambda curr, tot: progress.update(tid, completed=curr, total=tot)

            async def worker(v):
                tid = progress.add_task("[bold blue]Downloading", filename=v.filename[:35], total=v.file_size or 100)
                res = await engine.download_video(v, progress_callback=make_cb(tid))
                progress.update(tid, completed=res.bytes_downloaded, visible=False)
                progress.advance(overall_task, 1)
                return res

            tasks = [asyncio.create_task(worker(v)) for v in videos]
            results = await asyncio.gather(*tasks)

        display_results_summary(results, engine.out_dir)
    finally:
        await manager.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Download videos from Telegram channels/groups or post links.")
    parser.add_argument("--url", help="Post URL (e.g. https://t.me/c/3100538760/15 or /15-30)")
    parser.add_argument("--file", help="Path to text file containing links")
    parser.add_argument("--channel", help="Channel/group username (e.g. @somechannel) or numeric ID")
    parser.add_argument("--limit", type=int, default=50, help="How many recent messages to scan (default: 50)")
    parser.add_argument("--out", default=None, help="Output directory (default: from .env or 'downloads')")
    parser.add_argument("--concurrency", type=int, default=10, help="Max simultaneous downloads (default: 10)")
    args = parser.parse_args()

    # If no specific arguments provided, launch the rich interactive UI
    if len(sys.argv) == 1:
        asyncio.run(interactive_loop())
    elif args.channel:
        asyncio.run(legacy_channel_run(args.channel, args.limit, args.out, args.concurrency))
    else:
        asyncio.run(cli_mode(args))


if __name__ == "__main__":
    main()
