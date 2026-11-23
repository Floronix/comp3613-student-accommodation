
import pytest

from app.exceptions import InvalidTransition
from app.models.listing import Listing


def make_listing(status="pending"):
    return Listing(
        landlord_id=4,
        title="Student Apartment",
        area="st_augustine",
        price=3000,
        amenities="WiFi, Parking",
        contact_phone="1234567",
        contact_email="landlord@example.com",
        status=status,
        created_at="2026-11-23T00:00:00",
    )


def test_pending_listing_can_be_approved_provisionally():
    listing = make_listing()

    listing.transition(
        "approve_provisionally",
        "admin",
        "Additional documents required",
    )

    assert listing.status == "provisional"
    assert listing.feedback == "Additional documents required"


def test_pending_listing_can_be_verified():
    listing = make_listing()

    listing.transition("verify", "admin")

    assert listing.status == "verified"
    assert listing.feedback is None


def test_pending_listing_can_be_rejected():
    listing = make_listing()

    listing.transition("reject", "admin", "Incomplete information")

    assert listing.status == "rejected"
    assert listing.feedback == "Incomplete information"


def test_provisional_listing_can_be_resubmitted():
    listing = make_listing("provisional")
    listing.feedback = "Additional documents required"

    listing.transition("resubmit", "landlord")

    assert listing.status == "pending"
    assert listing.feedback is None


def test_verified_listing_can_be_activated():
    listing = make_listing("verified")

    listing.transition("activate", "landlord")

    assert listing.status == "active"


def test_active_listing_can_be_deactivated():
    listing = make_listing("active")

    listing.transition("deactivate", "landlord")

    assert listing.status == "inactive"
    assert listing.deactivated_by == "landlord"


def test_inactive_listing_can_be_activated_again():
    listing = make_listing("inactive")
    listing.deactivated_by = "landlord"

    listing.transition("activate", "landlord")

    assert listing.status == "active"
    assert listing.deactivated_by is None


def test_rejected_listing_can_be_resubmitted():
    listing = make_listing("rejected")
    listing.feedback = "Incorrect information"

    listing.transition("resubmit", "landlord")

    assert listing.status == "pending"
    assert listing.feedback is None
    assert listing.deactivated_by is None


def test_pending_listing_cannot_be_activated():
    listing = make_listing()

    with pytest.raises(InvalidTransition):
        listing.transition("activate", "landlord")


def test_active_listing_cannot_be_verified():
    listing = make_listing("active")

    with pytest.raises(InvalidTransition):
        listing.transition("verify", "admin")


def test_student_cannot_verify_listing():
    listing = make_listing()

    with pytest.raises(InvalidTransition):
        listing.transition("verify", "student")


def test_provisional_listing_can_be_verified():
    listing = make_listing("provisional")

    listing.transition("verify", "admin")

    assert listing.status == "verified"


def test_provisional_listing_can_be_rejected():
    listing = make_listing("provisional")

    listing.transition("reject", "admin", "Documents are insufficient")

    assert listing.status == "rejected"
    assert listing.feedback == "Documents are insufficient"


def test_landlord_cannot_reject_provisional_listing():
    listing = make_listing("provisional")

    with pytest.raises(InvalidTransition):
        listing.transition("reject", "landlord")


def test_provisional_listing_cannot_be_activated():
    listing = make_listing("provisional")

    with pytest.raises(InvalidTransition):
        listing.transition("activate", "landlord")


def test_verified_listing_can_be_rejected():
    listing = make_listing("verified")

    listing.transition("reject", "admin", "Further review required")

    assert listing.status == "rejected"
    assert listing.feedback == "Further review required"


def test_student_cannot_activate_verified_listing():
    listing = make_listing("verified")

    with pytest.raises(InvalidTransition):
        listing.transition("activate", "student")


def test_unknown_listing_status_is_rejected():
    listing = make_listing("unknown")

    with pytest.raises(InvalidTransition):
        listing.transition("verify", "admin")

def test_inactive_listing_rejects_invalid_action():
    listing = make_listing("inactive")

    with pytest.raises(InvalidTransition):
        listing.transition("verify", "admin")


def test_verified_listing_rejects_invalid_action():
    listing = make_listing("verified")

    with pytest.raises(InvalidTransition):
        listing.transition("deactivate", "landlord")


def test_base_state_rejects_unauthorized_role():
    listing = make_listing("verified")
    state = listing.get_state()

    with pytest.raises(InvalidTransition):
        state.require_role("student", {"admin"})

def test_admin_can_resubmit_provisional_listing():
    listing = make_listing("provisional")

    listing.transition("resubmit", "admin")

    assert listing.status == "pending"
    assert listing.feedback is None

def test_admin_can_activate_verified_listing():
    listing = make_listing("verified")

    listing.transition("activate", "admin")

    assert listing.status == "active"