def test_all_states_seeded(listing):
    statuses = {row["status"] for row in listing.values()}
    assert statuses == {"pending", "provisional", "verified", "active", "inactive", "rejected"}


def test_role_fixtures_work(client, admin, student, incoming, landlord, landlord2):
    r = client.get("/api/admin/listings", headers=admin)
    assert r.status_code == 200
    assert client.get("/api/admin/listings", headers=student).status_code == 403