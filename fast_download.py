"""
High-Speed Pipelined Parallel Downloader for Telethon (FastTelethon Pro)
Supports chunk-level resume, continuous worker queuing with 512KB chunks,
and multi-connection parallel MTProto streaming.
"""

import asyncio
import os
import math
import time
import json
import logging
from pathlib import Path
from typing import Optional, List, Union, BinaryIO

from telethon import utils, TelegramClient
from telethon.crypto import AuthKey
from telethon.network import MTProtoSender
from telethon.tl.alltlobjects import LAYER
from telethon.tl.functions import InvokeWithLayerRequest
from telethon.tl.functions.auth import ExportAuthorizationRequest, ImportAuthorizationRequest
from telethon.tl.functions.upload import GetFileRequest
from telethon.errors import FloodWaitError
from telethon.tl.types import (
    Document,
    InputDocumentFileLocation,
    InputPhotoFileLocation,
    InputPeerPhotoFileLocation,
    InputFileLocation,
)

logger = logging.getLogger("tg-downloader.fast")

TypeLocation = Union[
    Document,
    InputDocumentFileLocation,
    InputPeerPhotoFileLocation,
    InputFileLocation,
    InputPhotoFileLocation,
]


class ParallelTransferrer:
    def __init__(self, client: TelegramClient, dc_id: Optional[int] = None) -> None:
        self.client = client
        self.loop = self.client.loop
        self.dc_id = dc_id or self.client.session.dc_id
        self.auth_key = (
            None
            if dc_id and self.client.session.dc_id != dc_id
            else self.client.session.auth_key
        )
        self.senders: List[MTProtoSender] = []

    async def _cleanup(self) -> None:
        if self.senders:
            await asyncio.gather(
                *[s.disconnect() for s in self.senders],
                return_exceptions=True,
            )
            self.senders = []

    @staticmethod
    def _get_connection_count(file_size: int) -> int:
        """
        Dynamically scales workers (up to 16-20 parallel MTProto connections)
        to saturate 10-15+ MB/s connections without triggering flood restrictions.
        """
        configured = int(os.getenv("FAST_WORKERS", "16"))
        max_workers = max(4, min(configured, 20))

        if file_size < 5 * 1024 * 1024:
            return min(4, max_workers)
        elif file_size < 20 * 1024 * 1024:
            return min(8, max_workers)
        elif file_size < 100 * 1024 * 1024:
            return min(12, max_workers)
        return max_workers

    async def _create_sender(self) -> MTProtoSender:
        dc = await self.client._get_dc(self.dc_id)
        sender = MTProtoSender(self.auth_key, loggers=self.client._log)
        await sender.connect(
            self.client._connection(
                dc.ip_address,
                dc.port,
                dc.id,
                loggers=self.client._log,
                proxy=self.client._proxy,
            )
        )
        # Expand socket receive buffer and disable Nagle's algorithm
        sock_writer = getattr(sender._connection, "_writer", None)
        if sock_writer:
            raw_sock = sock_writer.get_extra_info("socket")
            if raw_sock:
                try:
                    import socket
                    raw_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2 * 1024 * 1024)
                    raw_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                except Exception:
                    pass

        if not self.auth_key:
            auth = await self.client(ExportAuthorizationRequest(self.dc_id))
            self.client._init_request.query = ImportAuthorizationRequest(
                id=auth.id, bytes=auth.bytes
            )
            req = InvokeWithLayerRequest(LAYER, self.client._init_request)
            await sender.send(req)
            self.auth_key = sender.auth_key
        return sender

    async def download(
        self,
        file: TypeLocation,
        file_size: int,
        out_file: BinaryIO,
        progress_callback=None,
        part_size_kb: int = 512,
        state_file: Optional[Path] = None,
    ) -> None:
        part_size = part_size_kb * 1024
        part_count = math.ceil(file_size / part_size)
        connections = min(self._get_connection_count(file_size), part_count)

        # Pre-allocate output file space
        out_file.truncate(file_size)

        # Load existing resume state if available
        completed_parts: set[int] = set()
        if state_file and state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as sf:
                    state = json.load(sf)
                    if state.get("file_size") == file_size:
                        completed_parts = set(state.get("completed_parts", []))
                        logger.info(
                            f"Resuming download: {len(completed_parts)}/{part_count} chunks already downloaded."
                        )
            except Exception as e:
                logger.warning(f"Error reading resume state: {e}")
                completed_parts = set()

        # Calculate initial bytes from completed parts
        downloaded_bytes = 0
        for p_idx in completed_parts:
            if p_idx == part_count - 1:
                downloaded_bytes += (file_size - p_idx * part_size)
            else:
                downloaded_bytes += part_size

        # Immediately report initial progress for resumed downloads
        if progress_callback and downloaded_bytes > 0:
            res = progress_callback(downloaded_bytes, file_size)
            if asyncio.iscoroutine(res):
                await res

        # If already completely downloaded, finish cleanly
        if len(completed_parts) >= part_count:
            if state_file and state_file.exists():
                try:
                    state_file.unlink()
                except Exception:
                    pass
            return

        # Queue only remaining parts that need downloading
        part_queue: asyncio.Queue[int] = asyncio.Queue()
        for idx in range(part_count):
            if idx not in completed_parts:
                part_queue.put_nowait(idx)

        # Initialize sender connections
        first_sender = await self._create_sender()
        if connections > 1:
            rest_senders = await asyncio.gather(
                *[self._create_sender() for _ in range(connections - 1)]
            )
            self.senders = [first_sender, *rest_senders]
        else:
            self.senders = [first_sender]

        file_lock = asyncio.Lock()
        last_save_time = time.time()
        chunks_saved_count = 0

        def save_state():
            if not state_file:
                return
            try:
                tmp_state = state_file.with_suffix(".part.tmp")
                with open(tmp_state, "w", encoding="utf-8") as sf:
                    json.dump(
                        {
                            "file_size": file_size,
                            "part_size": part_size,
                            "part_count": part_count,
                            "completed_parts": list(completed_parts),
                        },
                        sf,
                    )
                if tmp_state.exists():
                    if state_file.exists():
                        state_file.unlink()
                    tmp_state.rename(state_file)
            except Exception as ex:
                logger.debug(f"State save error: {ex}")

        async def worker(sender: MTProtoSender):
            nonlocal downloaded_bytes, last_save_time, chunks_saved_count
            while not part_queue.empty():
                try:
                    part_idx = part_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                offset = part_idx * part_size
                req = GetFileRequest(file, offset=offset, limit=part_size)

                for attempt in range(3):
                    try:
                        result = await self.client._call(sender, req)
                        chunk = getattr(result, "bytes", b"")
                        if chunk:
                            async with file_lock:
                                out_file.seek(offset)
                                out_file.write(chunk)
                                completed_parts.add(part_idx)
                                downloaded_bytes += len(chunk)
                                current_total = downloaded_bytes
                                chunks_saved_count += 1
                                now = time.time()
                                if chunks_saved_count >= 20 or (now - last_save_time) >= 3.0:
                                    save_state()
                                    last_save_time = now
                                    chunks_saved_count = 0

                            # Update progress outside write lock
                            if progress_callback:
                                res = progress_callback(current_total, file_size)
                                if asyncio.iscoroutine(res):
                                    await res
                        break
                    except FloodWaitError as e:
                        logger.warning(f"FloodWait in worker: waiting {e.seconds}s...")
                        await asyncio.sleep(e.seconds + 1)
                    except Exception as err:
                        if attempt == 2:
                            part_queue.put_nowait(part_idx)
                            raise err
                        await asyncio.sleep(0.5)

        try:
            workers = [asyncio.create_task(worker(s)) for s in self.senders]
            await asyncio.gather(*workers)
        finally:
            save_state()
            if len(completed_parts) >= part_count:
                if state_file and state_file.exists():
                    try:
                        state_file.unlink()
                    except Exception:
                        pass
            await self._cleanup()


async def fast_download_file(
    client: TelegramClient,
    location: TypeLocation,
    out_file: BinaryIO,
    file_size: int,
    progress_callback=None,
    state_file: Optional[Path] = None,
) -> None:
    """Streams file chunks in parallel to the output file with chunk resume support."""
    dc_id, input_location = utils.get_input_location(location)
    downloader = ParallelTransferrer(client, dc_id)
    await downloader.download(
        input_location,
        file_size,
        out_file,
        progress_callback=progress_callback,
        state_file=state_file,
    )
