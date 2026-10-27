"""Tables for towers, doors, residents, and parcels."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Tower(Base):
    __tablename__ = "towers"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True)
    name: Mapped[str] = mapped_column(String(80))

class Door(Base):
    __tablename__ = "doors"
    id: Mapped[int] = mapped_column(primary_key=True)
    tower_id: Mapped[int] = mapped_column(ForeignKey("towers.id"))
    no: Mapped[str] = mapped_column(String(8))
    size_class: Mapped[str] = mapped_column(String(1))  # S | M | L
    current_parcel_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

class Resident(Base):
    __tablename__ = "residents"
    id: Mapped[int] = mapped_column(primary_key=True)
    tower_id: Mapped[int] = mapped_column(ForeignKey("towers.id"))
    flat: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(80))

class Parcel(Base):
    __tablename__ = "parcels"
    id: Mapped[int] = mapped_column(primary_key=True)
    tower_id: Mapped[int] = mapped_column(ForeignKey("towers.id"))
    flat: Mapped[str] = mapped_column(String(8))
    size_class: Mapped[str] = mapped_column(String(1))
    door_id: Mapped[int] = mapped_column(ForeignKey("doors.id"))
    state: Mapped[str] = mapped_column(String(12))  # holding | collected
    dropped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    code_hash: Mapped[str] = mapped_column(String(64))
    code_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    code_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dwell_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
