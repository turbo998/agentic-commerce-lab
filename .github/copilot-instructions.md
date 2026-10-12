# Commerce lab engineering boundaries

This repository is an original offline teaching simulation. Use synthetic data only. Do not add model keys, external payment calls, provider SDKs, cloud resources or production-identity claims without a separately approved task.

- Keep planner proposals separate from human consent and deterministic Payment Authority. Agents may request catalog quotes; they cannot approve, pay on their own, refund, or expand a budget.
- Money is a safe integer in the currency's smallest unit. USD/HKD use 2 decimals, USDC 6. Never infer policy from free text or implicitly exchange currencies.
- Individual quote eligibility is not a combined basket or payment permission. Preserve cumulative task spend, valid reservations, account balance, exact consent binding and replay/restart behavior.
- Validate injected planner output against catalog facts and task scope. Reject invalid output explicitly; do not disguise it as a successful filtered proposal.
- Preserve the native Node >=22 HTTP/static stack. No runtime dependencies are needed.
- Validate focused changes with `node --test test/agent.test.js test/budget-http.test.js`; final checks are `npm run check` and `npm run test:e2e`. Actual browser checks are separate from these HTTP tests.
- Use `npm run demo` for workshop state, not the default service. Never reset unrelated state files, services, checkouts, or worktrees. Bind only to loopback.
- Record factual evidence and actual execution host. Do not present unperformed VS Code operations or mock planning as model inference. Instructions guide work; runtime code enforces permissions.
