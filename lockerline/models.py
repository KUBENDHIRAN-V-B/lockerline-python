"""Tables. A door's state is derived from current_parcel_id; there is deliberately no `state` column on doors.
One tower here; every row still carries its tower_id, a foreign key to towers, as the ticket's data list names it.
Seeding stays idempotent through its existence checks, not through composite unique constraints."""
from sqlalchemy import ForeignKey,Integer,String
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
  size_class: Mapped[str] = mapped_column(String(1))            # S | M | L
  current_parcel_id: Mapped[int | None] = mapped_column(Integer,nullable=True)


class Resident(Base):
    __tablename__ = "residents"
    id: Mapped[int] = mapped_column(primary_key=True)
    tower_id: Mapped[int] = mapped_column(ForeignKey("towers.id"))
    flat: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(80))


