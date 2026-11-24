"""Task #14: API status codes (400/401/403/404/409) and landlord/admin views."""

import pytest

MISSING = 999999


def _id(listing, title):
    return MISSING if title is None else listing[title]["id"]


@pytest.mark.parametrize(
    "who, title, body, code",
    [
        # 403: actor not permitted
        ("student", "Pending Unit", {"action": "verify"}, 403),
        ("landlord", "Pending Unit", {"action": "verify"}, 403),
        ("landlord", "Inactive Unit", {"action": "restore"}, 403),
        ("admin", "Verified Unit", {"action": "activate"}, 403),
        ("landlord2", "Verified Unit", {"action": "activate"}, 403),
        # 409: action not allowed from the current state
        ("admin", "Verified Active Flat", {"action": "verify"}, 409),
        ("landlord", "Rejected Unit", {"action": "activate"}, 409),
        ("landlord", "Pending Unit", {"action": "activate"}, 409),
        ("admin", "Rejected Unit", {"action": "verify"}, 409),
        # 400: missing reason, or an action clients can't call
        ("admin", "Pending Unit", {"action": "reject"}, 400),
        ("admin", "Provisional Unit", {"action": "reject", "reason": "  "}, 400),
        ("admin", "Pending Unit", {"action": "approve_provisionally"}, 400),
        ("landlord", "Verified Unit", {"action": "significant_edit"}, 400),
        ("landlord", "Verified Active Flat", {"action": "submit"}, 400),
        ("admin", "Pending Unit", {"action": "bogus"}, 400),
        # 404: unknown listing
        ("admin", None, {"action": "verify"}, 404),
    ],
)
def test_transition_error_codes(client, request, listing, who, title, body, code):
    r = client.post(
        f"/api/listings/{_id(listing, title)}/transition",
        headers=request.getfixturevalue(who),
        json=body,
    )

    assert r.status_code == code
    assert r.json()["detail"]

    if title is not None:
        after = client.get("/api/admin/listings", headers=request.getfixturevalue("admin"))
        status = {row["id"]: row["status"] for row in after.json()["listings"]}
        assert status[listing[title]["id"]] == listing[title]["status"]


@pytest.mark.parametrize("headers", [{}, {"X-User-Id": str(MISSING)}])
def test_missing_or_unknown_user_is_401_json(client, listing, headers):
    r = client.post(
        f"/api/listings/{listing['Pending Unit']['id']}/transition",
        headers=headers,
        json={"action": "verify"},
    )

    assert r.status_code == 401
    assert r.headers["content-type"] == "application/json"


@pytest.mark.parametrize(
    "method, path, who, title, body, code",
    [
        ("patch", "/api/landlord/listings/{id}", "landlord2", "Verified Unit", {"price": 1}, 403),
        ("patch", "/api/landlord/listings/{id}", "admin", "Verified Unit", {"price": 1}, 403),
        ("patch", "/api/landlord/listings/{id}", "landlord", None, {"price": 1}, 404),
        ("patch", "/api/landlord/listings/{id}", "landlord", "Verified Unit", {}, 400),
        ("delete", "/api/landlord/listings/{id}", "landlord2", "Verified Unit", None, 403),
        ("delete", "/api/landlord/listings/{id}", "landlord", None, None, 404),
        ("post", "/api/student/messages", "student", "Pending Unit", "hi", 404),
        ("post", "/api/student/messages", "student", None, "hi", 404),
        ("post", "/api/student/messages", "landlord", "Verified Active Flat", "hi", 403),
        ("post", "/api/landlord/listings", "student", None, None, 403),
        ("get", "/api/landlord/listings", "admin", None, None, 403),
        ("get", "/api/landlord/listings", "student", None, None, 403),
        ("get", "/api/admin/listings", "landlord", None, None, 403),
        ("get", "/api/student/listings/{id}", "landlord", "Verified Active Flat", None, 403),
        ("get", "/api/student/listings/{id}", "admin", "Verified Active Flat", None, 403),
    ],
)
def test_other_endpoint_error_codes(client, request, listing, method, path, who, title, body, code):
    listing_id = _id(listing, title)
    kwargs = {"headers": request.getfixturevalue(who)}

    if path == "/api/student/messages":
        kwargs["json"] = {"listing_id": listing_id, "body": body}
    elif path == "/api/landlord/listings" and method == "post":
        kwargs["json"] = {
            "title": "x", "area": "st_augustine", "price": 1, "amenities": "wifi",
            "contact_phone": "1", "contact_email": "x@example.com",
        }
    elif body is not None:
        kwargs["json"] = body

    r = client.request(method, path.format(id=listing_id), **kwargs)

    assert r.status_code == code


