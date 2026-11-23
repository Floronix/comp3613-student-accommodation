from app.states.listing_state import ListingState
from app.exceptions import InvalidTransition


class VerifiedState(ListingState):

    def transition(self, action, actor_role, feedback=None):
        if action == "activate":
            self.require_role(actor_role, {"landlord", "admin"})
            self.listing.status = "active"
            self.listing.feedback = None
            return

        if action == "reject":
            self.require_role(actor_role, {"admin"})
            self.listing.status = "rejected"
            self.listing.feedback = feedback
            return

        raise InvalidTransition(
            f"Cannot perform '{action}' while listing is verified"
        )
