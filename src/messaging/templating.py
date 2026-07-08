"""Render the personalized message and build the WhatsApp Web send URL.

The template lives in an editable text file (``message.txt``) and contains
placeholders such as ``{NAME}``. Placeholders are replaced by simple string
substitution (not ``str.format``) so that literal braces or non-ASCII text in
any language (Hindi, Tamil, Bengali, etc.) never break rendering.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

from .. import config

# Matches placeholders like {NAME} or {DUE DATE}. Only word characters and
# spaces are allowed inside so that stray braces in the message are ignored.
_PLACEHOLDER = re.compile(r"\{([\w ]+)\}")

_WEB_SEND_URL = "https://web.whatsapp.com/send"


def load_template(template_file: Path = config.TEMPLATE_FILE) -> str:
    """Read the raw template text from disk."""
    path = Path(template_file)
    if not path.exists():
        raise FileNotFoundError(f"Message template not found: {template_file}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"Message template is empty: {template_file}")
    return text


def render_message(template: str, fields: dict[str, str]) -> str:
    """Replace every ``{PLACEHOLDER}`` using ``fields`` (matched case-insensitively).

    Unknown placeholders are left untouched so the sender can spot them.
    """
    # Case-insensitive lookup map.
    lookup = {key.upper(): value for key, value in fields.items()}

    def _substitute(match: re.Match[str]) -> str:
        key = match.group(1).strip().upper()
        return lookup.get(key, match.group(0))

    return _PLACEHOLDER.sub(_substitute, template).strip()


def find_unresolved_placeholders(message: str) -> list[str]:
    """Return any placeholders that were not substituted."""
    return [m.group(1).strip() for m in _PLACEHOLDER.finditer(message)]


def build_web_send_url(phone: str, message: str) -> str:
    """Build the WhatsApp Web deep link that pre-fills chat + message.

    ``phone`` must already include the country code (e.g. ``919876543210``).
    """
    return f"{_WEB_SEND_URL}?phone={quote(phone)}&text={quote(message)}"


def build_wa_me_url(phone: str, message: str) -> str:
    """Build a public ``wa.me`` click-to-chat link (handy for dry-run output)."""
    return f"https://wa.me/{quote(phone)}?text={quote(message)}"
