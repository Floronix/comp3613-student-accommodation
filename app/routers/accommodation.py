"""Student-accommodation scenario JSON API (OpenAPI /docs).

Service errors are mapped to status codes in app.main:
InvalidRequest 400, NotPermitted 403, NotFound 404, InvalidTransition 409.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.services import housing_auth as auth
from app.services import listings

router = APIRouter(tags=["student-accommodation"])


class LoginBody(BaseModel):
    email: str
    password: str


class ListingBody(BaseModel):
    title: str
    area: str
    price: int
    amenities: str = ""
    contact_phone: str
    contact_email: str
    photos: str = ""
    bedrooms: int = 0
    bathrooms: int = 0
    has_kitchen: bool = False
    description: str = ""


class ListingEditBody(BaseModel):
    title: str | None = None
    area: str | None = None
    price: int | None = None
    amenities: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    photos: str | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    has_kitchen: bool | None = None
    description: str | None = None


class TransitionBody(BaseModel):
    action: str = Field(
        description="approve_provisionally | verify | reject | activate | deactivate | restore | resubmit"
    )
    reason: str | None = Field(
        default=None,
        description="Required for reject and approve_provisionally; optional deactivation reason",
    )
    feedback: str | None = Field(default=None, description="Alias for reason")


class MessageBody(BaseModel):
    listing_id: int
    body: str


Actor = dict[str, Any]


def current_actor(x_user_id: str | None = Header(default=None)) -> Actor:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    try:
        actor = auth.get_user(int(x_user_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="X-User-Id must be int") from exc
    if actor is None:
        raise HTTPException(status_code=401, detail="unknown user")
    return actor


@router.post("/auth/login")
def login(body: LoginBody) -> dict[str, Any]:
    user = auth.login(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"user": user}


@router.post("/landlord/listings")
def submit(body: ListingBody, actor: Actor = Depends(current_actor)) -> dict[str, Any]:
    return listings.submit_listing(actor, **body.model_dump())


@router.get("/landlord/listings")
def landlord_list(
    status: str | None = None, actor: Actor = Depends(current_actor)
) -> dict[str, Any]:
    """The caller's own listings, with status, feedback and deactivation details."""
    return listings.list_for_landlord(actor, status=status)


@router.post("/listings/{listing_id}/transition")
def transition(
    listing_id: int, body: TransitionBody, actor: Actor = Depends(current_actor)
) -> dict[str, Any]:
    return listings.transition(
        actor, listing_id, body.action, body.feedback, body.reason
    )


@router.patch("/landlord/listings/{listing_id}")
def edit_listing(
    listing_id: int, body: ListingEditBody, actor: Actor = Depends(current_actor)
) -> dict[str, Any]:
    return listings.edit_listing(
        actor, listing_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/landlord/listings/{listing_id}")
def remove_listing(
    listing_id: int, actor: Actor = Depends(current_actor)
) -> dict[str, Any]:
    return listings.remove_listing(actor, listing_id)


@router.get("/student/listings")
def browse(
    area: str | None = None,
    max_price: int | None = None,
    amenity: str | None = None,
    actor: Actor = Depends(current_actor),
) -> dict[str, Any]:
    return listings.browse_for_students(
        actor, area=area, max_price=max_price, amenity=amenity
    )


@router.get("/admin/listings")
def admin_list(
    status: str | None = None, actor: Actor = Depends(current_actor)
) -> dict[str, Any]:
    """Every listing, with status, feedback and deactivation details."""
    return listings.list_for_admin(actor, status=status)


@router.post("/student/messages")
def message(body: MessageBody, actor: Actor = Depends(current_actor)) -> dict[str, Any]:
    return listings.send_message(actor, body.listing_id, body.body)
