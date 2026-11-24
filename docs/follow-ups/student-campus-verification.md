# Follow-up draft: Verify student eligibility

**Status:** Task 13 prototype assumption accepted; live campus verification remains a follow-up.

## Task 13 prototype assumption

- A nonblank `student_id` means campus staff have already confirmed the student's current full-time or part-time status against UWI St. Augustine records outside this app.
- `provisional=1` means campus staff have manually reviewed and approved the incoming student's acceptance letter or proof of enrolment outside this app.
- When a student ID is issued, staff record it on the account and clear `provisional`; the ID is then the ongoing eligibility path.
- The app enforces the recorded eligibility fields but does not connect to campus records or upload/store proof documents. If neither an ID nor approved provisional status is recorded, listing access is denied.

## Problem

The existing eligibility gate can enforce the recorded decision, but it cannot independently verify campus affiliation or inspect proof. The project currently has no campus-record integration or in-app proof-review workflow.

## Proposed follow-up

For a live deployment, define and implement a trustworthy verification path using an authoritative campus record or approved proof-review process, including its source, reviewer, and secure evidence handling.

## Acceptance criteria

- Eligibility is based on a campus-record match or an approved proof decision, not merely a user-entered ID string.
- Missing, mismatched, or unverifiable evidence is denied without exposing sensitive records or evidence.
- The provisional incoming-student path has an explicit, documented verification rule.
- Tests cover successful verification and missing, mismatched, and unverifiable evidence.
- The verification decision can be reused consistently anywhere student eligibility is enforced.
