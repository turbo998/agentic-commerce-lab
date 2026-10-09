# Copilot Studio connector and local walkthrough

## What is implemented

This repository now has a typed local Commerce API facade at `/api/commerce/v1`, a local Copilot-style task/chat screen, and a separate human approval screen at `/consent.html`. All three use the existing Payment Authority and its JSON persistence; this is not a second payment service.

The connector scaffold is [`connector/copilot-commerce.swagger.json`](../connector/copilot-commerce.swagger.json) (OpenAPI/Swagger 2.0). It exposes only:

- list the fixed synthetic catalog;
- create a task and read an owned task;
- request a quote already present in that task's structured proposal;
- create a quote-bound pending human consent request;
- request a task-bound paid-resource HTTP 402 challenge and retry only an already human-approved challenge;
- read the caller's scoped status;
- request, but not approve, an eligible refund.

There is deliberately no connector operation for human approval, budget changes, arbitrary account selection, payment credential retrieval, arbitrary URL/tool execution, or direct payment/refund execution. The approval interface uses a separate synthetic `human` role. A human-approved consent is then consumed by a deterministic local workflow. This permission split is exercised by HTTP tests; it is not a substitute for production identity or authentication.

## Run locally

Requires Node.js 22+. No real Copilot, Microsoft 365, Teams, Entra, provider or LLM connection is made.

```powershell
npm ci
npm run check
npm run test:e2e
npm start
```

Open `http://127.0.0.1:4173`. The main task UI requests only an agent-role token from `POST /api/demo/session`. The separate approval page requires an explicit local “start human review” action and obtains a distinct human-role token from `POST /api/demo/human-session`, which requires a same-origin browser request. Both roles use one of two fixed synthetic identities (`alex@tenant-demo` or `sam@tenant-alt`); tokens expire after one hour or process restart. The user interface selects `alex`; no request body can choose the authenticated owner or tenant. This demo-only separation is not production authentication or Entra validation.

### Weekend shopping

1. Describe a shopping goal, select a synthetic offer from the catalog, and explicitly choose a task-limit currency and amount in the structured budget controls.
2. Submit the task. The deterministic offline script creates a structured suggestion; inspect the visible tool trace and the task's bound limit.
3. Request human approval. Open the separate approval page and verify merchant, items, amount, currency, task, quote version and expiry.
4. Approve the exact quote. The synthetic workflow captures the simulated payment and creates a receipt; return to the task UI for status and optional simulated fulfillment/refund request.

Free-text goals are never parsed into payment policy: a statement such as “spend at most 100 USD” does not set a limit. Only the structured task-limit fields bind policy. The task limit is a single currency and caps the sum of captured amounts plus active consent reservations across that task; the account-level balance is checked separately. Declined, revoked or expired requests release reservations, but refunds do not restore task capacity. Each merchant quote receives a separate approval.

### Travel and paid information

1. Select the travel journey, choose USDC as the structured task-limit currency, set an explicit limit at least as high as the displayed guide quote, and submit the task.
2. Click **Request human approval** on the travel-guide proposal. The task UI first sends the typed `POST /api/commerce/v1/resources/travel-guide` call and records its actual HTTP 402 challenge in the tool trace; it then requests the quote and creates a consent bound to that task, exact quote and challenge.
3. Open the linked separate human page and approve or reject. Approval causes a constrained retry of that same typed resource operation; the server captures the simulated payment and returns the fixed synthetic information response and receipt. Rejection does not capture or deliver.
4. The travel ticket/transport offers remain separate tasks and approvals; they do not inherit the information-service approval.

An unknown payment remains reserved until status reconciliation. Fulfillment errors enter persistent manual review. Refunds requested by an agent remain pending until a human approves them.

## Local connector contract checks

The Swagger definition points at `http://localhost:4173` and uses a `LocalDemoBearer` placeholder solely for local HTTP contract validation. `POST /api/demo/session` returns synthetic role tokens; provide `Bearer <agentToken>` when exercising API operations directly. Do not copy these tokens to a hosted connector, a chat prompt, a screenshot, or source control.

Copilot Studio hosted execution cannot reach a developer's loopback `localhost`. The schema is an import scaffold, not proof of connector import, publication or channel execution. A future tenant integration requires, at minimum:

1. an explicitly authorized HTTPS-hosted API endpoint and service operations;
2. approved Entra OAuth audience, delegated scopes, subject/tenant validation and least-privilege connector identity;
3. a separate authenticated human approval application, with its own session binding and CSRF protections;
4. Power Platform environment/tenant licensing, DLP policy, connector review, Copilot Studio tool configuration, and administrator approval;
5. tenant-level integration/negative tests for spoofed subjects, cross-tenant data, agent self-approval, revocation, replay, timeout/reconciliation and audit retention.

The local synthetic identity registry is not Entra authentication. No hosting, public tunnel, tenant configuration, connector publication, model call, provider sandbox or live transaction has been performed or authorized here. Hosted Copilot cannot call a developer's loopback address; a future tenant integration needs separately authorized HTTPS hosting and the gates above. Follow [Copilot Studio advanced connector guidance](https://learn.microsoft.com/microsoft-copilot-studio/advanced-connectors) and [Teams channel publication guidance](https://learn.microsoft.com/microsoft-copilot-studio/publication-add-bot-to-microsoft-teams) when a tenant owner separately approves that phase.
