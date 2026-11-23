"""Student-accommodation scenario JSON API (OpenAPI /docs)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
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
    feedback: str | None = None
    reason: str | None = None


class MessageBody(BaseModel):
    listing_id: int
    body: str


def _actor_id(x_user_id: str | None) -> int:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    try:
        return int(x_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="X-User-Id must be int") from exc



def _raise_listing_error(error: str) -> None:
    if error in {"listing not found", "unknown user"}:
        raise HTTPException(status_code=404, detail=error)

    if (
        error in {
            "landlords only",
            "students only",
            "admin/landlord only",
        }
        or error.startswith("you can only manage your own listings")
        or error.startswith("This action is not permitted")
    ):
        raise HTTPException(status_code=403, detail=error)

    if (
        error.startswith("Cannot perform")
        or error == "messages are only allowed for active listings"
    ):
        raise HTTPException(status_code=409, detail=error)

    raise HTTPException(status_code=400, detail=error)


@router.post("/auth/login")
def login(body: LoginBody) -> dict[str, Any]:
    user = auth.login(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"user": user}


@router.post("/landlord/listings")
def submit(
    body: ListingBody,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    result = listings.submit_listing(
        _actor_id(x_user_id),
        title=body.title,
        area=body.area,
        price=body.price,
        amenities=body.amenities,
        contact_phone=body.contact_phone,
        contact_email=body.contact_email,
        photos=body.photos,
        bedrooms=body.bedrooms,
        bathrooms=body.bathrooms,
        has_kitchen=body.has_kitchen,
        description=body.description,
    )

    if not result.get("ok"):
        _raise_listing_error(result.get("error", "Request failed"))

    return result


@router.post("/listings/{listing_id}/transition")
def transition(
    listing_id: int,
    body: TransitionBody,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    result = listings.transition(
        _actor_id(x_user_id),
        listing_id,
        body.action,
        body.feedback,
        body.reason,
    )
    if not result.get("ok"):
        _raise_listing_error(result.get("error", "Request failed"))
    return result

@router.patch("/landlord/listings/{listing_id}")
def edit_listing(
    listing_id: int,
    body: ListingEditBody,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    result = listings.edit_listing(
        _actor_id(x_user_id),
        listing_id,
        body.model_dump(exclude_unset=True),
    )

    if not result.get("ok"):
        _raise_listing_error(result.get("error", "Request failed"))

    return result

@router.delete("/landlord/listings/{listing_id}")
def remove_listing(
    listing_id: int,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    result = listings.remove_listing(
        _actor_id(x_user_id),
        listing_id,
    )

    if not result.get("ok"):
        _raise_listing_error(result.get("error", "Request failed"))

    return result

@router.get("/student/listings")
def browse(
    area: str | None = None,
    max_price: int | None = None,
    amenity: str | None = None,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    result = listings.browse_for_students(
        _actor_id(x_user_id), area=area, max_price=max_price, amenity=amenity
    )
    if not result.get("ok"):
        raise HTTPException(status_code=403, detail=result.get("error"))
    return result


@router.get("/admin/listings")
def admin_list(
    status: str | None = None, x_user_id: str | None = Header(default=None)
) -> dict[str, Any]:
    actor = auth.get_user(_actor_id(x_user_id))
    if not actor or actor["role"] != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    return {"listings": listings.list_all(status=status)}


@router.post("/student/messages")
def message(
    body: MessageBody, x_user_id: str | None = Header(default=None)
) -> dict[str, Any]:
    result = listings.send_message(
        _actor_id(x_user_id), body.listing_id, body.body
    )
    if not result.get("ok"):
        _raise_listing_error(result.get("error", "Request failed"))

    return result
