from abc import ABC, abstractmethod

from app.exceptions import InvalidTransition


class ListingState(ABC):
    """Base class for all listing lifecycle states."""

    def __init__(self, listing):
        self.listing = listing

    @abstractmethod
    def transition(self, action: str, actor_role: str, feedback: str | None = None):
        """Perform an action or raise InvalidTransition."""
        pass

    def require_role(self, actor_role: str, allowed_roles: set[str]):
        if actor_role not in allowed_roles:
            raise InvalidTransition(
                f"This action is not permitted for role: {actor_role}"
            )

    def invalid_action(self, action: str):
        raise InvalidTransition(
            f"Cannot perform '{action}' while listing is {self.listing.status}"
        )
