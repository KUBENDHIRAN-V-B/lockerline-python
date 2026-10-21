"""Public ids are opaque strings (P017, D01); database integers never reach the wire."""
import re

_PARCEL = re.compile(r"^P(\d{3,})$")

def parcel_public(internal_id: int) -> str:
    return f"P{internal_id:03d}"

def parcel_internal(public_id: str) -> int | None:
    ...