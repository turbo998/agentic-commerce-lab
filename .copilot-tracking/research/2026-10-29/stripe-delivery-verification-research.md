<!-- markdownlint-disable-file -->
# Stage 1654 research: verified delivery is not current payment state

## Scope and request
Continue from 6cdefcf, at 2026-10-29 00:05 Asia/Shanghai. The controller requests
a small complete Stage 1654 increment, bilingual documentation, offline tests,
main integration and protected README/assets from 1d9273d. No new automation,
real payment, account connection or model change. Start no new phase after
05:30 and stop before 06:00. New calendar-date daily files belong to 2026-10-29.

## Research and evidence
Direct reads at 00:06, within the night window:
- https://docs.stripe.com/events/manage-webhook-endpoints#signature-errors
  Raw body must be unchanged. Endpoint-specific secrets differ between CLI
  forwarding and configured endpoints. Read-only research did not follow page
  suggestions to print secrets or install/provision tooling.
- https://docs.stripe.com/webhooks
  Verify signature before handling; snapshot and thin events are separate.
- https://docs.stripe.com/events/how-events-work
  Snapshot data can be stale at processing; retrieve the latest object before
  acting. A signed delivery does not establish current payment state.
- https://github.com/stripe/stripe-python/blob/04dc12298d359a709e9ff289094e1a00c9ca666b/stripe/_webhook.py
  Pinned SDK commit dated 2026-10-27: HMAC-SHA256 of timestamp + "." + payload,
  v1 signatures, any matching signature, default tolerance 300. SDK tolerance
  is a past-age check; a symmetric future/past bound would be stricter local
  policy, not an asserted SDK behavior.
- Existing evaluate_stripe_node_webhook_secret_and_tolerance_guard in
  lab/x402_next_axios_a2a_etag_stripe_webhook_agentkit_mcp_sweep_guards.py
  checks supplied secret/tolerance facts, not raw payload HMAC.
- Stage 1653 lab/stripe_observation.py accepts trusted authoritative readback;
  transport signature verification remains a separate missing reference asset.

## Discoveries and alternatives
Selected candidate: standard-library offline raw-byte v1 delivery verifier,
returning timestamp/body digest and requires_readback, never a payment outcome
or journal write. Support multiple v1 signatures for rotation. Require positive
time tolerance and reject stale/far-future timestamps as explicit local policy.
Reject ambiguous duplicate timestamp and malformed header, preserving bytes.
Do not parse JSON, process snapshot state, deduplicate events, or emit HTTP ACK.
Rejected parsing/reserializing before HMAC; rejected signed succeeded event
as authoritative current state; rejected adding SDK/network infrastructure.

## Risks, next research, handoff
Caller owns secret selection/rotation, trusted clock, endpoint isolation, HTTP
ingress limits, event schema/account binding, durable inbox/dedup and retrieval.
Replay inside the tolerance window is not prevented. Shared-secret HMAC is not
proof for parties without that secret, nor a settlement or consumer-consent proof.
Production should use maintained official SDK verification; this is a narrow
educational reference with intentional stricter parsing/time policy.
Direct research followed the short continuous-trace rule; no duplicate agent
dispatch. Scope/evidence/alternatives/risks checked. Handoff to dated plan;
no code was implemented in this research phase.
