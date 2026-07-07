"""Per-client run reporting to a timestamped CSV.

Each run appends rows to ``logs/report-YYYYmmdd-HHMMSS.csv``. The reports also
power ``--resume``: numbers already recorded as ``sent`` are skipped on re-runs.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from . import config

# Status values written to the report.
STATUS_SENT = "sent"
STATUS_INVALID = "invalid"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

_FIELDNAMES = ["timestamp", "row", "name", "phone", "status", "detail"]


class Report:
    """Streaming CSV writer for a single run."""

    def __init__(self, log_dir: Path = config.LOG_DIR) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = self.log_dir / f"report-{stamp}.csv"
        self.counts: dict[str, int] = {}

        self._file = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=_FIELDNAMES)
        self._writer.writeheader()
        self._file.flush()

    def record(
        self,
        status: str,
        *,
        name: str,
        phone: str = "",
        row: int = 0,
        detail: str = "",
    ) -> None:
        """Append a single result row and flush immediately (crash-safe)."""
        self._writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "row": row,
                "name": name,
                "phone": phone,
                "status": status,
                "detail": detail,
            }
        )
        self._file.flush()
        self.counts[status] = self.counts.get(status, 0) + 1

    def summary(self) -> str:
        """Human-readable one-line tally of the run."""
        parts = [f"{status}={count}" for status, count in sorted(self.counts.items())]
        return ", ".join(parts) if parts else "no messages processed"

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()

    def __enter__(self) -> "Report":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def load_already_sent(log_dir: Path = config.LOG_DIR) -> set[str]:
    """Return the set of phone numbers marked ``sent`` in any prior report."""
    directory = Path(log_dir)
    sent: set[str] = set()
    if not directory.exists():
        return sent

    for report_path in directory.glob("report-*.csv"):
        try:
            with report_path.open("r", newline="", encoding="utf-8") as handle:
                for record in csv.DictReader(handle):
                    if record.get("status") == STATUS_SENT and record.get("phone"):
                        sent.add(record["phone"])
        except (OSError, csv.Error):
            continue  # ignore unreadable/partial reports
    return sent
