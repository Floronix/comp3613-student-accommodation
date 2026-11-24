import logging

from sqlmodel import Session, select

from app.models.report import Report

logger = logging.getLogger(__name__)


class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, report: Report) -> Report:
        try:
            self.db.add(report)
            self.db.commit()
            self.db.refresh(report)
            return report
        except Exception as e:
            logger.error(f"An error occurred while saving report: {e}")
            self.db.rollback()
            raise

    def list_all(self) -> list[Report]:
        return list(self.db.exec(select(Report).order_by(Report.id)).all())

    def delete_for_listing(self, listing_id: int) -> None:
        """Delete all reports for a listing; the caller commits."""
        for report in self.db.exec(select(Report).where(Report.listing_id == listing_id)):
            self.db.delete(report)