def test_reject_reason_shows_in_landlord_and_admin_views(
    client, admin, landlord, landlord2, listing
):
    pending_id = listing["Pending Unit"]["id"]

    r = client.post(
        f"/api/listings/{pending_id}/transition",
        headers=admin,
        json={"action": "reject", "reason": "Photos missing"},
    )
    assert r.status_code == 200

    own = client.get("/api/landlord/listings", headers=landlord).json()["listings"]
    by_id = {row["id"]: row for row in own}
    assert by_id[pending_id]["status"] == "rejected"
    assert by_id[pending_id]["feedback"] == "Photos missing"
    assert "Other Landlord Pending" not in {row["title"] for row in own}

    other = client.get("/api/landlord/listings", headers=landlord2).json()["listings"]
    assert [row["title"] for row in other] == ["Other Landlord Pending"]

    rejected = client.get(
        "/api/landlord/listings", params={"status": "rejected"}, headers=landlord
    ).json()["listings"]
    assert {row["title"] for row in rejected} == {"Pending Unit", "Rejected Unit"}

    admin_rows = client.get(
        "/api/admin/listings", params={"status": "rejected"}, headers=admin
    ).json()["listings"]
    assert {row["id"]: row["feedback"] for row in admin_rows}[pending_id] == "Photos missing"


def test_provisional_feedback_visible_to_landlord(client, admin, landlord, listing):
    pending_id = listing["Pending Unit"]["id"]

    client.post(
        f"/api/listings/{pending_id}/transition",
        headers=admin,
        json={"action": "approve_provisionally", "reason": "Add a kitchen photo"},
    )

    own = client.get(
        "/api/landlord/listings", params={"status": "provisional"}, headers=landlord
    ).json()["listings"]
    assert {row["id"]: row["feedback"] for row in own}[pending_id] == "Add a kitchen photo"


def test_admin_deactivation_is_recorded_in_views(client, admin, landlord, listing):
    active_id = listing["Verified Active Flat"]["id"]

    r = client.post(
        f"/api/listings/{active_id}/transition",
        headers=admin,
        json={"action": "deactivate", "reason": "Reported as unsafe"},
    )
    assert r.status_code == 200

    own = {row["id"]: row for row in client.get("/api/landlord/listings", headers=landlord).json()["listings"]}
    assert own[active_id]["status"] == "inactive"
    assert own[active_id]["deactivated_by"] == "admin"

    # Landlord can't reactivate an admin-deactivated listing.
    r = client.post(
        f"/api/listings/{active_id}/transition",
        headers=landlord,
        json={"action": "activate"},
    )
    assert r.status_code == 409


# --- Student direct links (D16 "view one listing") ---

STUDENT_LISTING = "/api/student/listings/{}"


@pytest.mark.parametrize(
    "title",
    [None, "Pending Unit", "Provisional Unit", "Verified Unit", "Inactive Unit", "Rejected Unit"],
)
def test_missing_and_hidden_listings_return_the_same_404(client, student, listing, title):
    r = client.get(STUDENT_LISTING.format(_id(listing, title)), headers=student)

    assert r.status_code == 404
    assert r.json() == {"detail": "listing not found"}


def test_student_can_open_active_listing_by_direct_link(client, student, listing):
    active = listing["Verified Active Flat"]

    r = client.get(STUDENT_LISTING.format(active["id"]), headers=student)

    assert r.status_code == 200
    assert r.json()["listing"]["id"] == active["id"]
    assert r.json()["listing"]["contact_phone"] == active["contact_phone"]


def test_direct_link_stops_working_once_listing_is_deactivated(
    client, student, landlord, listing
):
    active_id = listing["Verified Active Flat"]["id"]

    client.post(
        f"/api/listings/{active_id}/transition",
        headers=landlord,
        json={"action": "deactivate"},
    )

    assert client.get(STUDENT_LISTING.format(active_id), headers=student).status_code == 404
