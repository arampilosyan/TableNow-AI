from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, Float, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class Restaurant(Base):
    __tablename__ = "restaurants"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    cuisine: Mapped[str] = mapped_column(String(80), default="Mixed")
    address: Mapped[str] = mapped_column(String(240))
    district: Mapped[str] = mapped_column(String(100), default="Yerevan")
    latitude: Mapped[float] = mapped_column(Float, default=40.1792)
    longitude: Mapped[float] = mapped_column(Float, default=44.4991)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tables: Mapped[list["DiningTable"]] = relationship(back_populates="restaurant", cascade="all, delete-orphan")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="restaurant")

class DiningTable(Base):
    __tablename__ = "dining_tables"
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    capacity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="available")  # available, unavailable
    restaurant: Mapped["Restaurant"] = relationship(back_populates="tables")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="table")

class Reservation(Base):
    __tablename__ = "reservations"
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("dining_tables.id"), index=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_phone: Mapped[str] = mapped_column(String(40))
    party_size: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=120)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    restaurant: Mapped["Restaurant"] = relationship(back_populates="reservations")
    table: Mapped["DiningTable"] = relationship(back_populates="reservations")

Index("ix_res_table_start_status", Reservation.table_id, Reservation.starts_at, Reservation.status)
