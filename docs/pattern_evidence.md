# Pattern Evidence: State Pattern (Listing Lifecycle)

## Note

A listing moves through six statuses: pending, provisional, verified, active, inactive and rejected. Each status is its own class, so the allowed actions, the roles that can perform them and the resulting status change all sit with the state that owns them. This replaces a single status-checking `if/else` chain.

- **Context:** `Listing` keeps only the `status` string. `get_state()` builds the matching state object, and `transition()` hands the request to it.
- **State:** `ListingState` is an abstract base class with an abstract `transition(action, actor_role, feedback, reason)`. It also has a shared `require_role()` helper that raises `NotPermitted`.
- **Concrete states:** each of the six classes handles only its own valid actions and sets the next `status`.
- **Service layer:** `services/listings.py` calls `listing.transition(...)` and saves the result. The per-action rules (who may act, what the next status is) live in the states, not the service.

### Where errors come from

| Situation | Exception | HTTP | Raised by |
|---|---|---|---|
| Unknown action name (not in `ACTIONS`, including `submit` and `significant_edit` sent by a client) | `InvalidRequest` | 400 | `transition()` in `services/listings.py` |
| Missing reason or feedback for `reject` / `approve_provisionally` | `InvalidRequest` | 400 | The state class |
| Actor's role is not allowed to perform the action | `NotPermitted` | 403 | `require_role()` in `ListingState` (and `_require_role` / `_get_listing` in the service) |
| Known action, but not allowed from the listing's current state (or a condition is not met) | `InvalidTransition` | 409 | The state class |

`InvalidTransition` is therefore only for a valid action attempted in the wrong state. It is not used for unknown actions or role failures.

### Limits of the pattern in this code

The State pattern covers the transitions, but not all status-dependent logic:

- **`edit_listing`** in `services/listings.py` still branches on `listing.status`. It sets `edited_after_rejection` when the status is `"rejected"`, and only triggers `significant_edit` when the status is `"verified"`, `"active"` or `"inactive"`.
- **`send_message`** checks `listing.status != "active"` directly.
- **`app/services/lifecycle.py`** holds the `ACTIONS` tuple that decides which action names are valid, and `visible_to_students()`, which checks `status == "active"`. The set of actions is therefore defined in two places: `ACTIONS` and the state classes.

Adding a new action touches its state class and `ACTIONS`. Adding a new state touches its state class and the status-to-class map in `get_state()`, plus any of the status checks above that need to know about it.

## Key Files

| File | What it shows |
|---|---|
| `app/models/listing.py` | The Context: `get_state()` maps status to state class, and `transition()` delegates to it |
| `app/states/listing_state.py` | The abstract State: `transition()` and `require_role()` |
| `app/states/pending_state.py`, `provisional_state.py`, `verified_state.py`, `active_state.py`, `inactive_state.py`, `rejected_state.py` | The six concrete states, each with its own rules and transitions |
| `app/exceptions/` | `InvalidTransition`, `NotPermitted` and `InvalidRequest` raised by the states and the service |
| `app/services/listings.py` (`transition`, `edit_listing`) | Clients call the Context only, and `edit_listing` triggers `significant_edit` |
| `app/services/lifecycle.py` | `ACTIONS` (valid action names) and `visible_to_students()`, which sit outside the state classes |
| `docs/transitions.md` | The transition table the states implement |
| `tests/test_lifecycle.py` | Tests of the transitions, including role checks |
