
import pytest

from app.exceptions import InvalidRequest, InvalidTransition, NotPermitted
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

def test_provisional_approval_requires_feedback():
    listing = make_listing()

    with pytest.raises(InvalidRequest):
        listing.transition("approve_provisionally", "admin")

    assert listing.status == "pending"
    assert listing.feedback is None

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

def test_rejection_requires_reason():
    listing = make_listing()

    with pytest.raises(InvalidRequest):
        listing.transition("reject", "admin")

    assert listing.status == "pending"
    assert listing.feedback is None


def test_provisional_listing_cannot_be_resubmitted():
    listing = make_listing("provisional")
    listing.feedback = "Additional documents required"

    with pytest.raises(InvalidTransition):
        listing.transition("resubmit", "landlord")

    assert listing.status == "provisional"
    assert listing.feedback == "Additional documents required"


def test_verified_listing_can_be_activated():
    listing = make_listing("verified")

    listing.transition("activate", "landlord")

    assert listing.status == "active"

def test_verified_listing_can_be_deactivated():
    listing = make_listing("verified")

    listing.transition(
        "deactivate",
        "admin",
        reason="admin_deactivated",
    )

    assert listing.status == "inactive"
    assert listing.deactivated_by == "admin"
    assert listing.deactivation_reason == "admin_deactivated"


def test_active_listing_can_be_deactivated():
    listing = make_listing("active")

    listing.transition(
        "deactivate",
        "landlord",
        reason="withdrawn",
    )

    assert listing.status == "inactive"
    assert listing.deactivated_by == "landlord"
    assert listing.deactivation_reason == "withdrawn"

def test_deactivation_requires_reason():
    listing = make_listing("active")

    with pytest.raises(InvalidRequest):
        listing.transition("deactivate", "landlord")

    assert listing.status == "active"
    assert listing.deactivated_by is None


def test_inactive_listing_can_be_activated_again():
    listing = make_listing("inactive")
    listing.deactivated_by = "landlord"
    listing.deactivation_reason = "withdrawn"

    listing.transition("activate", "landlord")

    assert listing.status == "active"
    assert listing.deactivated_by is None
    assert listing.deactivation_reason is None

def test_rented_listing_cannot_be_activated_again():
    listing = make_listing("inactive")
    listing.deactivated_by = "landlord"
    listing.deactivation_reason = "rented"

    with pytest.raises(InvalidTransition):
        listing.transition("activate", "landlord")

    assert listing.status == "inactive"

def test_admin_can_restore_inactive_listing():
    listing = make_listing("inactive")
    listing.deactivated_by = "admin"
    listing.deactivation_reason = "admin_deactivated"

    listing.transition("restore", "admin")

    assert listing.status == "active"
    assert listing.deactivated_by is None
    assert listing.deactivation_reason is None
    assert listing.feedback is None

def test_admin_cannot_activate_inactive_listing_directly():
    listing = make_listing("inactive")
    listing.deactivated_by = "admin"
    listing.deactivation_reason = "admin_deactivated"

    with pytest.raises(NotPermitted):
        listing.transition("activate", "admin")

    assert listing.status == "inactive"

def test_landlord_cannot_restore_inactive_listing():
    listing = make_listing("inactive")
    listing.deactivated_by = "admin"
    listing.deactivation_reason = "admin_deactivated"

    with pytest.raises(NotPermitted):
        listing.transition("restore", "landlord")

    assert listing.status == "inactive"

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

    with pytest.raises(NotPermitted):
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

    with pytest.raises(NotPermitted):
        listing.transition("reject", "landlord")

def test_provisional_listing_cannot_be_activated():
    listing = make_listing("provisional")

    with pytest.raises(InvalidTransition):
        listing.transition("activate", "landlord")

def test_student_cannot_activate_verified_listing():
    listing = make_listing("verified")

    with pytest.raises(NotPermitted):
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
        listing.transition("resubmit", "landlord")

    assert listing.status == "verified"

def test_verified_listing_cannot_be_rejected():
    listing = make_listing("verified")

    with pytest.raises(InvalidTransition):
        listing.transition(
            "reject",
            "admin",
            feedback="Further review required",
        )

    assert listing.status == "verified"

def test_significant_edit_returns_verified_listing_to_pending():
    listing = make_listing("verified")

    listing.transition("significant_edit", "landlord")

    assert listing.status == "pending"
    assert listing.feedback is None
    assert listing.deactivated_by is None
    assert listing.deactivation_reason is None

def test_significant_edit_returns_active_listing_to_pending():
    listing = make_listing("active")

    listing.transition("significant_edit", "landlord")

    assert listing.status == "pending"
    assert listing.feedback is None
    assert listing.deactivated_by is None
    assert listing.deactivation_reason is None

def test_significant_edit_returns_inactive_listing_to_pending():
    listing = make_listing("inactive")
    listing.deactivated_by = "landlord"
    listing.deactivation_reason = "withdrawn"

    listing.transition("significant_edit", "landlord")

    assert listing.status == "pending"
    assert listing.feedback is None
    assert listing.deactivated_by is None
    assert listing.deactivation_reason is None

def test_student_cannot_make_significant_edit():
    listing = make_listing("active")

    with pytest.raises(NotPermitted):
        listing.transition("significant_edit", "student")

    assert listing.status == "active"
   
def test_provisional_listing_cannot_use_significant_edit_transition():
    listing = make_listing("provisional")
    listing.feedback = "Additional documents required"

    with pytest.raises(InvalidTransition):
        listing.transition("significant_edit", "landlord")

    assert listing.status == "provisional"
    assert listing.feedback == "Additional documents required"


def test_pending_listing_cannot_use_significant_edit_transition():
    listing = make_listing("pending")

    with pytest.raises(InvalidTransition):
        listing.transition("significant_edit", "landlord")

    assert listing.status == "pending"

def test_rejected_listing_cannot_use_significant_edit_transition():
    listing = make_listing("rejected")
    listing.feedback = "Incorrect information"

    with pytest.raises(InvalidTransition):
        listing.transition("significant_edit", "landlord")

    assert listing.status == "rejected"
    assert listing.feedback == "Incorrect information"

def test_base_state_rejects_unauthorized_role():
    listing = make_listing("verified")
    state = listing.get_state()

    with pytest.raises(NotPermitted):
        state.require_role("student", {"admin"})

def test_admin_cannot_resubmit_provisional_listing():
    listing = make_listing("provisional")

    with pytest.raises(InvalidTransition):
        listing.transition("resubmit", "admin")

    assert listing.status == "provisional"

def test_admin_cannot_activate_verified_listing():
    listing = make_listing("verified")

    with pytest.raises(NotPermitted):
        listing.transition("activate", "admin")

    assert listing.status == "verified"