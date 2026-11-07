from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Reservation, Restaurant

def _features(dt: datetime, party_size: int, restaurant_id: int):
    return [dt.hour, dt.weekday(), dt.month, party_size, restaurant_id]

def forecast_demand(db: Session, restaurant_id: int, target_date: datetime):
    rows = db.scalars(select(Reservation).where(
        Reservation.restaurant_id == restaurant_id,
        Reservation.status.in_(("pending", "confirmed"))
    )).all()
    # Use hourly booking counts as supervised examples when there is enough history.
    if len(rows) >= 12:
        try:
            import numpy as np
            from sklearn.ensemble import RandomForestRegressor
            X, y = [], []
            counts = {}
            for r in rows:
                key = (r.starts_at.date(), r.starts_at.hour)
                counts[key] = counts.get(key, 0) + 1
            for (day, hour), count in counts.items():
                dt = datetime.combine(day, datetime.min.time()).replace(hour=hour)
                X.append(_features(dt, 2, restaurant_id))
                y.append(count)
            if len(X) >= 8:
                model = RandomForestRegressor(n_estimators=80, random_state=42)
                model.fit(np.asarray(X), np.asarray(y))
                predictions = []
                for hour in range(11, 24):
                    dt = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                    predictions.append({"hour": hour, "expected_bookings": round(max(0, float(model.predict([_features(dt, 2, restaurant_id)])[0])), 2)})
                return {"method": "random_forest", "training_examples": len(X), "predictions": predictions}
        except Exception:
            pass
    # Transparent cold-start baseline: counts for matching weekday/hour, averaged where possible.
    predictions = []
    for hour in range(11, 24):
        same_hour = [r for r in rows if r.starts_at.hour == hour and r.starts_at.weekday() == target_date.weekday()]
        predictions.append({"hour": hour, "expected_bookings": round(len(same_hour) / max(1, len({r.starts_at.date() for r in rows if r.starts_at.weekday() == target_date.weekday()})), 2)})
    return {"method": "baseline", "training_examples": len(rows), "predictions": predictions}

def recommend_restaurants(db: Session, party_size: int):
    restaurants = db.scalars(select(Restaurant).where(Restaurant.is_active == True)).all()  # noqa: E712
    # Cold-start ranking: sufficient table capacity first; later can be trained on clicks/bookings.
    ranked = []
    for restaurant in restaurants:
        capacities = [t.capacity for t in restaurant.tables if t.status == "available" and t.capacity >= party_size]
        ranked.append((restaurant, min(capacities) if capacities else 999))
    ranked.sort(key=lambda x: (x[1], x[0].name))
    return [{"restaurant": r, "score": 1.0 / (1 + score) if score < 999 else 0.0} for r, score in ranked]
