# User Acceptance Test Plan

## Purpose and scope

All scenarios are **Planned** and none has been executed.
Each scenario lists the steps and expected result.
These cases cover the acceptance criteria and the main lifecycle, messaging and reporting flows.
The application is a referral platform. Payments, bookings, and contracts are
out of scope. 

## Interview scope

| Selected Student Accommodation source | Related UAT scenarios |
|---|---|
| Campus accommodation admin: listing decisions, provisional review, rejection, safety/suitability, deactivation, restoration | UAT-2 through UAT-7, UAT-11, UAT-15, UAT-23 through UAT-26 |
| Landlord: editing, significance of changes, listing availability | UAT-4, UAT-5, UAT-19, UAT-20 |
| Student seeker: availability, search filters, landlord contact, reporting concerns | UAT-3, UAT-9, UAT-10, UAT-12 through UAT-14 |
| Sprint 1 requirements / acceptance criteria (not a separate interview claim) | UAT-1, UAT-8, UAT-16 through UAT-18, UAT-21, UAT-22 |

## Test accounts

(For dev use only)

| Email | Password | Role / test use |
|---|---|---|
| `admin@example.com` | `admin-dev` | Admin |
| `landlord@example.com` | `land-dev` | Landlord 1 |
| `landlord2@example.com` | `land-dev` | Landlord 2 |
| `student@example.com` | `stud-dev` | Student with a registered student ID |
| `incoming@example.com` | `stud-dev` | Provisional incoming student |

UAT-8: create a student with no student ID and provisional = 0 first

Scenario API requests identify their caller with the `X-User-Id` header
which is a demo shortcut, so these checks don't prove production-level security.

## Scenarios

| ID | Scenario | Steps | Expected result | Status |
|---|---|---|---|---|
| UAT-1 | New listing starts as pending | Log in as a landlord and submit a valid listing. | The listing is created with status `pending`. | Planned |
| UAT-2 | Verify, then activate | Admin verifies the listing; its landlord activates it. | Status changes to `verified`, then `active`. | Planned |
| UAT-3 | Students see only active listings | Log in as an eligible student and browse listings. | Pending, provisional, verified, inactive, and rejected listings are not shown. | Planned |
| UAT-4 | Significant edit and re-verification | A landlord changes the bedrooms of their active listing. Admin verifies the revised listing. The landlord then activates it. | Status returns to `pending` and the listing disappears from student browse during review. After verification and activation, status is `active` and is visible again. | Planned |
| UAT-5 | Rejected listing | Admin rejects a listing with a reason. Admin tries to move it directly to pending or provisional. The landlord resubmits without editing, then edits it and resubmits. | Admin cannot bypass landlord resubmission. Resubmission without an edit is refused. After an edit, resubmission succeeds and status is `pending`. | Planned |
| UAT-6 | Unauthorized action | A landlord tries to verify a listing. A second landlord tries to activate the first landlord's listing. | Both requests are refused with `403` and the listing status is unchanged. | Planned |
| UAT-7 | Admin deactivation and restore | Admin deactivates an active listing for a safety or suitability issue. Its landlord tries to reactivate it. After the issue is resolved and reviewed, admin restores it. | The landlord is blocked from reactivating an admin-deactivated listing. Admin restore succeeds only after review; status is `active`. | Planned |
| UAT-8 | Eligibility denial | A student with neither a student ID nor the provisional flag browses listings. | Access is blocked with an eligibility explanation. | Planned |
| UAT-9 | Messaging visibility | An eligible student messages an active listing, then tries a non-active listing. | The active-listing message succeeds; the non-active-listing message is blocked. | Planned |
| UAT-10 | Report a listing | A student reports an active listing. Admin views reports. | The report appears in the admin report list with its listing and reason. | Planned |
| UAT-11 | Provisional approval and feedback | Admin provisionally approves a pending listing with feedback. The landlord views the feedback and edits the listing to address it. Admin verifies it; the landlord activates it. | The listing remains hidden from students while provisional and verified. The landlord sees the feedback. After verification and activation, status is `active` and is visible. | Planned |
| UAT-12 | Student filters | An eligible student filters active listings by area, maximum price, and amenity, using different letter casing for the amenity. | Only matching active listings appear; amenity matching is case-insensitive. | Planned |
| UAT-13 | Direct link visibility and details | A student opens a non-active listing by ID, then an active listing by ID. | The non-active listing returns not found. The active listing opens with price, location, amenities, other property details, and the landlord's phone and email. | Planned |
| UAT-14 | Landlord inbox | A student messages an active listing. Its landlord reads the messages and replies. The student views the reply. | The landlord sees the student's message, and the student sees the landlord's reply. | Planned |
| UAT-15 | Invalid transition and action | A landlord tries to activate a pending listing. On a separate active listing, the landlord posts `submit` to the transition endpoint to try to bypass review. | Activation is refused with `409`; the unknown transition action is refused with `400`; neither listing's status changes. | Planned |
| UAT-16 | Remove listing | A landlord removes their own listing. A second landlord tries to remove that listing. | The owner's removal succeeds and the listing disappears from all lists. The second landlord is refused with `403`. | Planned |
| UAT-17 | Both eligible student pathways | The registered-ID student and provisional incoming student each browse listings and open an active listing. | Both students can access eligible listings; non-active listings remain hidden. | Planned |
| UAT-18 | Supported accommodation areas | A landlord submits and edits listings using `st_augustine` and `mount_hope`, then tries an unsupported area. | The two supported areas are accepted; the unsupported area is refused and does not change or create a listing. Student area filtering returns only the selected area. | Planned |
| UAT-19 | Minor edit does not trigger review | A landlord changes only the photos or contact details of an active listing. | Status remains `active`, and the listing remains visible to students. | Planned |
| UAT-20 | Landlord deactivation and reactivation | A landlord deactivates their own active listing and then activates it again. | The listing moves to `inactive`, then returns to `active`; it is hidden while inactive and visible after activation. | Planned |
| UAT-21 | Listing input validation | A landlord submits listings with a non-positive price, empty amenities, or negative bedroom/bathroom counts. | Each invalid submission is rejected with a clear validation error and no listing is created. | Planned |
| UAT-22 | Login response and caller errors | Log in with valid credentials, then with an incorrect password. Make an API request without `X-User-Id` and with an unknown user ID. | Valid login succeeds without returning password or password-hash fields. Invalid credentials and missing or unknown caller IDs are rejected; unauthenticated API requests return `401`. | Planned |
| UAT-23 | Review reason and feedback required | Admin tries to reject a listing without a reason and provisionally approve one without feedback. | Both requests are refused with `400`; the listing remains `pending`. | Planned |
| UAT-24 | Restore precondition | A landlord deactivates their own listing. Admin tries to restore it without an admin deactivation. | Restore is refused with `409`; the listing remains `inactive`. | Planned |
| UAT-25 | Provisional listing needs more work or is rejected | Admin provisionally approves a listing with feedback. The landlord edits it; admin keeps it provisional for further work, then rejects it with a reason if it still fails review. | The listing remains hidden while provisional; feedback and rejection reason are visible to its landlord; rejected status is hidden from students. | Planned |
| UAT-26 | Significant edit while inactive | A landlord makes a significant change to their own inactive listing and tries to reactivate it. Admin reviews and verifies the change; the landlord activates it. | The edit returns the listing to `pending`; landlord activation is blocked before verification. It becomes active and visible only after admin verification and landlord activation. | Planned |
