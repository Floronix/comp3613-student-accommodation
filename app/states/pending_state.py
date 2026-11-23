from app.states.listing_state import ListingState
from app.exceptions import InvalidTransition


class PendingState(ListingState):

    def transition(self, action, actor_role, feedback=None):
        if action == "approve_provisionally":
            self.require_role(actor_role, {"admin"})
            self.listing.status = "provisional"
            self.listing.feedback = feedback
            return

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

        raise InvalidTransition(
            f"Cannot perform '{action}' while listing is pending"
        )
