"""
Telegram Video Downloader - Interactive TUI & CLI Entrypoint
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict

# Ensure UTF-8 output on Windows CMD / PowerShell
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.prompt import Prompt, IntPrompt, Confirm

import config
from link_parser import parse_telegram_link, extract_targets_from_text, ParsedTarget
from client_manager import TelegramManager, VideoInfo
from downloader_engine import DownloaderEngine, DownloadResult
import ui
from ui import console


async def process_and_download(
    manager: TelegramManager,
    targets: List[ParsedTarget],
    engine: DownloaderEngine,
):
    """
    Given a list of ParsedTargets, resolves entities, collects video metadata,
    and runs concurrent downloads with live Rich progress bars.
    """
    if not targets:
        console.print("[yellow]No targets provided.[/yellow]")
        return

    # Group message IDs by channel_ref to optimize entity resolution
    grouped_targets: Dict[any, List[int]] = {}
    target_raw_ids: Dict[any, int] = {}
    for t in targets:
        ref = t.channel_ref
        if ref not in grouped_targets:
            grouped_targets[ref] = []
            if t.raw_channel_id:
                target_raw_ids[ref] = t.raw_channel_id
        grouped_targets[ref].extend(t.message_ids)

    # De-duplicate message IDs per channel while preserving order
    for ref in grouped_targets:
        seen = set()
        deduped = []
        for mid in grouped_targets[ref]:
            if mid not in seen:
                seen.add(mid)
                deduped.append(mid)
        grouped_targets[ref] = deduped

    videos_to_download: List[VideoInfo] = []

    with console.status("[bold cyan]Inspecting Telegram channels and scanning messages...", spinner="dots"):
        for ref, msg_ids in grouped_targets.items():
            try:
                raw_id = target_raw_ids.get(ref)
                entity = await manager.resolve_entity(ref, raw_id)
                chat_title = getattr(entity, "title", str(ref))

                # Fetch in batches of 100
                chunk_size = 100
                for i in range(0, len(msg_ids), chunk_size):
                    chunk = msg_ids[i:i + chunk_size]
                    messages = await manager.get_messages(entity, chunk)
                    for msg in messages:
                        vinfo = manager.extract_video_info(msg, chat_title)
                        if vinfo:
                            videos_to_download.append(vinfo)
            except Exception as e:
                console.print(f"[bold red]Error fetching from channel {ref}:[/bold red] {e}")

    if not videos_to_download:
        console.print(
            Panel(
                "[yellow]No downloadable video files found in the requested message(s).[/yellow]\n"
                "• Check that the message IDs contain video files.\n"
                "• Make sure your account has joined the private channel if it's restricted.",
                border_style="yellow",
                title="No Media Found",
            )
        )
        return

    # Display discovered videos table
    ui.display_video_targets(videos_to_download)

    # Prompt confirmation if multiple
    if len(videos_to_download) > 1:
        if not Confirm.ask(f"[bold green]Proceed to download {len(videos_to_download)} video(s)?[/bold green]", default=True):
            console.print("[yellow]Download canceled by user.[/yellow]")
            return

    console.print(f"\n[bold green]Starting download to:[/bold green] [cyan]{engine.out_dir.resolve()}[/cyan]\n")

    # Set up multi-task live progress
    progress = ui.create_progress_display()
    results: List[DownloadResult] = []

    with progress:
        overall_task = progress.add_task(
            f"[bold green]Total Progress",
            filename=f"Queue: {len(videos_to_download)} videos",
            total=len(videos_to_download),
        )

        def make_progress_cb(task_id):
            def cb(current_bytes, total_bytes):
                progress.update(task_id, completed=current_bytes, total=total_bytes)
            return cb

        async def download_single(v: VideoInfo):
            task_id = progress.add_task(
                f"[bold blue]Downloading",
                filename=v.filename[:35],
                total=v.file_size or 100,
            )
            cb = make_progress_cb(task_id)
            res = await engine.download_video(v, progress_callback=cb)
            progress.update(task_id, completed=res.bytes_downloaded, visible=False)
            progress.advance(overall_task, 1)
            return res

        # Run concurrent downloads through engine semaphore
        tasks = [asyncio.create_task(download_single(v)) for v in videos_to_download]
        results = await asyncio.gather(*tasks)

    # Display results summary table
    console.print("")
    ui.display_results_summary(results, engine.out_dir)


async def handle_browse_channels(manager: TelegramManager, engine: DownloaderEngine):
    """Browse user's joined channels and download recent videos."""
    with console.status("[bold cyan]Loading your joined channels and supergroups...", spinner="dots"):
        channels = await manager.get_user_channels(limit=40)

    if not channels:
        console.print("[yellow]No channels or supergroups found for this account.[/yellow]")
        return

    ui.display_channels_table(channels)
    choice = IntPrompt.ask(
        f"[bold cyan]Select channel number (1-{len(channels)})[/bold cyan]",
        default=1,
    )
    if choice < 1 or choice > len(channels):
        console.print("[red]Invalid selection.[/red]")
        return

    selected = channels[choice - 1]
    console.print(f"[green]Selected:[/green] [bold]{selected['title']}[/bold]")

    scan_mode = Prompt.ask(
        "[bold cyan]Scan mode[/bold cyan]",
        choices=["recent", "range"],
        default="recent",
    )

    videos_found: List[VideoInfo] = []
    ent = selected["entity"]
    title = selected["title"]

    if scan_mode == "recent":
        limit = IntPrompt.ask("How many recent messages to scan?", default=50)
        with console.status(f"[bold cyan]Scanning last {limit} messages in {title}...", spinner="dots"):
            async for msg in manager.client.iter_messages(ent, limit=limit):
                vinfo = manager.extract_video_info(msg, title)
                if vinfo:
                    videos_found.append(vinfo)
    else:
        start_id = IntPrompt.ask("Start message ID")
        end_id = IntPrompt.ask("End message ID")
        if end_id < start_id:
            start_id, end_id = end_id, start_id
        ids = list(range(start_id, end_id + 1))
        with console.status(f"[bold cyan]Scanning message range {start_id}..{end_id} in {title}...", spinner="dots"):
            chunk_size = 100
            for i in range(0, len(ids), chunk_size):
                msgs = await manager.get_messages(ent, ids[i:i + chunk_size])
                for msg in msgs:
                    vinfo = manager.extract_video_info(msg, title)
                    if vinfo:
                        videos_found.append(vinfo)

    if not videos_found:
        console.print(f"[yellow]No video messages found in the scanned range of {title}.[/yellow]")
        return

    ui.display_video_targets(videos_found)
    if Confirm.ask(f"[bold green]Proceed to download {len(videos_found)} video(s)?[/bold green]", default=True):
        progress = ui.create_progress_display()
        with progress:
            overall_task = progress.add_task(
                f"[bold green]Total Progress",
                filename=f"Queue: {len(videos_found)} videos",
                total=len(videos_found),
            )

            def make_cb(tid):
                return lambda curr, tot: progress.update(tid, completed=curr, total=tot)

            async def worker(v):
                tid = progress.add_task(f"[bold blue]Downloading", filename=v.filename[:35], total=v.file_size or 100)
                res = await engine.download_video(v, progress_callback=make_cb(tid))
                progress.update(tid, completed=res.bytes_downloaded, visible=False)
                progress.advance(overall_task, 1)
                return res

            tasks = [asyncio.create_task(worker(v)) for v in videos_found]
            results = await asyncio.gather(*tasks)

        ui.display_results_summary(results, engine.out_dir)


