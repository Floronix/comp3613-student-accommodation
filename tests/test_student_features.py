"""Student-side feature tests: eligibility, auth, geography, filters, messaging.

Tests marked ``xfail(strict=True)`` cover defects that are still open. When the
fix lands the test passes, strict mode fails the run, and the marker must be
removed, so a fixed defect can't go unnoticed.
"""

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models.listing import Listing
from app.models.message import Message
from app.models.user import User
from app.utilities.security import encrypt_password, verify_password

BROWSE = "/api/student/listings"
MESSAGES = "/api/student/messages"
ACTIVE = "Verified Active Flat"  # seeded: st_augustine, 3500, "wifi,parking"
HIDDEN = [
    "Pending Unit",
    "Provisional Unit",
    "Verified Unit",
    "Inactive Unit",
    "Rejected Unit",
    "Other Landlord Pending",
]


@pytest.fixture
def ineligible(client, login):
    """A student with no registered ID and no provisional pathway."""
    with Session(engine) as session:
        session.add(
            User(
                username="nobody",
                email="nobody@example.com",
                password=encrypt_password("stud-dev"),
                role="student",
            )
        )
        session.commit()
    return login("nobody@example.com", "stud-dev")


@pytest.fixture
def actives(client, landlord, admin):
    """Two more active listings next to the seeded one, for filter tests."""
    make_active(
        client,
        landlord,
        admin,
        title="Hope Studio",
        area="mount_hope",
        price=2500,
        amenities="WiFi, Kitchen",
    )
    make_active(client, landlord, admin, title="Cheap Room", price=1500, amenities="laundry")


def submit(client, landlord, **overrides):
    body = {
        "title": "Test Flat",
        "area": "st_augustine",
        "price": 3000,
        "amenities": "wifi",
        "contact_phone": "555-0300",
        "contact_email": "landlord@example.com",
        **overrides,
    }
    return client.post("/api/landlord/listings", headers=landlord, json=body)


def make_active(client, landlord, admin, **overrides):
    listing = submit(client, landlord, **overrides).json()["listing"]
    url = f"/api/listings/{listing['id']}/transition"
    assert client.post(url, headers=admin, json={"action": "verify"}).status_code == 200
    assert client.post(url, headers=landlord, json={"action": "activate"}).status_code == 200
    return listing


def browse_titles(client, headers, **params):
    r = client.get(BROWSE, headers=headers, params=params)
    assert r.status_code == 200
    return {item["title"] for item in r.json()["listings"]}


def send(client, headers, listing_id, body="Is it still available?"):
    return client.post(MESSAGES, headers=headers, json={"listing_id": listing_id, "body": body})


def messages_for(listing_id):
    with Session(engine) as session:
        return session.exec(select(Message).where(Message.listing_id == listing_id)).all()


# --- Eligibility (AC 1, D11) ---


def test_user_eligibility_predicate_accepts_models_and_public_dicts():
    model_user = User(
        username="eligible",
        email="eligible@example.com",
        password="unused",
        role="student",
        student_id=" 202012345 ",
    )
    incoming_public_user = {"role": "student", "student_id": None, "provisional": 1}
    ineligible_public_user = {
        "role": "student",
        "student_id": " \t",
        "provisional": 0,
    }
    landlord_public_user = {
        "role": "landlord",
        "student_id": "202012345",
        "provisional": 0,
    }

    assert User.is_eligible_student(model_user)
    assert User.is_eligible_student(incoming_public_user)
    assert not User.is_eligible_student(ineligible_public_user)
    assert not User.is_eligible_student(landlord_public_user)


@pytest.mark.parametrize("who", ["student", "incoming"])
def test_registered_and_provisional_students_can_browse(client, request, who):
    assert ACTIVE in browse_titles(client, request.getfixturevalue(who))


def test_student_without_id_or_pathway_cannot_browse(client, ineligible):
    assert client.get(BROWSE, headers=ineligible).status_code == 403


def test_student_without_id_or_pathway_cannot_open_direct_link(
    client, ineligible, listing
):
    response = client.get(
        f"{BROWSE}/{listing[ACTIVE]['id']}", headers=ineligible
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "student eligibility required"


@pytest.mark.parametrize("who", ["admin", "landlord"])
def test_non_students_cannot_browse(client, request, who):
    assert client.get(BROWSE, headers=request.getfixturevalue(who)).status_code == 403


def test_browse_requires_user_header(client):
    assert client.get(BROWSE).status_code == 401


# --- Auth (AC 4, D19) ---


def test_login_never_returns_password_material(client):
    r = client.post(
        "/api/auth/login", json={"email": "student@example.com", "password": "stud-dev"}
    )
    assert r.status_code == 200
    assert "password" not in r.text


@pytest.mark.parametrize(
    "email,password",
    [("student@example.com", "wrong"), ("ghost@example.com", "stud-dev")],
)
def test_bad_credentials_are_rejected(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 401


def test_passwords_are_stored_hashed(client):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == "student@example.com")).one()
    assert user.password != "stud-dev"
    assert verify_password("stud-dev", user.password)


def test_user_list_never_exposes_passwords(client):
    login_response = client.post(
        "/login",
        data={"username": "admin", "password": "admin-dev"},
        follow_redirects=False,
    )
    assert login_response.status_code == 303

    response = client.get("/api/users")
    assert response.status_code == 200
    assert "password" not in response.text
    assert "password_hash" not in response.text


