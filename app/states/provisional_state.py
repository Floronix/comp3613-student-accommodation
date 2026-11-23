from app.states.listing_state import ListingState
from app.exceptions import InvalidTransition


class ProvisionalState(ListingState):

    def transition(self, action, actor_role, feedback=None):
        if action == "verify":
            self.require_role(actor_role, {"admin"})
            self.listing.status = "verified"
            self.listing.feedback = None
            return

        if action == "reject":
            self.require_role(actor_role, {"admin"})
            self.listing.status = "rejected"
            self.listing.feedback = feedback
            return

        if action == "resubmit":
            self.require_role(actor_role, {"landlord", "admin"})
            self.listing.status = "pending"
            self.listing.feedback = None
            return

        raise InvalidTransition(
            f"Cannot perform '{action}' while listing is provisional"
        )
