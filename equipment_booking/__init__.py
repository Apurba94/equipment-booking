"""Shared lab equipment booking with conflict detection and ICS export."""
from .core import BookingBook, parse_dt, to_ics

__version__ = "0.1.0"
__all__ = ["BookingBook", "parse_dt", "to_ics"]