def test_user_list_requires_authentication(client):
    assert client.get("/api/users").status_code == 401


def test_user_list_denies_authenticated_non_admin(client):
    login_response = client.post(
        "/login",
        data={"username": "student", "password": "stud-dev"},
        follow_redirects=False,
    )
    assert login_response.status_code == 303
    assert client.get("/api/users").status_code == 403


# --- Geography (AC 2, D12); off-campus rejection is in test_integration.py ---


@pytest.mark.parametrize("area", ["st_augustine", "mount_hope"])
def test_campus_areas_are_accepted(client, landlord, area):
    r = submit(client, landlord, area=area)
    assert r.status_code == 200
    assert r.json()["listing"]["area"] == area
    assert r.json()["listing"]["status"] == "pending"


# --- Visibility and contact info (AC 6, AC 9, D9) ---


def test_only_active_listings_are_visible(client, student):
    titles = browse_titles(client, student)
    assert ACTIVE in titles
    assert titles.isdisjoint(HIDDEN)


def test_unknown_status_is_hidden_from_browse_and_direct_links(
    client, student, listing
):
    listing_id = listing[ACTIVE]["id"]
    with Session(engine) as session:
        row = session.get(Listing, listing_id)
        assert row is not None
        row.status = "unknown"
        session.add(row)
        session.commit()

    assert ACTIVE not in browse_titles(client, student)
    response = client.get(
        f"/api/student/listings/{listing_id}", headers=student
    )
    assert response.status_code == 404


def test_visible_listings_show_landlord_contact(client, student):
    items = client.get(BROWSE, headers=student).json()["listings"]
    flat = next(i for i in items if i["title"] == ACTIVE)
    assert flat["contact_phone"] == "555-0100"
    assert flat["contact_email"] == "landlord@example.com"


def test_deactivated_listing_disappears_from_browse(client, student, landlord, listing):
    r = client.post(
        f"/api/listings/{listing[ACTIVE]['id']}/transition",
        headers=landlord,
        json={"action": "deactivate", "reason": "rented"},
    )
    assert r.status_code == 200
    assert ACTIVE not in browse_titles(client, student)


def test_significant_edit_hides_listing_during_re_review(client, student, landlord, listing):
    r = client.patch(
        f"/api/landlord/listings/{listing[ACTIVE]['id']}",
        headers=landlord,
        json={"bedrooms": 3},
    )
    assert r.json()["listing"]["status"] == "pending"
    assert ACTIVE not in browse_titles(client, student)


# --- Filters (AC 9, D10) ---


def test_filter_by_area(client, student, actives):
    assert browse_titles(client, student, area="mount_hope") == {"Hope Studio"}
    assert browse_titles(client, student, area="st_augustine") == {ACTIVE, "Cheap Room"}


def test_max_price_is_inclusive(client, student, actives):
    assert browse_titles(client, student, max_price=2500) == {"Hope Studio", "Cheap Room"}
    assert browse_titles(client, student, max_price=1499) == set()


@pytest.mark.parametrize(
    "amenity,expected",
    [
        ("wifi", {ACTIVE, "Hope Studio"}),
        ("WIFI", {ACTIVE, "Hope Studio"}),
        (" kitchen ", {"Hope Studio"}),
        ("park", set()),  # whole amenity only, not a substring of "parking"
    ],
)
def test_amenity_filter_matches_whole_amenity_ignoring_case(
    client, student, actives, amenity, expected
):
    assert browse_titles(client, student, amenity=amenity) == expected


def test_filters_combine(client, student, actives):
    titles = browse_titles(client, student, area="st_augustine", max_price=3000, amenity="laundry")
    assert titles == {"Cheap Room"}
    assert browse_titles(client, student, area="mount_hope", amenity="laundry") == set()


# --- Messaging (AC 10, D14) ---


@pytest.mark.parametrize("who", ["student", "incoming"])
def test_eligible_student_can_message_active_listing(client, request, listing, who):
    headers = request.getfixturevalue(who)
    listing_id = listing[ACTIVE]["id"]

    r = send(client, headers, listing_id)

    assert r.status_code == 200
    [msg] = messages_for(listing_id)
    assert msg.id == r.json()["message_id"]
    assert msg.student_id == int(headers["X-User-Id"])
    assert msg.body == "Is it still available?"


@pytest.mark.parametrize("title", HIDDEN)
def test_cannot_message_hidden_listing(client, student, listing, title):
    listing_id = listing[title]["id"]
    assert send(client, student, listing_id).status_code in (404, 409)
    assert messages_for(listing_id) == []


def test_message_to_unknown_listing_is_404(client, student):
    assert send(client, student, 99999).status_code == 404


@pytest.mark.parametrize("body", ["", "   "])
def test_message_body_is_required(client, student, listing, body):
    assert send(client, student, listing[ACTIVE]["id"], body).status_code == 400


@pytest.mark.parametrize("who", ["admin", "landlord"])
def test_non_students_cannot_send_student_messages(client, request, listing, who):
    r = send(client, request.getfixturevalue(who), listing[ACTIVE]["id"])
    assert r.status_code == 403


@pytest.mark.xfail(strict=True, reason="D14: messaging has no eligibility check (#16)")
def test_ineligible_student_cannot_message(client, ineligible, listing):
    assert send(client, ineligible, listing[ACTIVE]["id"]).status_code == 403
