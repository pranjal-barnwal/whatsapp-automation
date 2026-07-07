"""Data models for the recipient list."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Client:
    """A single recipient loaded from the sheet."""

    name: str
    raw_phone: str
    phone: str = ""              # normalized, country-code-prefixed (e.g. 919876543210)
    row: int = 0                 # 1-based row number in the sheet, for reporting
    fields: dict[str, str] = field(default_factory=dict)  # header -> value (for templating)


@dataclass
class SkippedRow:
    """A row that could not be used, with the reason why."""

    row: int
    name: str
    raw_phone: str
    reason: str
