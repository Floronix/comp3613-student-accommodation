from app.states.listing_state import ListingState
from app.exceptions import InvalidTransition


class InactiveState(ListingState):

    def transition(self, action, actor_role, feedback=None):
        if action == "activate":
            self.require_role(actor_role, {"landlord", "admin"})
            self.listing.status = "active"
            self.listing.deactivated_by = None
            return

        raise InvalidTransition(
            f"Cannot perform '{action}' while listing is inactive"
        )
