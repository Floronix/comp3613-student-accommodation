from app.states.listing_state import ListingState
from app.exceptions import InvalidTransition


class InactiveState(ListingState):

    def transition(self, action, actor_role, feedback=None, reason=None):

        if action == "activate":
            self.require_role(actor_role, {"landlord"})

            if self.listing.deactivated_by != "landlord":
                raise InvalidTransition(
                    "Only landlord-deactivated listings can be reactivated by landlords"
                )

            self.listing.status = "active"
            self.listing.deactivated_by = None
            self.listing.deactivation_reason = None
            return

        if action == "restore":
            self.require_role(actor_role, {"admin"})

            if self.listing.deactivated_by != "admin":
                raise InvalidTransition(
                    "Only admin-deactivated listings can be restored"
                )

            self.listing.status = "active"
            self.listing.deactivated_by = None
            self.listing.deactivation_reason = None
            self.listing.feedback = None
            return

        if action == "significant_edit":
            self.require_role(actor_role, {"landlord"})
            self.listing.status = "pending"
            self.listing.feedback = None
            self.listing.deactivated_by = None
            self.listing.deactivation_reason = None
            return

        raise InvalidTransition(
            f"Cannot perform '{action}' while listing is inactive"
        )
