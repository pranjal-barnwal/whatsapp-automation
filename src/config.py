"""Central configuration and default settings.

All values here are sensible defaults. Anything a user is likely to change
per-run can be overridden from the command line (see ``cli``).
"""
from __future__ import annotations

from pathlib import Path

# --- Paths -------------------------------------------------------------------
# Project root = the folder that contains the ``src`` package.
ROOT_DIR: Path = Path(__file__).resolve().parent.parent

DATA_FILE: Path = ROOT_DIR / "data" / "Clients.xlsx"
TEMPLATE_FILE: Path = ROOT_DIR / "message.txt"
LOG_DIR: Path = ROOT_DIR / "logs"
# Chrome/WhatsApp Web session lives here so the QR code is scanned only once.
PROFILE_DIR: Path = ROOT_DIR / ".wa_profile"

# --- Excel layout ------------------------------------------------------------
# Row 1 is a header and is skipped. Columns are 1-indexed in openpyxl.
HEADER_ROWS: int = 1

# Fixed column positions (1-indexed). Column 1 = name, column 2 = phone number.
# Any other columns in the sheet are ignored.
NAME_COLUMN: int = 1      # 1st column = client name
PHONE_COLUMN: int = 2     # 2nd column = phone number (no country code)

# Stop reading at the first empty row (blank name AND phone), treating it as the
# end of the client list. Set to False to skip blanks and read to the last row.
STOP_AT_FIRST_EMPTY_ROW: bool = True

# --- Phone numbers -----------------------------------------------------------
COUNTRY_CODE: str = "91"  # India; numbers in the sheet have no country code.

# --- Sending behaviour -------------------------------------------------------
# Randomised delay (seconds) between messages to look human and reduce the
# risk of the number being flagged for spam.
MIN_DELAY_SECONDS: float = 8.0
MAX_DELAY_SECONDS: float = 20.0

# How long (seconds) to wait for WhatsApp Web UI elements before giving up.
PAGE_LOAD_TIMEOUT: int = 60
ELEMENT_TIMEOUT: int = 40
