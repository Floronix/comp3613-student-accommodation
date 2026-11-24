"""Listing CRUD, browse filters, messaging, reports, and lifecycle transitions.

Failures raise the exceptions in app.exceptions; app.main maps them to
HTTP status codes (400, 403, 404, 409).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from app.database import engine
from app.exceptions import InvalidRequest, NotFound, NotPermitted
from app.models.user import User
from app.models.listing import Listing
from app.models.message import Message
from app.models.report import Report
from app.repositories import ListingRepository, MessageRepository, ReportRepository
from app.services.lifecycle import ACTIONS

ALLOWED_AREAS = {"st_augustine", "mount_hope"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_amenities(raw: str) -> list[str]:
    return [a.strip().lower() for a in (raw or "").split(",") if a.strip()]


def _require_role(actor: dict[str, Any], error: str, *roles: str) -> None:
    if actor["role"] not in roles:
        raise NotPermitted(error)


def _require_eligible_student(actor: dict[str, Any]) -> None:
    _require_role(actor, "students only", "student")
    if not User.is_eligible_student(actor):
        raise NotPermitted("student eligibility required")


def _get_listing(repo: ListingRepository, listing_id: int, actor: dict[str, Any]) -> Listing:
    """Fetch a listing, enforcing that landlords only touch their own."""
    listing = repo.get_by_id(listing_id)

    if listing is None:
        raise NotFound("listing not found")

    if actor["role"] == "landlord" and listing.landlord_id != actor["id"]:
        raise NotPermitted("you can only manage your own listings")

    return listing


def submit_listing(
    actor: dict[str, Any],
    *,
    title: str,
    area: str,
    price: int,
    amenities: str,
    contact_phone: str,
    contact_email: str,
    photos: str = "",
    bedrooms: int = 0,
    bathrooms: int = 0,
    has_kitchen: bool = False,
    description: str = "",
) -> dict[str, Any]:
    _require_role(actor, "landlords only", "landlord")

    if area not in ALLOWED_AREAS:
        raise InvalidRequest("invalid accommodation area")

    if price <= 0:
        raise InvalidRequest("price must be positive")

    if not amenities.strip():
        raise InvalidRequest("amenities are required")

    if bedrooms < 0:
        raise InvalidRequest("bedrooms cannot be negative")

    if bathrooms < 0:
        raise InvalidRequest("bathrooms cannot be negative")

    with Session(engine) as session:
        listing = ListingRepository(session).save(
            Listing(
                landlord_id=actor["id"],
                title=title,
                area=area,
                price=price,
                amenities=amenities,
                contact_phone=contact_phone,
                contact_email=contact_email,
                photos=photos,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                has_kitchen=has_kitchen,
                description=description,
                status="pending",
                created_at=_now(),
            )
        )

        return {"ok": True, "listing": listing.model_dump()}


def transition(
    actor: dict[str, Any],
    listing_id: int,
    action: str,
    feedback: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    _require_role(actor, "admin/landlord only", "admin", "landlord")

    # submit and significant_edit are triggered by create/edit, not by clients.
    if action not in ACTIONS:
        raise InvalidRequest(f"action must be one of {ACTIONS}")

    with Session(engine) as session:
        repo = ListingRepository(session)
        listing = _get_listing(repo, listing_id, actor)

        # The listing's current State object enforces the rest (role, reason,
        # allowed transition) and raises NotPermitted / InvalidRequest /
        # InvalidTransition. The spec names the field `reason`; `feedback`
        # is accepted too.
        listing.transition(
            action=action,
            actor_role=actor["role"],
            feedback=feedback or reason,
            reason=reason,
        )

        listing = repo.save(listing)

        return {"ok": True, "listing": listing.model_dump()}


def edit_listing(
    actor: dict[str, Any],
    listing_id: int,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Edit a landlord's listing and trigger review for significant changes."""

    _require_role(actor, "landlords only", "landlord")

    allowed_fields = {
        "title",
        "area",
        "price",
        "amenities",
        "contact_phone",
        "contact_email",
        "photos",
        "bedrooms",
        "bathrooms",
        "has_kitchen",
        "description",
    }

    updates = {
        key: value
        for key, value in updates.items()
        if key in allowed_fields and value is not None
    }

    if not updates:
        raise InvalidRequest("no valid changes provided")

    if "area" in updates and updates["area"] not in ALLOWED_AREAS:
        raise InvalidRequest("invalid accommodation area")

    if "price" in updates and updates["price"] <= 0:
        raise InvalidRequest("price must be positive")

    for field in ("bedrooms", "bathrooms"):
        if field in updates and updates[field] < 0:
            raise InvalidRequest(f"{field} cannot be negative")

    significant_fields = {
        "title",
        "area",
        "price",
        "amenities",
        "bedrooms",
        "bathrooms",
        "has_kitchen",
        "description",
    }

    with Session(engine) as session:
        repo = ListingRepository(session)
        listing = _get_listing(repo, listing_id, actor)

        changed_fields = {
            field
            for field, value in updates.items()
            if getattr(listing, field) != value
        }

        if listing.status == "rejected" and changed_fields:
            listing.edited_after_rejection = True

        significant_change = bool(
            changed_fields.intersection(significant_fields)
        )

        if significant_change and listing.status in {
            "verified",
            "active",
            "inactive",
        }:
            listing.transition(
                action="significant_edit",
                actor_role="landlord",
            )

        for field, value in updates.items():
            setattr(listing, field, value)

        listing = repo.save(listing)

        return {"ok": True, "listing": listing.model_dump()}


