"""
Rich Terminal User Interface (TUI) for CMD and PowerShell
"""

import sys
import time
from pathlib import Path
from typing import List, Optional

# Ensure UTF-8 output on Windows CMD / PowerShell
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)

from client_manager import VideoInfo
from downloader_engine import DownloadResult

console = Console()


def display_banner():
    """Displays the styled application banner."""
    console.clear()
    banner_text = Text(
        "⚡ TELEGRAM PRIVATE & BATCH VIDEO DOWNLOADER ⚡\n"
        "Download Private Posts • Protected Content • Multi-Video Ranges",
        justify="center",
        style="bold cyan",
    )
    console.print(
        Panel(
            banner_text,
            border_style="bright_blue",
            padding=(1, 2),
            subtitle="[bold green]Active MTProto Session[/bold green]",
        )
    )


def display_account_info(me: dict, out_dir: Path, concurrency: int):
    """Displays connected account and operational configuration."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold yellow")
    table.add_column("Value", style="bold white")

    name = f"{me.get('first_name', '')} {me.get('last_name', '')}".strip() or "Telegram User"
    username = f"@{me.get('username')}" if me.get('username') != "None" else "No username"
    phone = me.get("phone", "")

    table.add_row("👤 Account", f"{name} ({username})")
    table.add_row("📱 Phone", phone)
    table.add_row("📁 Save Location", f"[cyan]{out_dir.resolve()}[/cyan]")
    table.add_row("⚡ Parallel Workers", f"[magenta]{concurrency} concurrent streams[/magenta]")

    console.print(Panel(table, title="[bold green]Connected Profile[/bold green]", border_style="dim green"))


def display_menu() -> str:
    """Displays the main interactive menu options."""
    table = Table(show_header=False, border_style="bright_blue", padding=(0, 1))
    table.add_column("Key", style="bold cyan", width=6)
    table.add_column("Action", style="bold white")

    table.add_row("[1]", "📥  Download Single Post Link (e.g. https://t.me/c/3100538760/15)")
    table.add_row("[2]", "🔢  Download Post Range (e.g. https://t.me/c/3100538760/15-30)")
    table.add_row("[3]", "📋  Download Multiple Links (Paste list or load from file)")
    table.add_row("[4]", "📁  Browse Joined Channels (Select channel & scan videos)")
    table.add_row("[5]", "⚙️   Settings (Change download folder or concurrency)")
    table.add_row("[6]", "❌  Exit")

    console.print(Panel(table, title="[bold white]Main Menu[/bold white]", border_style="blue"))
    choice = Prompt.ask(
        "[bold cyan]Select an option[/bold cyan]",
        choices=["1", "2", "3", "4", "5", "6"],
        default="1",
    )
    return choice


def display_video_targets(videos: List[VideoInfo]):
    """Displays a preview table of videos discovered and queued for download."""
    table = Table(title=f"📹 Discovered Media ({len(videos)} video(s))", border_style="bright_blue")
    table.add_column("#", style="dim", width=4)
    table.add_column("Msg ID", style="cyan", width=8)
    table.add_column("Filename", style="bold white")
    table.add_column("Size", style="green", width=12)
    table.add_column("Duration", style="yellow", width=10)

    for idx, v in enumerate(videos, start=1):
        size_str = format_bytes(v.file_size)
        dur_str = format_duration(v.duration_seconds)
        table.add_row(str(idx), str(v.message_id), v.filename, size_str, dur_str)

    console.print(table)


def create_progress_display() -> Progress:
    """Creates a rich multi-task progress bar for live downloads."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.fields[filename]}", justify="left"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )


def display_results_summary(results: List[DownloadResult], out_dir: Path):
    """Prints a summary table after downloads complete."""
    table = Table(title="📊 Download Summary", border_style="bright_green")
    table.add_column("Msg ID", style="cyan", width=8)
    table.add_column("Filename", style="white")
    table.add_column("Size", style="magenta", width=12)
    table.add_column("Time", style="yellow", width=10)
    table.add_column("Status", width=12)

    total_downloaded_bytes = 0
    success_count = 0
    skipped_count = 0
    failed_count = 0

    for r in results:
        size_str = format_bytes(r.bytes_downloaded or r.info.file_size)
        time_str = f"{r.duration_seconds:.1f}s" if r.duration_seconds > 0 else "-"

        if r.status == "SUCCESS":
            status_str = "[bold green]✓ SUCCESS[/bold green]"
            success_count += 1
            total_downloaded_bytes += r.bytes_downloaded
        elif r.status == "SKIPPED":
            status_str = "[bold yellow]↷ SKIPPED[/bold yellow]"
            skipped_count += 1
        else:
            status_str = f"[bold red]✗ FAILED[/bold red]"
            failed_count += 1

        table.add_row(str(r.info.message_id), r.info.filename, size_str, time_str, status_str)

    console.print(table)
    summary_line = (
        f"[bold green]Success: {success_count}[/bold green] | "
        f"[bold yellow]Skipped: {skipped_count}[/bold yellow] | "
        f"[bold red]Failed: {failed_count}[/bold red] | "
        f"Total Transferred: [bold cyan]{format_bytes(total_downloaded_bytes)}[/bold cyan]"
    )
    console.print(Panel(summary_line, border_style="cyan"))
    console.print(f"📂 [bold]Saved in:[/bold] [link=file:///{out_dir.resolve()}]{out_dir.resolve()}[/link]\n")


def format_bytes(size: int) -> str:
    """Format bytes to human readable string (KB, MB, GB)."""
    if not size or size <= 0:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def format_duration(seconds: int | float | None) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    if not seconds or seconds <= 0:
        return "-"
    try:
        total_seconds = int(round(float(seconds)))
    except (ValueError, TypeError):
        return "-"
    m, s = divmod(total_seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def display_channels_table(channels: list[dict]):
    """Displays the list of channels/supergroups joined by the user."""
    table = Table(title="📁 Joined Channels & Groups", border_style="bright_blue")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Channel Name", style="bold white")
    table.add_column("Type", style="yellow", width=12)
    table.add_column("Username / ID", style="dim", width=22)

    for idx, c in enumerate(channels, start=1):
        c_type = "Channel" if c["is_broadcast"] else "Supergroup"
        ref = f"@{c['username']}" if c["username"] else str(c["raw_id"])
        table.add_row(str(idx), c["title"][:40], c_type, ref)

    console.print(table)
