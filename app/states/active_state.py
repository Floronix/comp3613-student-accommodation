from app.states.listing_state import ListingState
from app.exceptions import InvalidTransition


class ActiveState(ListingState):

    def transition(self, action, actor_role, feedback=None):
        if action == "deactivate":
            self.require_role(actor_role, {"landlord", "admin"})
            self.listing.status = "inactive"
            self.listing.deactivated_by = actor_role
            return

        raise InvalidTransition(
            f"Cannot perform '{action}' while listing is active"
        )