def remove_listing(
    actor: dict[str, Any],
    listing_id: int,
) -> dict[str, Any]:
    """Permanently remove a landlord's listing and its messages and reports."""

    _require_role(actor, "landlords only", "landlord")

    with Session(engine) as session:
        listing_repo = ListingRepository(session)

        listing = _get_listing(listing_repo, listing_id, actor)

        try:
            MessageRepository(session).delete_for_listing(listing_id)
            ReportRepository(session).delete_for_listing(listing_id)
            listing_repo.delete(listing)
        except Exception:
            session.rollback()
            raise

        return {"ok": True, "message": "Listing removed successfully"}


def browse_for_students(
    actor: dict[str, Any],
    *,
    area: str | None = None,
    max_price: int | None = None,
    amenity: str | None = None,
) -> dict[str, Any]:
    _require_eligible_student(actor)

    with Session(engine) as session:
        items = [
            row.model_dump()
            for row in ListingRepository(session).list_all()
            if row.is_visible_to_students()
        ]

    results = []

    for item in items:
        if area and item["area"] != area:
            continue

        if max_price is not None and int(item["price"]) > max_price:
            continue

        if amenity:
            listing_amenities = _parse_amenities(item["amenities"])
            if amenity.strip().lower() not in listing_amenities:
                continue

        results.append(item)

    return {"ok": True, "listings": results}


def get_for_student(actor: dict[str, Any], listing_id: int) -> dict[str, Any]:
    """One listing by direct link. Hidden listings look the same as missing ones."""
    _require_eligible_student(actor)

    with Session(engine) as session:
        item = _get_visible_listing(ListingRepository(session), listing_id).model_dump()

    return {"ok": True, "listing": item}


def _get_visible_listing(repo: ListingRepository, listing_id: int) -> Listing:
    """A listing students may see; hidden ones raise the same 404 as missing ones."""
    listing = repo.get_by_id(listing_id)

    if listing is None or not listing.is_visible_to_students():
        raise NotFound("listing not found")

    return listing


def _list(status: str | None, landlord_id: int | None = None) -> dict[str, Any]:
    with Session(engine) as session:
        rows = ListingRepository(session).list_all(status, landlord_id)
        return {"ok": True, "listings": [row.model_dump() for row in rows]}


def list_for_admin(actor: dict[str, Any], *, status: str | None = None) -> dict[str, Any]:
    """Every listing with its status, feedback and deactivation details."""
    _require_role(actor, "admin only", "admin")
    return _list(status)


def list_for_landlord(actor: dict[str, Any], *, status: str | None = None) -> dict[str, Any]:
    """The landlord's own listings with status and admin feedback."""
    _require_role(actor, "landlords only", "landlord")
    return _list(status, landlord_id=actor["id"])


def send_message(
    actor: dict[str, Any],
    listing_id: int,
    body: str,
) -> dict[str, Any]:
    """Start or continue the student's thread with a listing's landlord."""
    _require_eligible_student(actor)

    if not body.strip():
        raise InvalidRequest("body required")

    with Session(engine) as session:
        _get_visible_listing(ListingRepository(session), listing_id)

        message = MessageRepository(session).create(
            Message(
                listing_id=listing_id,
                student_id=actor["id"],
                sender_role="student",
                body=body,
                created_at=_now(),
            )
        )

        return {"ok": True, "message_id": message.id}


def list_student_messages(
    actor: dict[str, Any], *, listing_id: int | None = None
) -> dict[str, Any]:
    """The student's own threads, including landlord replies."""
    _require_eligible_student(actor)

    with Session(engine) as session:
        rows = MessageRepository(session).list_all(listing_id, student_id=actor["id"])
        return {"ok": True, "messages": [row.model_dump() for row in rows]}


def list_listing_messages(actor: dict[str, Any], listing_id: int) -> dict[str, Any]:
    """Every thread on one of the landlord's own listings."""
    _require_role(actor, "landlords only", "landlord")

    with Session(engine) as session:
        _get_listing(ListingRepository(session), listing_id, actor)
        rows = MessageRepository(session).list_all(listing_id)
        return {"ok": True, "messages": [row.model_dump() for row in rows]}


def reply_to_student(
    actor: dict[str, Any],
    listing_id: int,
    student_id: int,
    body: str,
) -> dict[str, Any]:
    """Landlord reply in a thread the student started on their listing."""
    _require_role(actor, "landlords only", "landlord")

    if not body.strip():
        raise InvalidRequest("body required")

    with Session(engine) as session:
        _get_listing(ListingRepository(session), listing_id, actor)
        repo = MessageRepository(session)

        if not repo.list_all(listing_id, student_id):
            raise NotFound("no messages from this student on this listing")

        message = repo.create(
            Message(
                listing_id=listing_id,
                student_id=student_id,
                sender_role="landlord",
                body=body,
                created_at=_now(),
            )
        )

        return {"ok": True, "message_id": message.id}


def report_listing(
    actor: dict[str, Any], listing_id: int, reason: str
) -> dict[str, Any]:
    """Flag a problem with a visible listing for admins to review."""
    _require_eligible_student(actor)

    if not reason.strip():
        raise InvalidRequest("reason required")

    with Session(engine) as session:
        _get_visible_listing(ListingRepository(session), listing_id)

        report = ReportRepository(session).create(
            Report(
                listing_id=listing_id,
                student_id=actor["id"],
                reason=reason,
                created_at=_now(),
            )
        )

        return {"ok": True, "report_id": report.id}


def list_reports(actor: dict[str, Any]) -> dict[str, Any]:
    _require_role(actor, "admin only", "admin")

    with Session(engine) as session:
        rows = ReportRepository(session).list_all()
        return {"ok": True, "reports": [row.model_dump() for row in rows]}
