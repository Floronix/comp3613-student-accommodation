from typing import Optional

from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    """One message in the thread between a listing's landlord and one student."""

    id: Optional[int] = Field(default=None, primary_key=True)
    listing_id: int = Field(index=True)
    student_id: int = Field(index=True)
    sender_role: str = "student"  # "student" or "landlord"
    body: str
    created_at: str
