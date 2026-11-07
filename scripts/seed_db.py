from app.db import init_db, SessionLocal
from app.models import Restaurant, DiningTable

def seed():
    init_db()
    db = SessionLocal()
    try:
        if db.query(Restaurant).count():
            print("Database already has restaurants; skipping seed.")
            return
        # Fictional demo venues and coordinates around central Yerevan.
        venues = [
            ("Apricot Yard (Demo)", "Armenian", "Saryan St, Yerevan", "Kentron", 40.1830, 44.5070, "Demo listing — not a real partner."),
            ("Cascade Table (Demo)", "European", "Tamanyan St, Yerevan", "Kentron", 40.1910, 44.5150, "Demo listing — not a real partner."),
            ("Arabkir Kitchen (Demo)", "Mixed", "Komitas Ave, Yerevan", "Arabkir", 40.2050, 44.5050, "Demo listing — not a real partner."),
            ("Vernissage Bistro (Demo)", "Café", "Hanrapetutyan St, Yerevan", "Kentron", 40.1770, 44.5150, "Demo listing — not a real partner.")
        ]
        for name, cuisine, address, district, lat, lon, desc in venues:
            r = Restaurant(name=name, cuisine=cuisine, address=address, district=district,
                           latitude=lat, longitude=lon, description=desc)
            r.tables = [DiningTable(name=f"T{i}", capacity=cap) for i, cap in enumerate([2, 2, 4, 4, 6], 1)]
            db.add(r)
        db.commit()
        print("Seeded 4 fictional demo restaurants.")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