async def interactive_loop():
    """Main interactive terminal loop for PowerShell & CMD."""
    ui.display_banner()

    valid, msg = config.validate_config()
    if not valid:
        console.print(
            Panel(
                f"[bold red]{msg}[/bold red]\n\n"
                "Please configure your credentials in the [bold cyan].env[/bold cyan] file:\n"
                "  TG_API_ID=123456\n"
                "  TG_API_HASH=your_api_hash\n"
                "  TG_PHONE=+8801XXXXXXXXX",
                title="Configuration Error",
                border_style="red",
            )
        )
        return

    manager = TelegramManager()
    try:
        console.print("[dim cyan]Connecting to Telegram MTProto session...[/dim cyan]")
        await manager.initialize()
        me = await manager.get_me()
    except Exception as e:
        console.print(f"[bold red]Failed to authenticate with Telegram:[/bold red] {e}")
        return

    out_dir = config.DEFAULT_DOWNLOAD_DIR
    concurrency = config.DEFAULT_CONCURRENCY
    engine = DownloaderEngine(out_dir=out_dir, concurrency=concurrency)

    while True:
        ui.display_banner()
        ui.display_account_info(me, engine.out_dir, engine.concurrency)
        choice = ui.display_menu()

        if choice == "1":
            # Single Post Link
            console.print("\n[bold cyan]Download Single Video Post Link[/bold cyan]")
            url = Prompt.ask("Enter Telegram post link (e.g. https://t.me/c/3100538760/15)").strip()
            target = parse_telegram_link(url)
            if not target:
                console.print("[red]Invalid Telegram link format. Expected https://t.me/c/... or https://t.me/...[/red]")
            else:
                await process_and_download(manager, [target], engine)
            Prompt.ask("\n[dim]Press Enter to return to main menu...[/dim]")

        elif choice == "2":
            # Range of Posts
            console.print("\n[bold cyan]Download Video Range[/bold cyan]")
            console.print("[dim]Format: https://t.me/c/3100538760/15-30 or provide base URL and start/end numbers.[/dim]")
            url_input = Prompt.ask("Enter range URL or single link").strip()
            target = parse_telegram_link(url_input)

            if not target:
                console.print("[red]Could not parse link. Please check format.[/red]")
            else:
                if len(target.message_ids) == 1:
                    start_id = target.message_ids[0]
                    end_id = IntPrompt.ask("End message ID in range", default=start_id + 5)
                    if end_id < start_id:
                        start_id, end_id = end_id, start_id
                    target.message_ids = list(range(start_id, end_id + 1))

                await process_and_download(manager, [target], engine)
            Prompt.ask("\n[dim]Press Enter to return to main menu...[/dim]")

        elif choice == "3":
            # Multiple Links / File
            console.print("\n[bold cyan]Download Multiple Links[/bold cyan]")
            console.print("[dim]Paste your links below (separated by spaces or newlines), OR enter path to a .txt file:[/dim]")
            user_input = Prompt.ask("Links or .txt file").strip()
            targets = []

            p = Path(user_input)
            if p.is_file():
                console.print(f"[cyan]Reading links from file: {p.resolve()}[/cyan]")
                targets = extract_targets_from_text(p.read_text(encoding="utf-8"))
            else:
                targets = extract_targets_from_text(user_input)

            if not targets:
                console.print("[yellow]No valid Telegram post links found in input.[/yellow]")
            else:
                console.print(f"[green]Parsed {len(targets)} link target(s).[/green]")
                await process_and_download(manager, targets, engine)
            Prompt.ask("\n[dim]Press Enter to return to main menu...[/dim]")

        elif choice == "4":
            # Browse Channels
            console.print("\n[bold cyan]Browse Joined Channels[/bold cyan]")
            await handle_browse_channels(manager, engine)
            Prompt.ask("\n[dim]Press Enter to return to main menu...[/dim]")

        elif choice == "5":
            # Settings
            console.print("\n[bold cyan]Settings & Configuration[/bold cyan]")
            new_dir = Prompt.ask("Downloads directory", default=str(engine.out_dir))
            engine.out_dir = config.parse_download_dir(new_dir)
            new_conc = IntPrompt.ask("Concurrent workers (2-5 recommended)", default=engine.concurrency)
            engine.concurrency = max(1, min(new_conc, 10))
            engine.semaphore = asyncio.Semaphore(engine.concurrency)
            console.print("[green]Settings updated successfully![/green]")
            Prompt.ask("\n[dim]Press Enter to return to main menu...[/dim]")

        elif choice == "6":
            # Exit
            console.print("\n[cyan]Disconnecting session and shutting down... Goodbye![/cyan]")
            await manager.disconnect()
            break


