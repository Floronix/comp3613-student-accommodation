from app.states.listing_state import ListingState
from app.exceptions import InvalidRequest, InvalidTransition


class PendingState(ListingState):

    def transition(self, action, actor_role, feedback=None, reason=None):

        if action == "approve_provisionally":
            self.require_role(actor_role, {"admin"})

            if not feedback or not feedback.strip():
                raise InvalidRequest(
                    "Feedback is required for provisional approval"
                )

            self.listing.status = "provisional"
            self.listing.feedback = feedback.strip()
            return

        if action == "verify":
            self.require_role(actor_role, {"admin"})
            self.listing.status = "verified"
            self.listing.feedback = None
            return

        if action == "reject":
            self.require_role(actor_role, {"admin"})

            if not feedback or not feedback.strip():
                raise InvalidRequest(
                    "A rejection reason is required"
                )

            self.listing.status = "rejected"
            self.listing.feedback = feedback.strip()
            self.listing.edited_after_rejection = False
            return

        raise InvalidTransition(
            f"Cannot perform '{action}' while listing is pending"
        )
