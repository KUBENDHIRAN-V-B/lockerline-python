"""Door choice, parcel, code and events are one transaction."""

from datetime import timedelta, timezone
import hashlib
import hmac
import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..clock import Clock, as_utc
from ..errors import NoDoorFree, NoSuchFlat, NoSuchTower
from ..models import Door, Parcel, Resident, Tower
from ..schemas import DropOut, DropRequest
from . import events

SIZE_ORDER = ("S", "M", "L")


def parcel_public_id(parcel_id: int) -> str:
    """Convert an internal parcel ID to its public ID."""
    return f"P{parcel_id:03d}"


def parse_parcel_id(value: str) -> int | None:
    """Convert a public parcel ID such as P017 to integer 17."""
    match = re.fullmatch(r"P(\d+)", value)
    return int(match.group(1)) if match else None


def hash_pickup_code(code: str, secret: str) -> str:
    """Return a keyed SHA-256 digest; never persist the plaintext code."""
    return hmac.new(
        secret.encode("utf-8"),
        code.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def verify_pickup_code(
    code: str,
    stored_hash: str,
    secret: str,
) -> bool:
    """Compare a supplied code with its stored hash in constant time."""
    return hmac.compare_digest(
        hash_pickup_code(code, secret),
        stored_hash,
    )


def _tower(session: Session, code: str) -> Tower:
    """Find a tower by its code."""
    tower = session.scalar(
        select(Tower).where(Tower.code == code)
    )
    if tower is None:
        raise NoSuchTower(f"There is no tower {code!r}")
    return tower


def _free_sizes(session: Session, tower_id: int) -> list[str]:
    """Return available door sizes in S, M, L order."""
    rows = session.scalars(
        select(Door.size_class)
        .where(
            Door.tower_id == tower_id,
            Door.current_parcel_id.is_(None),
        )
        .distinct()
    )
    found = set(rows)
    return [size for size in SIZE_ORDER if size in found]


def _new_unique_code(
    session: Session,
    secret: str,
) -> tuple[str, str]:
    """Generate a six-digit code and its unique stored hash."""
    # A code may be reused once its previous parcel has been collected.
    existing_hashes = set(
        session.scalars(
            select(Parcel.code_hash).where(Parcel.code_used_at.is_(None))
        )
    )

    for _ in range(100):
        code = f"{secrets.randbelow(1_000_000):06d}"
        digest = hash_pickup_code(code, secret)

        if digest not in existing_hashes:
            return code, digest

    raise RuntimeError("Could not generate a unique pickup code")


def create_drop(
    session: Session,
    request: DropRequest,
    clock: Clock,
    free_window_hours: int = 48,
    code_secret: str = "development-only-change-this-secret",
    tower_code: str = "A",
) -> DropOut:
    """Validate and save the parcel and door assignment in one transaction."""
    try:
        tower = _tower(session, tower_code)

        resident = session.scalar(
            select(Resident).where(
                Resident.tower_id == tower.id,
                Resident.flat == request.flat,
            )
        )
        if resident is None:
            raise NoSuchFlat(
                f"Flat {request.flat!r} does not exist in tower {tower_code}"
            )

        door = session.scalar(
            select(Door)
            .where(
                Door.tower_id == tower.id,
                Door.size_class == request.size_class,
                Door.current_parcel_id.is_(None),
            )
            .order_by(Door.no.asc())
            .limit(1)
        )

        if door is None:
            raise NoDoorFree(
                f"No free door of size {request.size_class}",
                free_sizes=_free_sizes(session, tower.id),
            )

        # Read the injected clock once; calculate expiry from drop time.
        dropped_at = as_utc(clock.now()).astimezone(timezone.utc)
        expires_at = dropped_at + timedelta(hours=free_window_hours)

        # Persist only the hash, never the plaintext pickup code.
        code, code_hash = _new_unique_code(session, code_secret)

        parcel = Parcel(
            tower_id=tower.id,
            flat=request.flat,
            size_class=request.size_class,
            door_id=door.id,
            state="holding",
            dropped_at=dropped_at,
            code_hash=code_hash,
            code_expires_at=expires_at,
            code_used_at=None,
        )

        session.add(parcel)
        session.flush()

        door.current_parcel_id = parcel.id
        events.record(session, tower.id, parcel.id, "dropped", dropped_at, {"door": door.no})
        events.record(session, tower.id, parcel.id, "code_issued", dropped_at, {"expires_at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ")})
        session.commit()

        return DropOut(
            parcel_id=parcel_public_id(parcel.id),
            door=door.no,
            size_class=parcel.size_class,
            flat=parcel.flat,
            dropped_at=dropped_at,
            code=code,
            expires_at=expires_at,
        )

    except Exception:
        session.rollback()
        raise
