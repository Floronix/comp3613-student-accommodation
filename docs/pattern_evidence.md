# Pattern Evidence: State Pattern (Listing Lifecycle)

## Note

A listing moves through six statuses: pending, provisional, verified, active, inactive and rejected. Each status is its own class, so the allowed actions, the roles that can perform them and the resulting status change all sit with the state that owns them. This replaces a single status-checking `if/else` chain.

- **Context:** `Listing` keeps only the `status` string. `get_state()` builds the matching state object, and `transition()` hands the request to it.
- **State:** `ListingState` is an abstract base class with an abstract `transition(action, actor_role, feedback, reason)`. It also has a shared `require_role()` helper that raises `NotPermitted`.
- **Concrete states:** each of the six classes handles only its own valid actions and sets the next `status`. Anything else raises `InvalidTransition`, which the API returns as a 409.
- **Service layer:** `services/listings.py` calls `listing.transition(...)` and saves the result. It contains no per-status logic.

Adding a new state or action only touches one state class and the status-to-class map in `get_state()`. For example, `provisional` and `restore` were added without changing the service.

## Key Files

| File | What it shows |
|---|---|
| `app/models/listing.py` | The Context: `get_state()` maps status to state class, and `transition()` delegates to it |
| `app/states/listing_state.py` | The abstract State: `transition()` and `require_role()` |
| `app/states/pending_state.py`, `provisional_state.py`, `verified_state.py`, `active_state.py`, `inactive_state.py`, `rejected_state.py` | The six concrete states, each with its own rules and transitions |
| `app/exceptions/` | `InvalidTransition`, `NotPermitted` and `InvalidRequest` raised by the states |
| `app/services/listings.py` (`transition`, `edit_listing`) | Clients call the Context only, and `edit_listing` triggers `significant_edit` |
| `docs/transitions.md` | The transition table the states implement |
| `tests/test_lifecycle.py` | Tests of the transitions, including role checks |
