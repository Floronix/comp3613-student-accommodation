import jwt

from app.config import get_settings
from app.repositories.user import UserRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.utilities.security import verify_password


def test_save_password(test_session):
    repository = UserRepository(test_session)
    service = AuthService(repository)

    created = service.register_user("alice", "alice@example.com", "secret")
    saved = repository.get_by_username("alice")

    assert saved is not None
    assert created.id == saved.id
    assert saved.username == "alice"
    assert saved.email == "alice@example.com"
    assert saved.role == "regular_user"
    assert saved.password != "secret"
    assert verify_password("secret", saved.password)


def test_login(test_session):
    repository = UserRepository(test_session)
    service = AuthService(repository)
    service.register_user("alice", "alice@example.com", "secret")

    token = service.authenticate_user("alice", "secret")
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["sub"] == str(repository.get_by_username("alice").id)
    assert payload["role"] == "regular_user"


def test_register_user(test_session):
    repository = UserRepository(test_session)
    auth_service = AuthService(repository)
    auth_service.register_user("alice", "alice@example.com", "secret")

    users = UserService(repository).get_all_users()

    assert len(users) == 1
    assert users[0].username == "alice"
    assert users[0].email == "alice@example.com"

def create_test_listing(client, landlord):
    response = client.post(
        "/api/landlord/listings",
        headers=landlord,
        json={
            "title": "Integration Test Apartment",
            "area": "st_augustine",
            "price": 3000,
            "amenities": "WiFi, Parking",
            "contact_phone": "1234567",
            "contact_email": "landlord@example.com",
        },
    )

    assert response.status_code == 200
    return response.json()["listing"]


def test_admin_can_provisionally_approve_listing(client, landlord, admin):
    listing = create_test_listing(client, landlord)

    response = client.post(
        f"/api/listings/{listing['id']}/transition",
        headers=admin,
        json={
            "action": "approve_provisionally",
            "feedback": "Additional documents required",
        },
    )

    assert response.status_code == 200
    assert response.json()["listing"]["status"] == "provisional"
    assert response.json()["listing"]["feedback"] == "Additional documents required"

def test_admin_can_reject_listing_using_reason(client, landlord, admin):
    listing = create_test_listing(client, landlord)

    response = client.post(
        f"/api/listings/{listing['id']}/transition",
        headers=admin,
        json={
            "action": "reject",
            "reason": "Missing property documents",
        },
    )

    assert response.status_code == 200
    assert response.json()["listing"]["status"] == "rejected"
    assert response.json()["listing"]["feedback"] == "Missing property documents"

def test_admin_can_verify_listing(client, landlord, admin):
    listing = create_test_listing(client, landlord)

    response = client.post(
        f"/api/listings/{listing['id']}/transition",
        headers=admin,
        json={"action": "verify"},
    )

    assert response.status_code == 200
    assert response.json()["listing"]["status"] == "verified"


def test_landlord_can_activate_verified_listing(client, landlord, admin):
    listing = create_test_listing(client, landlord)

    # Admin verifies the listing first.
    client.post(
        f"/api/listings/{listing['id']}/transition",
        headers=admin,
        json={"action": "verify"},
    )

    # The listing owner activates it.
    response = client.post(
        f"/api/listings/{listing['id']}/transition",
        headers=landlord,
        json={"action": "activate"},
    )

    assert response.status_code == 200
    assert response.json()["listing"]["status"] == "active"


def test_landlord_can_deactivate_without_reason(client, landlord, admin):
    listing = create_test_listing(client, landlord)

    # Admin verifies the listing.
    client.post(
        f"/api/listings/{listing['id']}/transition",
        headers=admin,
        json={"action": "verify"},
    )

    # Landlord activates the listing.
    client.post(
        f"/api/listings/{listing['id']}/transition",
        headers=landlord,
        json={"action": "activate"},
    )

    # Landlord deactivates without providing a reason.
    response = client.post(
        f"/api/listings/{listing['id']}/transition",
        headers=landlord,
        json={"action": "deactivate"},
    )

    assert response.status_code == 200
    assert response.json()["listing"]["status"] == "inactive"
    assert response.json()["listing"]["deactivated_by"] == "landlord"
    assert response.json()["listing"]["deactivation_reason"] is None


