import itertools

import pytest

from app.exceptions import InvalidRequest, InvalidTransition, NotPermitted
from app.models.listing import Listing

STATES = ["pending", "provisional", "verified", "active", "inactive", "rejected"]
ACTIONS = [
    "approve_provisionally",
    "verify",
    "reject",
    "activate",
    "deactivate",
    "significant_edit",
    "restore",
    "resubmit",
]
ROLES = ["admin", "landlord", "student"]

# (state, action, role) -> resulting status. Mirrors docs/transitions.md.
# 14 table rows; "deactivate" is allowed for landlord or admin, giving 16 entries.
ALLOWED = {
    ("pending", "approve_provisionally", "admin"): "provisional",
    ("pending", "verify", "admin"): "verified",
    ("pending", "reject", "admin"): "rejected",
    ("provisional", "verify", "admin"): "verified",
    ("provisional", "reject", "admin"): "rejected",
    ("verified", "activate", "landlord"): "active",
    ("verified", "deactivate", "landlord"): "inactive",
    ("verified", "deactivate", "admin"): "inactive",
    ("verified", "significant_edit", "landlord"): "pending",
    ("active", "deactivate", "landlord"): "inactive",
    ("active", "deactivate", "admin"): "inactive",
    ("active", "significant_edit", "landlord"): "pending",
    ("inactive", "activate", "landlord"): "active",
    ("inactive", "restore", "admin"): "active",
    ("inactive", "significant_edit", "landlord"): "pending",
    ("rejected", "resubmit", "landlord"): "pending",
}


def make_listing(status):
    return Listing(
        landlord_id=4,
        title="Matrix Apartment",
        area="st_augustine",
        price=3000,
        amenities="wifi",
        contact_phone="1234567",
        contact_email="landlord@example.com",
        status=status,
        created_at="2026-11-23T00:00:00",
    )


def prepared(status, action):
    """A listing in `status` with the preconditions the allowed action needs."""
    listing = make_listing(status)
    if status == "inactive":
        listing.deactivated_by = "admin" if action == "restore" else "landlord"
    if status == "rejected":
        listing.edited_after_rejection = True
    return listing


def test_matrix_has_expected_number_of_allowed_transitions():
    assert len(ALLOWED) == 16


@pytest.mark.parametrize(
    "state,action,role", list(itertools.product(STATES, ACTIONS, ROLES))
)
def test_transition_matrix(state, action, role):
    listing = prepared(state, action)
    expected = ALLOWED.get((state, action, role))

    if expected is None:
        permitted_roles = {
            allowed_role
            for allowed_state, allowed_action, allowed_role in ALLOWED
            if (allowed_state, allowed_action) == (state, action)
        }
        error = (
            NotPermitted
            if permitted_roles and role not in permitted_roles
            else InvalidTransition
        )
        with pytest.raises(error):
            listing.transition(action, role, feedback="Reviewer note")
        assert listing.status == state
    else:
        listing.transition(action, role, feedback="Reviewer note")
        assert listing.status == expected


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("action", ["submit", "bogus"])
def test_unknown_actions_are_rejected_in_every_state(state, action):
    listing = prepared(state, action)

    with pytest.raises(InvalidTransition):
        listing.transition(action, "admin", feedback="Reviewer note")

    assert listing.status == state


@pytest.mark.parametrize(
    "state,action",
    [
        ("pending", "approve_provisionally"),
        ("pending", "reject"),
        ("provisional", "reject"),
    ],
)
def test_admin_decisions_require_feedback(state, action):
    listing = prepared(state, action)

    with pytest.raises(InvalidRequest):
        listing.transition(action, "admin")

    assert listing.status == state


@pytest.mark.parametrize(
    "deactivated_by,action,role",
    [
        ("admin", "activate", "landlord"),
        ("landlord", "restore", "admin"),
    ],
)
def test_reactivation_depends_on_who_deactivated(deactivated_by, action, role):
    listing = make_listing("inactive")
    listing.deactivated_by = deactivated_by

    with pytest.raises(InvalidTransition):
        listing.transition(action, role)

    assert listing.status == "inactive"


@pytest.mark.parametrize("role", ["landlord", "admin"])
@pytest.mark.parametrize("state", ["verified", "active"])
def test_deactivate_records_who_did_it(state, role):
    listing = make_listing(state)

    listing.transition("deactivate", role)

    assert listing.status == "inactive"
    assert listing.deactivated_by == role


# ---- Visibility ----------------------------------------------------------


@pytest.mark.parametrize(
    "state,visible",
    [
        ("pending", False),
        ("provisional", False),
        ("verified", False),
        ("active", True),
        ("inactive", False),
        ("rejected", False),
    ],
)
def test_only_active_is_visible_to_students(state, visible):
    assert make_listing(state).is_visible_to_students() is visible


def student_titles(client, student):
    response = client.get("/api/student/listings", headers=student)
    assert response.status_code == 200
    return {row["title"] for row in response.json()["listings"]}


def test_students_only_see_the_active_seeded_listing(client, student):
    # The seed has one listing in each of the six states.
    assert student_titles(client, student) == {"Verified Active Flat"}


def test_deactivating_hides_and_reactivating_shows(client, student, landlord, listing):
    url = f"/api/listings/{listing['Verified Active Flat']['id']}/transition"

    assert client.post(url, headers=landlord, json={"action": "deactivate"}).status_code == 200
    assert "Verified Active Flat" not in student_titles(client, student)

    assert client.post(url, headers=landlord, json={"action": "activate"}).status_code == 200
    assert "Verified Active Flat" in student_titles(client, student)


def test_significant_edit_hides_an_active_listing(client, student, landlord, listing):
    listing_id = listing["Verified Active Flat"]["id"]

    response = client.patch(
        f"/api/landlord/listings/{listing_id}",
        headers=landlord,
        json={"bedrooms": 3},
    )

    assert response.status_code == 200
    assert response.json()["listing"]["status"] == "pending"
    assert "Verified Active Flat" not in student_titles(client, student)


def test_admin_deactivated_listing_stays_hidden_until_admin_restores(
    client, student, landlord, admin, listing
):
    url = f"/api/listings/{listing['Verified Active Flat']['id']}/transition"

    assert client.post(url, headers=admin, json={"action": "deactivate"}).status_code == 200
    assert "Verified Active Flat" not in student_titles(client, student)

    # The landlord cannot bring back an admin-deactivated listing.
    blocked = client.post(url, headers=landlord, json={"action": "activate"})
    assert blocked.status_code == 409
    assert "Verified Active Flat" not in student_titles(client, student)

    assert client.post(url, headers=admin, json={"action": "restore"}).status_code == 200
    assert "Verified Active Flat" in student_titles(client, student)