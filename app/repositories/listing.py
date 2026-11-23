import logging

from sqlmodel import Session, select

from app.models.listing import Listing

logger = logging.getLogger(__name__)


class ListingRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, listing: Listing) -> Listing:
        """Insert a new listing or persist changes to an existing one."""
        try:
            self.db.add(listing)
            self.db.commit()
            self.db.refresh(listing)
            return listing
        except Exception as e:
            logger.error(f"An error occurred while saving listing: {e}")
            self.db.rollback()
            raise

    def get_by_id(self, listing_id: int) -> Listing | None:
        return self.db.get(Listing, listing_id)

    def list_all(self, status: str | None = None) -> list[Listing]:
        stmt = select(Listing).order_by(Listing.id)

        if status:
            stmt = stmt.where(Listing.status == status)

        return list(self.db.exec(stmt).all())

    def delete(self, listing: Listing) -> None:
        """Permanently delete a listing and commit the transaction."""
        try:
            self.db.delete(listing)
            self.db.commit()
        except Exception as e:
            logger.error(f"An error occurred while deleting listing: {e}")
            self.db.rollback()
            raise
