"""Reading and preparing the recipient list from the Excel sheet."""
from .loader import load_clients
from .models import Client, SkippedRow
from .phone import normalize_phone

__all__ = ["Client", "SkippedRow", "load_clients", "normalize_phone"]
