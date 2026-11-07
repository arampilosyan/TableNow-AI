def test_health_and_restaurants(client):
    assert client.get("/health").json()["status"]=="ok"
    rows=client.get("/api/restaurants").json()
    assert len(rows)==1 and rows[0]["name"]=="Test Bistro"

def test_availability_and_reservation(client):
    params={"restaurant_id":1,"date":"2030-01-01","time":"19:00","party_size":2}
    free=client.get("/api/availability",params=params)
    assert free.status_code==200 and len(free.json())==2
    payload={"restaurant_id":1,"table_id":1,"customer_name":"Ani","customer_phone":"+37499123456",
             "party_size":2,"date":"2030-01-01","time":"19:00","duration_minutes":120}
    created=client.post("/api/reservations",json=payload)
    assert created.status_code==201
    again=client.get("/api/availability",params=params).json()
    assert all(t["id"]!=1 for t in again)

def test_overlapping_booking_rejected(client):
    payload={"restaurant_id":1,"table_id":1,"customer_name":"Ani","customer_phone":"+37499123456",
             "party_size":2,"date":"2030-01-01","time":"19:00","duration_minutes":120}
    assert client.post("/api/reservations",json=payload).status_code==201
    payload["customer_name"]="Aram"
    payload["time"]="20:00"
    response=client.post("/api/reservations",json=payload)
    assert response.status_code==409

def test_admin_requires_key(client):
    assert client.get("/api/admin/reservations").status_code==401
    assert client.get("/api/admin/reservations",headers={"X-Admin-Key":"test-key"}).status_code==200
