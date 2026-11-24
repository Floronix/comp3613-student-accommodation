from typing import Optional

from sqlmodel import Field, SQLModel


class Report(SQLModel, table=True):
    """A student's report of a problem with a listing, for admins to review."""

    id: Optional[int] = Field(default=None, primary_key=True)
    listing_id: int = Field(index=True)
    student_id: int = Field(index=True)
    reason: str
    created_at: str
