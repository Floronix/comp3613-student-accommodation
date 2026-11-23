from app.states.listing_state import ListingState
from app.exceptions import InvalidTransition


class RejectedState(ListingState):

    def transition(self, action, actor_role, feedback=None, reason=None):

        if action == "resubmit":
            self.require_role(actor_role, {"landlord"})

            if not self.listing.edited_after_rejection:
                raise InvalidTransition(
                    "A rejected listing must be edited before it can be resubmitted"
                )

            self.listing.status = "pending"
            self.listing.feedback = None
            self.listing.deactivated_by = None
            self.listing.deactivation_reason = None
            self.listing.edited_after_rejection = False
            return

        raise InvalidTransition(
            f"Cannot perform '{action}' while listing is rejected"
        )
    