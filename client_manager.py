"""
Telegram Client Lifecycle & Entity Resolution Manager
"""

import logging
from dataclasses import dataclass
from typing import Optional, Any, Callable
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import (
    DocumentAttributeVideo,
    DocumentAttributeFilename,
    PeerChannel,
    Channel,
    Chat,
)
from telethon.errors import (
    ChannelPrivateError,
    ChatAdminRequiredError,
    UserDeactivatedError,
    AuthKeyUnregisteredError,
)

import config

logger = logging.getLogger("tg-downloader.client")

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".ts", ".m4v"}


@dataclass
class VideoInfo:
    message_id: int
    chat_id: int
    chat_title: str
    filename: str
    file_size: int  # in bytes
    duration_seconds: int = 0
    width: int = 0
    height: int = 0
    mime_type: str = "video/mp4"
    caption: str = ""
    message_obj: Any = None


def configure_sqlite_wal(session_name: str) -> None:
    """Configures SQLite WAL mode and busy timeout to avoid database locked errors."""
    db_file = f"{session_name}.session"
    try:
        import sqlite3
        conn = sqlite3.connect(db_file, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=15000;")
        conn.close()
    except Exception:
        pass


class TelegramManager:
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self._dialogs_cached = False

    async def initialize(
        self,
        code_callback: Optional[Callable] = None,
        password_callback: Optional[Callable] = None,
    ) -> TelegramClient:
        """Create and start the TelegramClient instance with interactive or GUI login prompts."""
        valid, msg = config.validate_config()
        if not valid:
            raise ValueError(msg)

        configure_sqlite_wal(config.SESSION_NAME)

        self.client = TelegramClient(
            config.SESSION_NAME,
            config.TG_API_ID,
            config.TG_API_HASH,
        )
        await self.client.connect()


        if not await self.client.is_user_authorized():
            if not code_callback:
                from rich.panel import Panel
                from rich.console import Console
                from rich.prompt import Prompt
                term = Console()
                term.print(
                    Panel(
                        f"[bold yellow]Authentication required for account: [white]{config.TG_PHONE}[/white][/bold yellow]\n\n"
                        "Telegram has sent a verification code to your Telegram app (or via SMS).\n"
                        "Please check your active Telegram devices for the official code.",
                        title="🔐 Telegram Authentication",
                        border_style="yellow",
                        padding=(1, 2),
                    )
                )

                def get_code():
                    while True:
                        code = Prompt.ask("[bold cyan]Enter verification code[/bold cyan]").strip()
                        if code:
                            return code

                def get_password():
                    return Prompt.ask("[bold magenta]Enter your 2FA password[/bold magenta]", password=True)

                code_cb = get_code
                password_cb = get_password
            else:
                code_cb = code_callback
                password_cb = password_callback or (lambda: "")

            await self.client.start(
                phone=config.TG_PHONE,
                code_callback=code_cb,
                password=password_cb,
            )
            if not code_callback:
                term.print("[bold green]✓ Successfully authenticated with Telegram![/bold green]\n")

        return self.client

    async def get_me(self) -> dict:
        """Get profile information of the currently authenticated account."""
        if not self.client:
            raise RuntimeError("Client not initialized")
        me = await self.client.get_me()
        return {
            "id": me.id,
            "first_name": me.first_name or "",
            "last_name": me.last_name or "",
            "username": me.username or "None",
            "phone": me.phone or config.TG_PHONE,
        }

    async def resolve_entity(self, channel_ref: str | int, raw_channel_id: Optional[int] = None) -> Any:
        """
        Resolves a public channel username or private channel ID to an MTProto entity.
        Automatically loads dialogs into cache if entity lookup fails initially.
        """
        if not self.client:
            raise RuntimeError("Client not initialized")

        # 1. Try direct lookup
        try:
            entity = await self.client.get_entity(channel_ref)
            return entity
        except Exception:
            pass

        # 2. If it's a private channel, try with PeerChannel or integer forms
        if isinstance(channel_ref, int):
            abs_id = abs(channel_ref)
            if str(abs_id).startswith("100"):
                abs_id = int(str(abs_id)[3:])

            try:
                entity = await self.client.get_entity(PeerChannel(abs_id))
                return entity
            except Exception:
                pass

        # 3. If still not found, warm the cache by iterating dialogs
        try:
            logger.info("Entity not in local cache; refreshing dialogs...")
            async for dialog in self.client.iter_dialogs():
                d_ent = dialog.entity
                d_id = getattr(d_ent, "id", None)
                # Match against normalized ID or raw channel ID
                if dialog.id == channel_ref:
                    return d_ent
                if d_id and (d_id == raw_channel_id or d_id == channel_ref):
                    return d_ent
                if raw_channel_id and d_id == raw_channel_id:
                    return d_ent
            self._dialogs_cached = True
        except Exception as e:
            logger.warning(f"Error while refreshing dialogs: {e}")

        # 4. Final attempt after cache warmup
        try:
            return await self.client.get_entity(channel_ref)
        except Exception as e:
            raise ValueError(
                f"Cannot access channel/group ({channel_ref}).\n"
                f"Please verify that your account ({config.TG_PHONE}) has joined this private channel."
            ) from e

    async def get_messages(self, entity: Any, message_ids: list[int]) -> list[Any]:
        """Fetch messages by IDs from the given entity."""
        if not self.client:
            raise RuntimeError("Client not initialized")
        if not message_ids:
            return []

        # get_messages accepts a single ID or list of IDs
        msgs = await self.client.get_messages(entity, ids=message_ids)
        if not isinstance(msgs, list):
            msgs = [msgs]
        # Filter out None (deleted or inaccessible messages)
        return [m for m in msgs if m is not None]

    async def fetch_videos_from_target(self, target: Any) -> list[VideoInfo]:
        """
        Resolves target entity, fetches messages by IDs, and extracts all downloadable VideoInfo.
        """
        if not self.client:
            raise RuntimeError("Client not initialized")

        channel_ref = getattr(target, "channel_ref", target)
        raw_id = getattr(target, "raw_channel_id", None)
        message_ids = getattr(target, "message_ids", [])
        if isinstance(message_ids, int):
            message_ids = [message_ids]

        entity = await self.resolve_entity(channel_ref, raw_id)
        chat_title = getattr(entity, "title", str(channel_ref))

        videos: list[VideoInfo] = []
        chunk_size = 100
        for i in range(0, len(message_ids), chunk_size):
            chunk = message_ids[i:i + chunk_size]
            messages = await self.get_messages(entity, chunk)
            for msg in messages:
                vinfo = self.extract_video_info(msg, chat_title)
                if vinfo:
                    videos.append(vinfo)

        return videos

    async def get_user_channels(self, limit: int = 50) -> list[dict]:
        """List channels and supergroups the user is currently a member of."""
        if not self.client:
            raise RuntimeError("Client not initialized")

        channels = []
        count = 0
        async for dialog in self.client.iter_dialogs():
            ent = dialog.entity
            if isinstance(ent, (Channel, Chat)):
                is_broadcast = getattr(ent, "broadcast", False)
                is_megagroup = getattr(ent, "megagroup", False)
                if is_broadcast or is_megagroup:
                    channels.append({
                        "id": dialog.id,
                        "raw_id": ent.id,
                        "title": dialog.name or "Untitled Channel",
                        "username": getattr(ent, "username", None),
                        "is_broadcast": is_broadcast,
                        "is_megagroup": is_megagroup,
                        "entity": ent,
                    })
                    count += 1
                    if count >= limit:
                        break
        return channels

    @staticmethod
    def extract_video_info(message: Any, chat_title: str = "") -> Optional[VideoInfo]:
        """
        Examines a message and returns VideoInfo if it contains a video, else None.
        Handles both native Telegram video messages and document-wrapped videos.
        """
        if not message or not message.media:
            return None

        # Check native video
        if message.video:
            doc = message.video
            filename = None
            duration = 0
            width = 0
            height = 0
            mime = getattr(doc, "mime_type", "video/mp4")

            for attr in getattr(doc, "attributes", []):
                if isinstance(attr, DocumentAttributeVideo):
                    raw_dur = getattr(attr, "duration", 0)
                    duration = int(round(float(raw_dur or 0)))
                    width = getattr(attr, "w", 0)
                    height = getattr(attr, "h", 0)
                elif isinstance(attr, DocumentAttributeFilename):
                    filename = getattr(attr, "file_name", None)

            if not filename:
                ext = ".mp4"
                if "webm" in mime:
                    ext = ".webm"
                elif "mkv" in mime:
                    ext = ".mkv"
                filename = f"video_{message.chat_id}_{message.id}{ext}"

            return VideoInfo(
                message_id=message.id,
                chat_id=message.chat_id,
                chat_title=chat_title or str(message.chat_id),
                filename=filename,
                file_size=getattr(doc, "size", 0),
                duration_seconds=duration,
                width=width,
                height=height,
                mime_type=mime,
                caption=message.message or "",
                message_obj=message,
            )

        # Check document sent as video file
        if message.document:
            doc = message.document
            mime = getattr(doc, "mime_type", "")
            is_video = mime.startswith("video/")

            filename = None
            duration = 0
            width = 0
            height = 0

            for attr in getattr(doc, "attributes", []):
                if isinstance(attr, DocumentAttributeVideo):
                    is_video = True
                    raw_dur = getattr(attr, "duration", 0)
                    duration = int(round(float(raw_dur or 0)))
                    width = getattr(attr, "w", 0)
                    height = getattr(attr, "h", 0)
                elif isinstance(attr, DocumentAttributeFilename):
                    filename = getattr(attr, "file_name", None)

            if filename:
                ext = Path(filename).suffix.lower()
                if ext in VIDEO_EXTENSIONS:
                    is_video = True

            if is_video:
                if not filename:
                    filename = f"doc_video_{message.chat_id}_{message.id}.mp4"

                return VideoInfo(
                    message_id=message.id,
                    chat_id=message.chat_id,
                    chat_title=chat_title or str(message.chat_id),
                    filename=filename,
                    file_size=getattr(doc, "size", 0),
                    duration_seconds=duration,
                    width=width,
                    height=height,
                    mime_type=mime or "video/mp4",
                    caption=message.message or "",
                    message_obj=message,
                )

        return None

    async def disconnect(self):
        """Safely disconnect client."""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
