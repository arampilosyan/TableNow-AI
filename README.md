# TableNow AI — Yerevan Restaurant Reservations

A full-stack starter platform for discovering restaurants, viewing table availability, and requesting/confirming reservations. Includes a restaurant admin dashboard, live updates over WebSockets, SQLite for local development, PostgreSQL support, and ML demand forecasting with a safe fallback.

## Features

- Customer experience: restaurant directory, date/time/party-size search, available tables, reservation requests.
- Restaurant admin: manage table status, view reservations, confirm/cancel bookings.
- Live availability: WebSocket broadcasts when tables or reservations change.
- Double-booking protection: database transaction + overlap checks.
- ML: demand forecast and restaurant ranking/recommendation features. The forecasting module trains a scikit-learn model when enough data exists and otherwise uses a transparent baseline.
- Seed data for Yerevan (fictional demo venues; not real-time partner inventory).
- API docs at `/docs`.

> **Important:** Seed venues and availability are demo data. Real availability requires each restaurant to onboard and maintain its floor plan/inventory, or integrate its POS/reservation API. Do not represent demo data as live real-world availability.

## Quick start

Requires Python 3.10+.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
python scripts/seed_db.py
uvicorn app.main:app --reload
```

Open:
- Customer app: http://127.0.0.1:8000
- Admin dashboard: http://127.0.0.1:8000/admin
- API docs: http://127.0.0.1:8000/docs

Demo admin access:
- Header key: `X-Admin-Key: dev-admin-key`
- The included browser admin UI sends this key for local demo convenience.
- Change `ADMIN_API_KEY` before any deployment. This starter intentionally uses a simple shared key; production should use individual accounts, password hashing, sessions/JWT, roles, CSRF protection and audit logs.

## Configuration

See `.env.example`. `DATABASE_URL` defaults to SQLite. For PostgreSQL, set for example:

```env
DATABASE_URL=postgresql+psycopg://tablenow:password@localhost:5432/tablenow
```

Then run the same app. Create tables with `python scripts/seed_db.py` or `python -c "from app.db import init_db; init_db()"`.

## Main API

- `GET /api/restaurants`
- `GET /api/availability?restaurant_id=1&date=2026-12-01&time=19:00&party_size=2`
- `POST /api/reservations`
- `GET /api/admin/reservations` (requires `X-Admin-Key`)
- `PATCH /api/admin/reservations/{id}` (requires `X-Admin-Key`)
- `PATCH /api/admin/tables/{id}` (requires `X-Admin-Key`)
- `GET /api/ml/forecast?restaurant_id=1&date=2026-12-01` (requires `X-Admin-Key`)
- `GET /api/ml/recommendations?party_size=2`

Reservation request example:

```json
{
  "restaurant_id": 1,
  "table_id": 1,
  "customer_name": "Ani",
  "customer_phone": "+37499123456",
  "party_size": 2,
  "date": "2026-12-01",
  "time": "19:00",
  "duration_minutes": 120
}
```

New reservations start as `pending`. A restaurant admin must confirm them. Confirmed bookings block overlapping time slots.

## Project structure

```text
app/
  main.py          FastAPI routes and WebSocket
  models.py        SQLAlchemy models
  schemas.py       Pydantic request/response schemas
  db.py            Database setup
  services/
    reservations.py  availability and booking rules
    ml.py            demand forecasting and recommendations
  static/
    index.html       customer UI
    admin.html       restaurant admin UI
    styles.css
    app.js
    admin.js
tests/
scripts/seed_db.py
```

## Tests

```bash
pytest -q
```

Tests use an isolated SQLite database and validate availability and booking conflict prevention.

## ML notes

The ML pipeline uses hour, weekday, month, party size and restaurant ID as features. It trains a RandomForestRegressor from historical reservations when enough examples exist. For a fresh installation, the system reports a baseline forecast until there is sufficient data. This avoids pretending a model has learned from nonexistent history.

## Production checklist

- Use PostgreSQL, HTTPS, secret manager and backups.
- Replace shared admin key with real authentication and role-based access.
- Add phone/email verification and customer account management.
- Add rate limiting, input abuse protection, audit logs and monitoring.
- Integrate each restaurant's POS/reservation system or require staff to keep the dashboard current.
- Obtain consent and comply with applicable privacy/data-protection rules.
- Validate restaurant addresses, coordinates, opening hours and actual inventory before public launch.
