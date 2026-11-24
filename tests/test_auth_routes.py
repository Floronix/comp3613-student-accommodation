"""Defensive integration coverage for the scenario API boundary."""

import pytest

API_ROUTES = [
    (
        "post",
        "/api/landlord/listings",
        {
            "title": "Route Guard Flat",
            "area": "st_augustine",
            "price": 1800,
            "amenities": "wifi",
            "contact_phone": "555-0199",
            "contact_email": "landlord@example.com",
        },
    ),
    ("get", "/api/landlord/listings", None),
    ("post", "/api/listings/1/transition", {"action": "verify"}),
    ("patch", "/api/landlord/listings/1", {"contact_phone": "555-0199"}),
    ("delete", "/api/landlord/listings/1", None),
    ("get", "/api/student/listings", None),
    ("get", "/api/student/listings/1", None),
    ("get", "/api/admin/listings", None),
    (
        "post",
        "/api/student/messages",
        {"listing_id": 1, "body": "Is this available?"},
    ),
]


def _request(client, method, path, payload=None, headers=None):
    kwargs = {}
    if payload is not None:
        kwargs["json"] = payload
    if headers is not None:
        kwargs["headers"] = headers
    return getattr(client, method)(path, **kwargs)


def test_every_scenario_route_requires_a_user_id(client):
    for method, path, payload in API_ROUTES:
        response = _request(client, method, path, payload)
        assert response.status_code == 401, f"{method.upper()} {path} accepted no identity"


def test_every_scenario_route_rejects_a_non_integer_user_id(client):
    for method, path, payload in API_ROUTES:
        response = _request(
            client,
            method,
            path,
            payload,
            headers={"X-User-Id": "not-a-number"},
        )
        assert response.status_code == 400, f"{method.upper()} {path} accepted an invalid identity"
        assert response.json()["detail"] == "X-User-Id must be int"


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_students_cannot_edit_or_delete_listings(
    client, student, listing, admin, method
):
    target = listing["Pending Unit"]
    path = f"/api/landlord/listings/{target['id']}"

    if method == "patch":
        response = client.patch(
            path,
            headers=student,
            json={"contact_phone": "555-9999"},
        )
    else:
        response = client.delete(path, headers=student)

    assert response.status_code == 403
    assert response.json()["detail"] == "landlords only"

    remaining = client.get("/api/admin/listings", headers=admin).json()["listings"]
    unchanged = next(row for row in remaining if row["id"] == target["id"])
    assert unchanged["contact_phone"] == target["contact_phone"]


@pytest.mark.parametrize(
    "payload",
    [{}, {"email": "student@example.com"}, {"password": "stud-dev"}],
)
def test_login_rejects_incomplete_credentials(client, payload):
    response = client.post("/api/auth/login", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]


def test_transition_rejects_non_integer_listing_id(client, admin):
    response = client.post(
        "/api/listings/not-an-integer/transition",
        headers=admin,
        json={"action": "verify"},
    )

    assert response.status_code == 422
