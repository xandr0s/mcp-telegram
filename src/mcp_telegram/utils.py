"""Utility functions for the MCP Telegram module."""

import re
import typing
import uuid

from pathlib import Path

from telethon.tl import patched  # type: ignore


def parse_entity(entity: str) -> int | str:
    """
    Parse a string entity identifier as an integer ID.

    If the string represents a valid integer (potentially negative), it's
    returned as an `int`. Otherwise, the original string (assumed to be
    a username or phone number) is returned.

    Args:
        entity (`str`): The entity (ID, username, phone number, or "me").

    Returns:
        `int | str`: The parsed integer ID or the original string identifier.
    """
    return int(entity) if entity.lstrip("-").isdigit() else entity


def get_unique_filename(message: patched.Message) -> str:
    """Generate a unique filename for a message media.

    Args:
        message (`patched.Message`): The message to generate a filename for.

    Returns:
        `str`: The unique filename.
    """

    unique_prefix = str(uuid.uuid4())

    original_filename = None
    original_suffix = ""

    if message.file and isinstance(message.file.name, str):
        original_filename = Path(message.file.name).stem
        original_suffix = Path(message.file.name).suffix

    if original_filename:
        filename = f"{original_filename}_{unique_prefix}{original_suffix}"
    else:
        # Fallback if no original name (use message_id and media type if possible)
        fallback_name = f"download_{message.id}_{unique_prefix}"
        if message.file and isinstance(message.file.mime_type, str):
            # Try to get extension from mime type (basic implementation)
            parts = message.file.mime_type.split("/")
            if len(parts) == 2 and parts[1]:
                filename = f"{fallback_name}.{parts[1]}"
            else:
                filename = fallback_name
        else:
            filename = fallback_name

    return filename


def render_rich_text(node: typing.Any) -> str:
    """Flatten a Telethon ``RichText`` tree into a Markdown-ish string.

    Rich messages (Telegram's new post format, TL layer 227+) carry their text
    as a nested ``RichText`` tree instead of ``Message.message``. Unknown node
    types fall through to their children so new formatting never silently drops
    the text.
    """
    if node is None:
        return ""
    name = type(node).__name__
    if name == "TextEmpty":
        return ""
    if name == "TextPlain":
        return str(getattr(node, "text", "") or "")
    if name == "TextConcat":
        return "".join(render_rich_text(child) for child in (node.texts or []))

    inner = render_rich_text(getattr(node, "text", None))
    if not inner.strip():
        return inner
    if name == "TextBold":
        return f"**{inner}**"
    if name in ("TextItalic", "TextMarked"):
        return f"*{inner}*"
    if name == "TextStrike":
        return f"~~{inner}~~"
    if name == "TextFixed":
        return f"`{inner}`"
    if name in ("TextUrl", "TextAutoUrl"):
        url = getattr(node, "url", None)
        return f"[{inner}]({url})" if url else inner
    if name == "TextEmail":
        return f"[{inner}](mailto:{getattr(node, 'email', '')})"
    return inner


def render_rich_message(rich: typing.Any) -> tuple[str, int]:
    """Flatten a ``RichMessage`` into (text, photo_count).

    Blocks are Instant-View style ``PageBlock*`` objects: paragraphs carry
    ``text``, collages and slideshows carry ``items`` plus an optional
    ``caption``. Anything unrecognised is still walked for nested text.
    """
    if rich is None:
        return "", 0

    parts: list[str] = []
    photos = 0

    def walk(block: typing.Any) -> None:
        nonlocal photos
        name = type(block).__name__
        if name == "PageBlockPhoto":
            photos += 1
        # Collages and slideshows nest under `items`; details, blockquotes and
        # covers nest under `blocks`. Walk both so nested text is never lost.
        for attr in ("items", "blocks"):
            for child in getattr(block, attr, None) or []:
                walk(child)
        text = render_rich_text(getattr(block, "text", None)).strip()
        if text:
            parts.append(text)
        caption = getattr(block, "caption", None)
        if caption is not None:
            for attr in ("text", "credit"):
                rendered = render_rich_text(getattr(caption, attr, None)).strip()
                if rendered:
                    parts.append(rendered)

    for block in getattr(rich, "blocks", None) or []:
        walk(block)

    photos = max(photos, len(getattr(rich, "photos", None) or []))
    return "\n\n".join(parts), photos


def parse_telegram_url(url: str) -> tuple[str | int, int] | None:
    """Parse a Telegram message URL to extract the entity and message ID.

    Handles common formats like:
    - `https://t.me/username/123`
    - `t.me/username/123`
    - `https://telegram.me/username/123`
    - `telegram.me/username/123`
    - `https://t.me/c/1234567890/123`

    Args:
        url (`str`): The Telegram URL to parse.

    Returns:
        `tuple[str | int, int] | None`:
            A tuple containing the entity (username or channel_id) and the
            message ID, or None if the URL format is not recognized.
    """
    # Regex to capture the entity (username or channel_id) and message ID
    pattern = r"^(?:https?://)?t(?:elegram)?\.me/(?:(?P<username>[A-Za-z0-9_]+)/(?P<message_id>\d+)|c/(?P<chat_id>\d+)/(?P<chat_message_id>\d+))/?$"

    match = re.match(pattern, url)

    if match:
        captured = match.groupdict()
        entity = captured.get("username") or captured.get("chat_id")
        message_id = captured.get("message_id") or captured.get("chat_message_id")

        if entity and message_id:
            return parse_entity(entity), int(message_id)

    return None
