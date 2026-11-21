# Listing Lifecycle / Transitions Table

## States
| State | Meaning | Visible to students? |
|---|---|---|
| pending | Submitted, awaiting admin review | No |
| provisional | Temporarily accepted, landlord must address admin feedback | No |
| verified | Approved by admin, not live | No |
| active | Approved and live | Yes (the only visible state) |
| inactive | Rented, withdrawn, or admin-deactivated | No |
| rejected | Failed review, needs revision | No |

## Transitions
Anything not listed is not allowed and raises InvalidTransition.

| From | Action | Actor | To | Conditions |
|---|---|---|---|---|
| (new) | submit | landlord | pending | automatic on creation |
| pending | verify | admin | verified | |
| pending | approve_provisionally | admin | provisional | feedback given to landlord |
| pending | reject | admin | rejected | reason required |
| provisional | verify | admin | verified | landlord's changes checked |
| provisional | reject | admin | rejected | reason required |
| verified | activate | landlord | active | |
| verified | deactivate | landlord or admin | inactive | record deactivated_by |
| verified | significant_edit | landlord | pending | |
| active | deactivate | landlord or admin | inactive | record deactivated_by |
| active | significant_edit | landlord | pending | hidden from students during re-review |
| inactive | activate | landlord | active | only if deactivated_by is landlord and no significant changes |
| inactive | restore | admin | active | only after admin confirms the issue is resolved |
| inactive | significant_edit | landlord | pending | changed details need admin approval |
| rejected | resubmit | landlord | pending | listing has been edited after rejection |

## Rules
- Only active listings are visible to eligible students, including by direct links.
- Landlords may only act on their own listings.
- Only admins can verify, reject, approve provisionally, or restore.
- A rejected listing cannot go to pending or provisional without a landlord resubmission.
- A listing returns to pending only through significant_edit (verified, active or inactive) or resubmit (if rejected).
- Minor edits (e.g. photos) don't change state. Significant edits include bedrooms/bathrooms, adding or removing a kitchen or core feature, and description changes that affect what the property offers or how it is classified.
- Removing a listing has no transitions, just delete.
- The starter lets admins perform landlord actions (activate, deactivate, resubmit). In this design, only landlords activate and resubmit. Admins can deactivate and restore.
- Requesting revisions (admin, pending) and landlord edits to a provisional listing don't change the state. The admin then verifies or rejects.
- Correcting a decision only uses transitions in the table. There is no direct admin override (e.g. rejected cannot go to verified without a landlord resubmit).
- A landlord may remove their own listing in any state.
- An action that isn't in the table returns 409 (InvalidTransition). An actor who isn't permitted returns 403. An unknown listing returns 404. A missing reason for reject or approve_provisionally returns 400.

## Notes
- "Approved" in the requirements and interviews = verified (approved, not live) and active (approved and visible).
- New in this design (not in the starter): state `provisional`; actions `approve_provisionally`, `significant_edit`, `restore`.
- Status strings and the existing actions match the starter (`app/services/lifecycle.py`).
- The submit action is triggered automatically when a listing is created. It cannot be called through the transition endpoint. Currently anyone can call it, which resets any listing to pending.
- The significant_edit action is triggered by the future edit endpoint when a significant field changes. Clients don't call it directly.
- The reason field is optional in the request schema, but the service requires it for reject and approve_provisionally and returns 400 if it's missing.
- New actions to add to `ACTIONS`: `approve_provisionally`, `significant_edit`, `restore`. New columns on `Listing`: `deactivated_by` and `feedback` (the admin's reason or feedback).
- Restore always returns the listing to active.