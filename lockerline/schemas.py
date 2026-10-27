"""Validated request and response models."""
from datetime import datetime, timezone
from typing import Annotated, Literal
from pydantic import BaseModel, Field, PlainSerializer

SizeClass = Literal["S", "M", "L"]
DoorState = Literal["free", "holding"]

def _iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

UtcZ = Annotated[datetime, PlainSerializer(_iso_z, return_type=str)]

class DropRequest(BaseModel):
    size_class: SizeClass
    flat: str = Field(min_length=1, max_length=8, pattern=r"^\d+$")

class DropOut(BaseModel):
    parcel_id: str
    door: str
    size_class: SizeClass
    flat: str
    dropped_at: UtcZ
    code: str = Field(pattern=r"^\d{6}$")
    expires_at: UtcZ

class ParcelOut(BaseModel):
    parcel_id: str
    door: str
    size_class: SizeClass
    flat: str
    state: Literal["holding", "collected"]
    dropped_at: UtcZ

class DoorListItem(BaseModel):
    no: str
    size: SizeClass
    state: DoorState
    parcel_id: str | None = None
    dwell_seconds: int | None = None

class DoorOut(DoorListItem):
    flat: str | None = None

class DoorsOut(BaseModel):
    tower: str
    free: int = Field(description="Number of free doors among the returned doors")
    doors: list[DoorListItem]

class PickupRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class PickupOut(BaseModel):
    parcel_id: str
    door: str
    opened_at: UtcZ
    dwell_seconds: int
