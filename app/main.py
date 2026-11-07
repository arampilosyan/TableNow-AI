import os
from datetime import date, datetime, time
from fastapi import FastAPI, Depends, HTTPException, Header, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db, init_db
from app.models import Restaurant, DiningTable, Reservation
from app.schemas import ReservationCreate, ReservationStatusUpdate, TableStatusUpdate
from app.services.reservations import available_tables, create_reservation
from app.services.ml import forecast_demand, recommend_restaurants

app = FastAPI(title="TableNow AI", version="1.0.0", description="Restaurant discovery and live table reservation platform")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
connections: list[WebSocket] = []
ADMIN_KEY = os.getenv("ADMIN_API_KEY", "dev-admin-key")

@app.on_event("startup")
def startup():
    init_db()

def require_admin(x_admin_key: str | None = Header(default=None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing admin key")

async def broadcast(event: dict):
    stale = []
    for ws in connections:
        try:
            await ws.send_json(event)
        except Exception:
            stale.append(ws)
    for ws in stale:
        if ws in connections:
            connections.remove(ws)

@app.get("/")
def home():
    return FileResponse("app/static/index.html")

@app.get("/admin")
def admin():
    return FileResponse("app/static/admin.html")

@app.get("/health")
def health():
    return {"status": "ok", "service": "TableNow AI"}

@app.get("/api/restaurants")
def restaurants(db: Session = Depends(get_db)):
    rows = db.scalars(select(Restaurant).where(Restaurant.is_active == True).order_by(Restaurant.name)).all()  # noqa: E712
    return [{"id": r.id, "name": r.name, "cuisine": r.cuisine, "address": r.address, "district": r.district,
             "latitude": r.latitude, "longitude": r.longitude, "description": r.description} for r in rows]

@app.get("/api/availability")
def availability(restaurant_id: int, date_value: date = Query(default=None, alias='date'), time_value: time = Query(default=None, alias='time'),
                 party_size: int = 2, duration_minutes: int = 120, db: Session = Depends(get_db)):
    # Accept the documented query names date/time via aliases.
    if date_value is None or time_value is None:
        raise HTTPException(422, detail="date and time are required")
    if party_size < 1 or duration_minutes < 30:
        raise HTTPException(422, detail="Invalid party size or duration")
    starts_at = datetime.combine(date_value, time_value)
    tables = available_tables(db, restaurant_id, starts_at, party_size, duration_minutes)
    return [{"id": t.id, "name": t.name, "capacity": t.capacity, "status": t.status} for t in tables]

@app.post("/api/reservations", status_code=201)
async def reserve(payload: ReservationCreate, db: Session = Depends(get_db)):
    try:
        reservation = create_reservation(db, payload)
    except ValueError as e:
        raise HTTPException(409, detail=str(e))
    await broadcast({"type": "reservation_created", "restaurant_id": reservation.restaurant_id})
    return {"id": reservation.id, "status": reservation.status, "message": "Reservation request sent. The restaurant must confirm it."}

@app.get("/api/admin/reservations", dependencies=[Depends(require_admin)])
def admin_reservations(db: Session = Depends(get_db)):
    rows = db.scalars(select(Reservation).order_by(Reservation.starts_at.desc()).limit(250)).all()
    return [{"id": r.id, "restaurant": r.restaurant.name, "restaurant_id": r.restaurant_id,
             "table": r.table.name, "table_id": r.table_id, "customer_name": r.customer_name,
             "customer_phone": r.customer_phone, "party_size": r.party_size,
             "starts_at": r.starts_at.isoformat(timespec="minutes"), "duration_minutes": r.duration_minutes,
             "status": r.status} for r in rows]

@app.patch("/api/admin/reservations/{reservation_id}", dependencies=[Depends(require_admin)])
async def update_reservation(reservation_id: int, payload: ReservationStatusUpdate, db: Session = Depends(get_db)):
    if payload.status not in {"confirmed", "cancelled"}:
        raise HTTPException(422, detail="Status must be confirmed or cancelled")
    reservation = db.get(Reservation, reservation_id)
    if not reservation:
        raise HTTPException(404, detail="Reservation not found")
    if payload.status == "confirmed":
        # Re-check at confirmation time to avoid confirming a stale pending request.
        from app.services.reservations import available_tables
        free = available_tables(db, reservation.restaurant_id, reservation.starts_at, reservation.party_size, reservation.duration_minutes)
        if reservation.table_id not in {t.id for t in free} and reservation.status != "confirmed":
            raise HTTPException(409, detail="Table is no longer available")
    reservation.status = payload.status
    db.commit()
    await broadcast({"type": "reservation_updated", "restaurant_id": reservation.restaurant_id})
    return {"id": reservation.id, "status": reservation.status}

@app.get("/api/admin/tables", dependencies=[Depends(require_admin)])
def admin_tables(restaurant_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(select(DiningTable).where(DiningTable.restaurant_id == restaurant_id).order_by(DiningTable.id)).all()
    return [{"id": t.id, "name": t.name, "capacity": t.capacity, "status": t.status} for t in rows]

@app.patch("/api/admin/tables/{table_id}", dependencies=[Depends(require_admin)])
async def update_table(table_id: int, payload: TableStatusUpdate, db: Session = Depends(get_db)):
    if payload.status not in {"available", "unavailable"}:
        raise HTTPException(422, detail="Status must be available or unavailable")
    table = db.get(DiningTable, table_id)
    if not table:
        raise HTTPException(404, detail="Table not found")
    table.status = payload.status
    db.commit()
    await broadcast({"type": "table_updated", "restaurant_id": table.restaurant_id})
    return {"id": table.id, "status": table.status}

@app.get("/api/ml/forecast", dependencies=[Depends(require_admin)])
def ml_forecast(restaurant_id: int, target_date: date, db: Session = Depends(get_db)):
    if not db.get(Restaurant, restaurant_id):
        raise HTTPException(404, detail="Restaurant not found")
    return forecast_demand(db, restaurant_id, datetime.combine(target_date, time(12, 0)))

@app.get("/api/ml/recommendations")
def ml_recommendations(party_size: int = 2, db: Session = Depends(get_db)):
    if party_size < 1 or party_size > 20:
        raise HTTPException(422, detail="party_size must be between 1 and 20")
    return [{"restaurant_id": item["restaurant"].id, "name": item["restaurant"].name, "score": round(item["score"], 4)}
            for item in recommend_restaurants(db, party_size)]

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connections.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in connections:
            connections.remove(ws)
