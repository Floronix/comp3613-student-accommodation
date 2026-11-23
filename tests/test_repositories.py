from app.models.listing import Listing
from app.models.message import Message
from app.repositories import ListingRepository, MessageRepository


def make_listing(status="pending", **kw):
    return Listing(
        landlord_id=1,
        title=kw.pop("title", "Flat"),
        area="st_augustine",
        price=3000,
        amenities="wifi",
        contact_phone="555-0100",
        contact_email="landlord@example.com",
        status=status,
        created_at="2099-01-01T10:00:00+00:00",
        **kw,
    )


def test_listing_save_get_and_new_fields(test_session):
    repo = ListingRepository(test_session)
    listing = repo.save(make_listing())

    assert listing.id is not None
    assert listing.deactivated_by is None
    assert listing.feedback is None

    listing.status = "inactive"
    listing.deactivated_by = "admin"
    listing.feedback = "Fire exit blocked"
    repo.save(listing)
    test_session.expire_all()

    saved = repo.get_by_id(listing.id)
    assert saved.status == "inactive"
    assert saved.deactivated_by == "admin"
    assert saved.feedback == "Fire exit blocked"
    assert repo.get_by_id(9999) is None


def test_listing_list_all_orders_by_id_and_filters_status(test_session):
    repo = ListingRepository(test_session)
    a = repo.save(make_listing("pending", title="A"))
    b = repo.save(make_listing("active", title="B"))
    c = repo.save(make_listing("pending", title="C"))

    assert [x.id for x in repo.list_all()] == [a.id, b.id, c.id]
    assert [x.id for x in repo.list_all("pending")] == [a.id, c.id]
    assert repo.list_all("rejected") == []


def test_message_create(test_session):
    listing = ListingRepository(test_session).save(make_listing("active"))
    msg = MessageRepository(test_session).create(
        Message(
            listing_id=listing.id,
            student_id=2,
            body="Is it available?",
            created_at="2099-01-01T10:00:00+00:00",
        )
    )

    assert msg.id is not None
    assert test_session.get(Message, msg.id).body == "Is it available?"

def test_listing_delete_removes_associated_messages(test_session):
    listing_repo = ListingRepository(test_session)
    message_repo = MessageRepository(test_session)

    listing = listing_repo.save(make_listing("active"))

    message = message_repo.create(
        Message(
            listing_id=listing.id,
            student_id=2,
            body="Is this apartment available?",
            created_at="2099-01-01T10:00:00+00:00",
        )
    )

    message_repo.delete_for_listing(listing.id)
    listing_repo.delete(listing)

    test_session.expire_all()

    assert listing_repo.get_by_id(listing.id) is None
    assert test_session.get(Message, message.id) is None