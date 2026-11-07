from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import DiningTable, Reservation, Restaurant

ACTIVE_STATUSES = ("pending", "confirmed")

def overlaps(start_a, duration_a, start_b, duration_b):
    end_a = start_a + timedelta(minutes=duration_a)
    end_b = start_b + timedelta(minutes=duration_b)
    return start_a < end_b and start_b < end_a

def available_tables(db: Session, restaurant_id: int, starts_at: datetime, party_size: int, duration: int = 120):
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant or not restaurant.is_active:
        return []
    tables = db.scalars(select(DiningTable).where(
        DiningTable.restaurant_id == restaurant_id,
        DiningTable.capacity >= party_size,
        DiningTable.status == "available"
    ).order_by(DiningTable.capacity, DiningTable.id)).all()
    result = []
    for table in tables:
        bookings = db.scalars(select(Reservation).where(
            Reservation.table_id == table.id,
            Reservation.status.in_(ACTIVE_STATUSES)
        )).all()
        if not any(overlaps(starts_at, duration, b.starts_at, b.duration_minutes) for b in bookings):
            result.append(table)
    return result

def create_reservation(db: Session, payload):
    # Serialize writes for SQLite and perform conflict check inside the transaction.
    table = db.get(DiningTable, payload.table_id)
    if not table or table.restaurant_id != payload.restaurant_id:
        raise ValueError("Selected table does not belong to this restaurant.")
    if table.capacity < payload.party_size:
        raise ValueError("Selected table capacity is too small.")
    starts_at = datetime.combine(payload.date, payload.time)
    db.rollback() if db.in_transaction() else None
    try:
        if not available_tables(db, payload.restaurant_id, starts_at, payload.party_size, payload.duration_minutes) or table.id not in {
            t.id for t in available_tables(db, payload.restaurant_id, starts_at, payload.party_size, payload.duration_minutes)
        }:
            raise ValueError("This table is no longer available for the selected time.")
        reservation = Reservation(
            restaurant_id=payload.restaurant_id, table_id=payload.table_id,
            customer_name=payload.customer_name, customer_phone=payload.customer_phone,
            party_size=payload.party_size, starts_at=starts_at,
            duration_minutes=payload.duration_minutes, status="pending"
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)
        return reservation
    except Exception:
        db.rollback()
        raise