def test_landlord_cannot_verify_listing(client, landlord):
    listing = create_test_listing(client, landlord)

    response = client.post(
        f"/api/listings/{listing['id']}/transition",
        headers=landlord,
        json={"action": "verify"},
    )

    assert response.status_code == 403


def test_landlord_cannot_manage_another_landlords_listing(
    client, landlord, landlord2, admin
):
    listing = create_test_listing(client, landlord)

    # Admin verifies the listing.
    client.post(
        f"/api/listings/{listing['id']}/transition",
        headers=admin,
        json={"action": "verify"},
    )

    # A different landlord attempts to activate it.
    response = client.post(
        f"/api/listings/{listing['id']}/transition",
        headers=landlord2,
        json={"action": "activate"},
    )

    assert response.status_code == 403


def test_invalid_transition_returns_conflict(client, landlord):
    listing = create_test_listing(client, landlord)

    response = client.post(
        f"/api/listings/{listing['id']}/transition",
        headers=landlord,
        json={"action": "activate"},
    )

    assert response.status_code == 409

def test_landlord_cannot_call_significant_edit_directly(
    client, landlord
):
    listing = create_test_listing(client, landlord)

    response = client.post(
        f"/api/listings/{listing['id']}/transition",
        headers=landlord,
        json={"action": "significant_edit"},
    )

    assert response.status_code == 400

def test_students_only_see_active_listings(
    client, landlord, student, admin
):
    # Create one listing that will remain pending.
    pending_listing = create_test_listing(client, landlord)

    # Create another listing and make it active.
    active_listing = create_test_listing(client, landlord)

    client.post(
        f"/api/listings/{active_listing['id']}/transition",
        headers=admin,
        json={"action": "verify"},
    )

    client.post(
        f"/api/listings/{active_listing['id']}/transition",
        headers=landlord,
        json={"action": "activate"},
    )

    response = client.get(
        "/api/student/listings",
        headers=student,
    )

    assert response.status_code == 200

    listings = response.json()["listings"]
    visible_ids = [item["id"] for item in listings]

    assert active_listing["id"] in visible_ids
    assert pending_listing["id"] not in visible_ids

    assert all(
        item["status"] == "active"
        for item in listings
    )

def test_landlord_cannot_resubmit_rejected_listing_without_edit(
    client, landlord, listing
):
    rejected = listing["Rejected Unit"]

    response = client.post(
        f"/api/listings/{rejected['id']}/transition",
        headers=landlord,
        json={"action": "resubmit"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "A rejected listing must be edited before it can be resubmitted"
    )




def test_landlord_can_resubmit_rejected_listing_after_edit(
    client, landlord, listing
):
    rejected = listing["Rejected Unit"]

    edit_response = client.patch(
        f"/api/landlord/listings/{rejected['id']}",
        headers=landlord,
        json={"photos": "updated-photo.jpg"},
    )

    assert edit_response.status_code == 200

    response = client.post(
        f"/api/listings/{rejected['id']}/transition",
        headers=landlord,
        json={"action": "resubmit"},
    )

    assert response.status_code == 200
    assert response.json()["listing"]["status"] == "pending"
    assert response.json()["listing"]["feedback"] is None
    assert response.json()["listing"]["edited_after_rejection"] is False


def test_landlord_cannot_activate_rejected_listing(client, landlord, listing):
    rejected = listing["Rejected Unit"]

    response = client.post(
        f"/api/listings/{rejected['id']}/transition",
        headers=landlord,
        json={"action": "activate"},
    )

    assert response.status_code == 409



def test_submit_transition_cannot_reset_verified_listing(client, landlord, admin):
    listing = create_test_listing(client, landlord)
    path = f"/api/listings/{listing['id']}/transition"

    verified = client.post(path, headers=admin, json={"action": "verify"})
    assert verified.status_code == 200
    assert verified.json()["listing"]["status"] == "verified"

    denied = client.post(path, headers=landlord, json={"action": "submit"})
    assert denied.status_code == 400

    activated = client.post(path, headers=landlord, json={"action": "activate"})
    assert activated.status_code == 200
    assert activated.json()["listing"]["status"] == "active"
