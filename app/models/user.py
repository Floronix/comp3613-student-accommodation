from collections.abc import Mapping
from typing import Any, Optional

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: EmailStr = Field(index=True, unique=True)
    password: str
    role: str = ""
    display_name: Optional[str] = None
    student_id: Optional[str] = None
    provisional: int = 0


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    @staticmethod
    def is_eligible_student(user: "User | Mapping[str, Any]") -> bool:
        """Check the current eligibility gate for a model or public-user dict."""
        if isinstance(user, Mapping):
            role = user.get("role")
            student_id = user.get("student_id")
            provisional = user.get("provisional")
        else:
            role = user.role
            student_id = user.student_id
            provisional = user.provisional

        has_student_id = bool(str(student_id or "").strip())
        return role == "student" and (has_student_id or bool(provisional))