async def cli_mode(args):
    """Headless CLI mode for direct automation."""
    valid, msg = config.validate_config()
    if not valid:
        console.print(f"[bold red]{msg}[/bold red]")
        sys.exit(1)

    manager = TelegramManager()
    await manager.initialize()

    out_dir = config.parse_download_dir(args.out) if args.out else config.DEFAULT_DOWNLOAD_DIR
    concurrency = args.concurrency or config.DEFAULT_CONCURRENCY
    engine = DownloaderEngine(out_dir=out_dir, concurrency=concurrency)

    targets = []
    if args.url:
        t = parse_telegram_link(args.url)
        if t:
            targets.append(t)
    elif args.file:
        p = Path(args.file)
        if p.exists():
            targets = extract_targets_from_text(p.read_text(encoding="utf-8"))

    if not targets:
        console.print("[red]No valid targets provided via --url or --file[/red]")
        await manager.disconnect()
        sys.exit(1)

    try:
        await process_and_download(manager, targets, engine)
    finally:
        await manager.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Telegram Private & Batch Video Downloader Pro")
    parser.add_argument("--url", help="Telegram post link (e.g. https://t.me/c/3100538760/15 or /15-30)")
    parser.add_argument("--file", help="Path to text file containing links")
    parser.add_argument("--out", default=None, help="Destination folder for downloads (default: from .env or 'downloads')")
    parser.add_argument("--concurrency", type=int, default=10, help="Max simultaneous downloads (default: 10)")
    parser.add_argument("--cli", action="store_true", help="Launch interactive Terminal UI (TUI) instead of Desktop GUI")
    parser.add_argument("--gui", action="store_true", help="Launch Modern Desktop GUI (default)")
    args = parser.parse_args()

    # Headless CLI mode if specific download targets are provided
    if args.url or args.file:
        asyncio.run(cli_mode(args))
    elif args.cli:
        try:
            asyncio.run(interactive_loop())
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Program interrupted. Exiting...[/yellow]")
    else:
        # Default: Launch Modern Desktop GUI
        try:
            from gui import main as gui_main
            gui_main()
        except Exception as e:
            console.print(f"[yellow]Could not launch Desktop GUI: {e}. Falling back to Terminal UI...[/yellow]")
            try:
                asyncio.run(interactive_loop())
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Program interrupted. Exiting...[/yellow]")


if __name__ == "__main__":
    main()


