from app.states.listing_state import ListingState
from app.exceptions import InvalidRequest, InvalidTransition


class VerifiedState(ListingState):

    def transition(self, action, actor_role, feedback=None, reason=None):

        if action == "activate":
            self.require_role(actor_role, {"landlord"})
            self.listing.status = "active"
            self.listing.feedback = None
            self.listing.deactivated_by = None
            self.listing.deactivation_reason = None
            return

        if action == "deactivate":
            self.require_role(actor_role, {"landlord", "admin"})

            if not reason or not reason.strip():
                raise InvalidRequest(
                    "A deactivation reason is required"
                )

            self.listing.status = "inactive"
            self.listing.deactivated_by = actor_role
            self.listing.deactivation_reason = reason.strip()
            return

        if action == "significant_edit":
            self.require_role(actor_role, {"landlord"})
            self.listing.status = "pending"
            self.listing.feedback = None
            self.listing.deactivated_by = None
            self.listing.deactivation_reason = None
            return

        raise InvalidTransition(
            f"Cannot perform '{action}' while listing is verified"
        )
