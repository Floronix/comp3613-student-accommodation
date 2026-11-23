# Defect Inventory

| ID | Area | Defect | Where | Fix in | Fixed? |
|---|---|---|---|---|---|
| D1 | Lifecycle | `verify` works on a rejected listing without resubmit | lifecycle.py | #10 | ❌ |
| D2 | Lifecycle | `activate` works from pending (skips verification) and from rejected | lifecycle.py | #10 | ❌ |
| D3 | Lifecycle | `deactivate` flips any state to inactive | lifecycle.py | #10 | ❌ |
| D4 | Lifecycle | `reject` and `resubmit` leave stale flags set; status and flags drift apart | lifecycle.py | #10 | ❌ |
| D5 | Lifecycle | `submit` can be called through the transition endpoint and resets any listing to pending | lifecycle.py, listings.py | #10, #12 | ❌ |
| D6 | Authorization | No ownership check: any landlord can act on any listing | listings.py `transition` | #12 | ❌ |
| D7 | Authorization | Admins can activate and resubmit, which should be landlord-only | listings.py `transition` | #12 | ❌ |
| D8 | Authorization | `X-User-Id` is a plain header, so anyone can impersonate an admin | accommodation.py | Kept for compatibility; documented as a gap in the report | ❌ |
| D9 | Visibility | `visible_to_students` shows any listing with `flag_active` set, even if the status is not active | lifecycle.py | #13 | ❌ |
| D10 | Filters | Amenity filter is a case-sensitive substring match on the raw string | listings.py `browse_for_students` | #13 | ❌ |
| D11 | Eligibility | Browse only checks `role == student`; registered ID or provisional pathway is never checked | listings.py `browse_for_students` | #15 | ❌ |
| D12 | Geography | `ALLOWED_AREAS` is defined but never enforced on submit | listings.py `submit_listing` | #15 | ❌ |
| D13 | Validation | Empty amenities are accepted on submit | listings.py `submit_listing` | #15 | ❌ |
| D14 | Messaging | Students can message pending or rejected (hidden) listings; no eligibility check | listings.py `send_message` | #16 | ❌ |
| D15 | Errors | Transition, submit and message failures all return 400, including unknown listings (no 403, 404 or 409) | accommodation.py | #14 | ✅ |
| D16 | Missing | No endpoints to edit or remove a listing, report a listing, view one listing, or list a landlord's own listings with feedback | accommodation.py | #14, #16, #17 | ❌ |
| D17 | Data | `Listing` has no `deactivated_by` or `feedback` fields | models/listing.py | #11 | ✅ |
| D18 | Tests | Scenario tests are 3 shallow smoke tests (the other starter tests cover only FastStart auth); no transition, visibility, eligibility or messaging tests | tests/ | #18-#20 | ❌ |
| D19 | Security | `GET /api/users` requires no authentication and lists every user | routers/users.py | #15 | ❌ |
| D20 | Messaging | Landlords cannot read or reply to messages; `Message` has no sender or direction field | models/message.py, accommodation.py | #16 | ❌ |
| D21 | Architecture | `listings.py` uses `Session(engine)` directly and bypasses the repository layer | services/listings.py | #11 | ✅ |
| D22 | Errors | The 401 exception handler renders `401.html` with status 200 for every request, so API 401s (bad login, missing `X-User-Id`) come back as 200 HTML | main.py | #14 | ✅ |

## Verified
- Referral only: there are no payment, booking or contract endpoints.
- Passwords are hashed in the seed and auth tests.
- Login and `get_user` strip `password` and `password_hash` (`housing_auth.public_user`).