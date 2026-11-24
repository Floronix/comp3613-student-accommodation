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

    def list_all(
        self, listing_id: int | None = None, student_id: int | None = None
    ) -> list[Message]:
        stmt = select(Message).order_by(Message.id)

        if listing_id is not None:
            stmt = stmt.where(Message.listing_id == listing_id)

        if student_id is not None:
            stmt = stmt.where(Message.student_id == student_id)

        return list(self.db.exec(stmt).all())

    def delete_for_listing(self, listing_id: int) -> None:
        """Delete all messages associated with a listing."""

        messages = self.db.exec(
            select(Message).where(Message.listing_id == listing_id)
        ).all()

        for message in messages:
            self.db.delete(message)
