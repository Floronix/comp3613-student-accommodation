import logging

from sqlmodel import Session, select

from app.models.message import Message

logger = logging.getLogger(__name__)


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, message: Message) -> Message:
        try:
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            return message
        except Exception as e:
            logger.error(f"An error occurred while saving message: {e}")
            self.db.rollback()
            raise

    def delete_for_listing(self, listing_id: int) -> None:
        """Delete all messages associated with a listing."""

        messages = self.db.exec(
            select(Message).where(Message.listing_id == listing_id)
        ).all()

        for message in messages:
            self.db.delete(message)
