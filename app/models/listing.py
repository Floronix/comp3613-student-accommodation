from typing import Optional

from sqlmodel import Field, SQLModel

from app.exceptions import InvalidTransition
from app.states import (
    PendingState,
    ProvisionalState,
    VerifiedState,
    ActiveState,
    InactiveState,
    RejectedState,
)


class Listing(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    landlord_id: int = Field(index=True)
    title: str
    area: str
    price: int
    amenities: str = ""
    contact_phone: str
    contact_email: str
    photos: str = ""

    status: str

    deactivated_by: Optional[str] = None
    feedback: Optional[str] = None
    created_at: str

    def get_state(self):
        """Return the state object matching the listing's current status."""

        states = {
            "pending": PendingState,
            "provisional": ProvisionalState,
            "verified": VerifiedState,
            "active": ActiveState,
            "inactive": InactiveState,
            "rejected": RejectedState,
        }

        state_class = states.get(self.status)

        if state_class is None:
            raise InvalidTransition(
                f"Unknown listing status: {self.status}"
            )

        return state_class(self)

    def transition(
        self,
        action: str,
        actor_role: str,
        feedback: str | None = None,
    ):
        """Delegate the requested transition to the current state."""

        current_state = self.get_state()
        current_state.transition(action, actor_role, feedback)
