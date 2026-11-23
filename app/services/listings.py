"""Listing CRUD, browse filters, messaging, and lifecycle transitions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from app.database import engine
from app.exceptions import InvalidTransition
from app.models.listing import Listing
from app.models.message import Message
from app.repositories import ListingRepository, MessageRepository
from app.services.housing_auth import get_user
from app.services.lifecycle import ACTIONS, visible_to_students

ALLOWED_AREAS = {"st_augustine", "mount_hope"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_amenities(raw: str) -> list[str]:
    return [a.strip().lower() for a in (raw or "").split(",") if a.strip()]


def submit_listing(
    landlord_id: int,
    *,
    title: str,
    area: str,
    price: int,
    amenities: str,
    contact_phone: str,
    contact_email: str,
    photos: str = "",
) -> dict[str, Any]:
    user = get_user(landlord_id)

    if not user or user["role"] != "landlord":
        return {"ok": False, "error": "landlords only"}

    if area not in ALLOWED_AREAS:
        return {"ok": False, "error": "invalid accommodation area"}

    if price <= 0:
        return {"ok": False, "error": "price must be positive"}

    if not amenities.strip():
        return {"ok": False, "error": "amenities are required"}

    with Session(engine) as session:
        listing = ListingRepository(session).save(
            Listing(
                landlord_id=landlord_id,
                title=title,
                area=area,
                price=price,
                amenities=amenities,
                contact_phone=contact_phone,
                contact_email=contact_email,
                photos=photos,
                status="pending",
                created_at=_now(),
            )
        )

        return {"ok": True, "listing": listing.model_dump()}


def transition(
    actor_id: int,
    listing_id: int,
    action: str,
    feedback: str | None = None,
) -> dict[str, Any]:
    actor = get_user(actor_id)

    if not actor:
        return {"ok": False, "error": "unknown user"}

    if action not in ACTIONS:
        return {"ok": False, "error": f"action must be one of {ACTIONS}"}

    with Session(engine) as session:
        repo = ListingRepository(session)
        listing = repo.get_by_id(listing_id)

        if listing is None:
            return {"ok": False, "error": "listing not found"}

        # Landlords can only manage their own listings.
        if actor["role"] == "landlord":
            if listing.landlord_id != actor_id:
                return {"ok": False, "error": "you can only manage your own listings"}

        elif actor["role"] != "admin":
            return {"ok": False, "error": "admin/landlord only"}

        try:
            # Delegate the transition to the listing's current State object.
            listing.transition(
                action=action,
                actor_role=actor["role"],
                feedback=feedback,
            )
        except InvalidTransition as error:
            return {"ok": False, "error": str(error)}

        listing = repo.save(listing)

        return {"ok": True, "listing": listing.model_dump()}


def browse_for_students(
    student_id: int,
    *,
    area: str | None = None,
    max_price: int | None = None,
    amenity: str | None = None,
) -> dict[str, Any]:
    student = get_user(student_id)

    if not student or student["role"] != "student":
        return {"ok": False, "error": "students only"}

    with Session(engine) as session:
        items = [
            row.model_dump()
            for row in ListingRepository(session).list_all()
        ]

    results = []

    for item in items:
        if not visible_to_students(item):
            continue

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


def list_all(*, status: str | None = None) -> list[dict[str, Any]]:
    with Session(engine) as session:
        return [
            row.model_dump()
            for row in ListingRepository(session).list_all(status)
        ]


def send_message(
    student_id: int,
    listing_id: int,
    body: str,
) -> dict[str, Any]:
    student = get_user(student_id)

    if not student or student["role"] != "student":
        return {"ok": False, "error": "students only"}

    if not body.strip():
        return {"ok": False, "error": "body required"}

    with Session(engine) as session:
        listing = ListingRepository(session).get_by_id(listing_id)

        if listing is None:
            return {"ok": False, "error": "listing not found"}

        if listing.status != "active":
            return {"ok": False, "error": "messages are only allowed for active listings"}

        message = MessageRepository(session).create(
            Message(
                listing_id=listing_id,
                student_id=student_id,
                body=body,
                created_at=_now(),
            )
        )

        return {"ok": True, "message_id": message.id}
