<!-- markdownlint-disable-file -->
# Stage 1670 implementation details

Use StripeEventInbox.read_receipt(scope,event_id), matching the existing Event ID
regex. Reject invalid scope/ID explicitly; query all five PK dimensions and reuse
_receipt. Expected absence returns None, storage exceptions propagate. SELECT only,
no BEGIN IMMEDIATE/clock/HMAC/JSON; local DB/route identity remain trusted.
Tests: absent/present, reopen, full scope isolation, original hash after reserialization,
distinct IDs same object, handled/active state stable, invalid inputs, store failure,
actual SQL trace, receipt outside pending limit, stale delivery does not readmit.
Archive raw-body verification guidance as separate from historical lookup; no ACK/
payment/worker authority. Exact bilingual example, links, daily order, focused/full,
compile/demos, protected diff, generated-report restoration; final CI/canonical gates.
