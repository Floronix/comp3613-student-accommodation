import os
os.environ["DATABASE_URI"] = "sqlite:///test.db"

import pytest
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.seed import seed, seed_all_states
import app.models


@pytest.fixture
def test_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def client():
    """Fresh seeded database (all six states) and an API client."""
    seed(reset=True)
    seed_all_states()
    return TestClient(fastapi_app)


@pytest.fixture
def login(client):
    def _login(email, password):
        r = client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200
        return {"X-User-Id": str(r.json()["user"]["id"])}

    return _login


@pytest.fixture
def admin(login):
    return login("admin@example.com", "admin-dev")


@pytest.fixture
def student(login):
    return login("student@example.com", "stud-dev")


@pytest.fixture
def incoming(login):
    return login("incoming@example.com", "stud-dev")


@pytest.fixture
def landlord(login):
    return login("landlord@example.com", "land-dev")


@pytest.fixture
def landlord2(login):
    return login("landlord2@example.com", "land-dev")


@pytest.fixture
def listing(client, admin):
    """Seeded listings keyed by title, e.g. listing["Rejected Unit"]["id"]."""
    rows = client.get("/api/admin/listings", headers=admin).json()["listings"]
    return {r["title"]: r for r in rows}
