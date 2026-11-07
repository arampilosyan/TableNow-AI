import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.main import app
from app.models import Restaurant, DiningTable

@pytest.fixture()
def client(monkeypatch):
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    TestingSession=sessionmaker(bind=engine,autoflush=False,autocommit=False)
    Base.metadata.create_all(engine)
    db=TestingSession()
    r=Restaurant(name="Test Bistro",cuisine="Test",address="Yerevan",district="Kentron",latitude=40.1,longitude=44.5)
    r.tables=[DiningTable(name="T1",capacity=2),DiningTable(name="T2",capacity=4)]
    db.add(r);db.commit();db.close()
    def override():
        s=TestingSession()
        try: yield s
        finally: s.close()
    app.dependency_overrides[get_db]=override
    import app.main as main_module
    monkeypatch.setattr(main_module, "ADMIN_KEY", "test-key")
    with TestClient(app) as c: yield c
    app.dependency_overrides.clear()
