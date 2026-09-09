"""
Telegram Link and Target Parser
Supports:
- Private channel links: https://t.me/c/3100538760/15
- Private channel ranges: https://t.me/c/3100538760/15-25
- Private topic/forum links: https://t.me/c/3100538760/2/15
- Public channel links: https://t.me/channel_name/15
- Public channel ranges: https://t.me/channel_name/15-25
- Raw text batch / multi-line link parsing
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedTarget:
    raw_url: str
    is_private: bool
    channel_ref: str | int  # Either username (str) or full Telegram peer id (-100xxxxxxx)
    raw_channel_id: Optional[int] = None  # e.g., 3100538760
    message_ids: list[int] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if len(self.message_ids) == 1:
            return f"Channel: {self.channel_ref} | Msg: {self.message_ids[0]}"
        elif len(self.message_ids) > 1:
            return f"Channel: {self.channel_ref} | Msg Range: {self.message_ids[0]}..{self.message_ids[-1]} ({len(self.message_ids)} msgs)"
        return f"Channel: {self.channel_ref} | No msgs"


# Alias for convenience
LinkTarget = ParsedTarget


def normalize_private_channel_id(raw_id: int | str) -> int:
    """
    Ensures a private channel ID has the standard Telegram supergroup/channel -100 prefix.
    Telegram private links use positive IDs (e.g., 3100538760), but MTProto expects -1003100538760.
    """
    s = str(raw_id).strip()
    if s.startswith("-100"):
        return int(s)
    if s.startswith("-"):
        s = s[1:]
    return int(f"-100{s}")


# Regex for private links: https://t.me/c/3100538760/15 or /15-25 or with topic /2/15
PRIVATE_LINK_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?t\.me/c/(\d+)(?:/\d+)?/(\d+)(?:-(\d+))?",
    re.IGNORECASE,
)

# Regex for public links: https://t.me/username/15 or /15-25 or with topic /topic/15
PUBLIC_LINK_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?t\.me/([a-zA-Z0-9_]{4,})(?:/\d+)?/(\d+)(?:-(\d+))?",
    re.IGNORECASE,
)


def parse_telegram_link(url: str) -> Optional[ParsedTarget]:
    """Parse a single Telegram message URL or range URL."""
    clean_url = url.strip()
    # Strip query parameters (e.g. ?single)
    if "?" in clean_url:
        clean_url = clean_url.split("?")[0]

    # Check for private channel link
    m_priv = PRIVATE_LINK_PATTERN.search(clean_url)
    if m_priv:
        raw_chan_id = int(m_priv.group(1))
        start_id = int(m_priv.group(2))
        end_id = int(m_priv.group(3)) if m_priv.group(3) else start_id

        if end_id < start_id:
            start_id, end_id = end_id, start_id

        msg_ids = list(range(start_id, end_id + 1))
        full_chan_id = normalize_private_channel_id(raw_chan_id)

        return ParsedTarget(
            raw_url=url.strip(),
            is_private=True,
            channel_ref=full_chan_id,
            raw_channel_id=raw_chan_id,
            message_ids=msg_ids,
        )

    # Check for public channel link
    m_pub = PUBLIC_LINK_PATTERN.search(clean_url)
    if m_pub:
        username = m_pub.group(1)
        # Avoid common non-channel paths like "joinchat", "addstickers", "c", etc.
        if username.lower() not in {"joinchat", "addstickers", "c", "s", "proxy", "socks"}:
            start_id = int(m_pub.group(2))
            end_id = int(m_pub.group(3)) if m_pub.group(3) else start_id

            if end_id < start_id:
                start_id, end_id = end_id, start_id

            msg_ids = list(range(start_id, end_id + 1))
            return ParsedTarget(
                raw_url=url.strip(),
                is_private=False,
                channel_ref=username,
                raw_channel_id=None,
                message_ids=msg_ids,
            )

    return None


def extract_targets_from_text(text: str) -> list[ParsedTarget]:
    """
    Finds and parses all Telegram post/range URLs in a block of text
    (e.g., pasted lines, comma-separated URLs, or file content).
    """
    targets: list[ParsedTarget] = []
    # Split by lines, commas, or whitespace
    tokens = re.split(r"[\r\n,;\s]+", text)
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        parsed = parse_telegram_link(token)
        if parsed:
            targets.append(parsed)
    return targets
