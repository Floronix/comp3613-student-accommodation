def test_all_states_seeded(listing):
    statuses = {row["status"] for row in listing.values()}

    assert statuses == {
        "pending",
        "provisional",
        "verified",
        "active",
        "inactive",
        "rejected",
    }


def test_role_fixtures_work(client, admin, student, incoming, landlord, landlord2):
    assert client.get(
        "/api/admin/listings",
        headers=admin,
    ).status_code == 200

    assert client.get(
        "/api/admin/listings",
        headers=student,
    ).status_code == 403

    assert client.get(
        "/api/admin/listings",
        headers=incoming,
    ).status_code == 403

    assert client.get(
        "/api/admin/listings",
        headers=landlord,
    ).status_code == 403

    assert client.get(
        "/api/admin/listings",
        headers=landlord2,
    ).status_code == 403