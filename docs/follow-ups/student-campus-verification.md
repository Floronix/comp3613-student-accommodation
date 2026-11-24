# Follow-up draft: Verify student eligibility

**Status:** Draft only; not posted or implemented in Task 15.

## Problem

Task 15's browse gate accepts a nonblank student ID or the provisional incoming flag. It does not confirm campus affiliation against campus records or approved proof, so those fields alone are not verification.

## Proposed follow-up

Define and implement a trustworthy verification path using an authoritative campus record or an approved proof-review process. Keep the existing Task 15 gate distinct from this stronger verification until the accepted sources, review owner, and provisional-student policy are agreed.

## Acceptance criteria

- Eligibility is based on a campus-record match or an approved proof decision, not merely a user-entered ID string.
- Missing, mismatched, or unverifiable evidence is denied without exposing sensitive records or evidence.
- The provisional incoming-student path has an explicit, documented verification rule.
- Tests cover successful verification and missing, mismatched, and unverifiable evidence.
- The verification decision can be reused consistently anywhere student eligibility is enforced.
