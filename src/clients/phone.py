"""Phone-number cleaning and validation for Indian mobile numbers (+91)."""
from __future__ import annotations

import re

from .. import config

# Digits that are valid for an Indian mobile number's first digit.
_VALID_INDIAN_MOBILE = re.compile(r"^[6-9]\d{9}$")


def normalize_phone(raw: str, country_code: str = config.COUNTRY_CODE) -> str | None:
    """Return a country-code-prefixed number, or ``None`` if it is not valid.

    Handles the common messy inputs found in spreadsheets:
      * numeric cells that openpyxl reads as ``9876543210.0``
      * spaces, dashes, dots and parentheses
      * a leading ``+`` or ``00`` international prefix
      * a leading ``0`` trunk prefix
      * a country code the user already typed into the sheet
    """
    if raw is None:
        return None

    text = str(raw).strip()
    if not text:
        return None

    # openpyxl may give us "9876543210.0" for a numeric cell.
    if text.endswith(".0"):
        text = text[:-2]

    # Keep digits only (drops +, spaces, dashes, parentheses, etc.).
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None

    # Strip a leading international prefix "00".
    if digits.startswith("00"):
        digits = digits[2:]

    # Strip the country code if the user already included it (e.g. 919876543210).
    if len(digits) == len(country_code) + 10 and digits.startswith(country_code):
        digits = digits[len(country_code):]

    # Strip a single leading trunk "0" (e.g. 09876543210).
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    if not _VALID_INDIAN_MOBILE.match(digits):
        return None

    return f"{country_code}{digits}"
