# Stage Benchmark Archive Index (`Stage 001` – `Stage 773`)

> **Why this index exists**: Earlier versions of `README.md` and `README.en.md` embedded every individual `Stage 267..773` report link on a single 300+ KB table row, making the repository homepage slow to load and difficult to scan. All historical stage benchmark decks (`reports/agentic-commerce-*`) remain preserved in the repository and are indexed by cohort below.

![Agentic Commerce 4-Layer Architecture](../assets/svg/01-agentic-commerce-webiq-architecture.svg)

---

## Nightly research increments (not model benchmarks)

**Stage 1652 / 2026-10-28:** [Authority boundaries and durable recovery (EN)](research/2026-10-28-authority-recovery.en.md)
| [权限边界与持久化恢复（中文）](research/2026-10-28-authority-recovery.md).
Offline payment-attempt journal; no change to the README/SVG executive overview.

**Stage 1653 / 2026-10-28:** [PaymentIntent observation binding (EN)](research/2026-10-28-stripe-observation.en.md)
| [PaymentIntent 观察绑定（中文）](research/2026-10-28-stripe-observation.md).
Offline provider-semantic readback gate; intermediate states retain unknown.

**Stage 1654 / 2026-10-29:** [Raw-byte webhook verification (EN)](research/2026-10-29-stripe-delivery.en.md)
| [原始字节验签与回读边界（中文）](research/2026-10-29-stripe-delivery.md).
Offline HMAC transport evidence; signed events never directly close unknown payments.

**Stage 1655 / 2026-10-29:** [Scoped durable event receipt (EN)](research/2026-10-29-stripe-inbox.en.md)
| [持久事件接收与业务幂等边界（中文）](research/2026-10-29-stripe-inbox.md).
Verified SQLite receipt dedup; no worker completion or payment-effect guarantee.

**Stage 1656 / 2026-10-29:** [Explicit readback handoff fencing (EN)](research/2026-10-29-stripe-readback.en.md)
| [回读工作交接与旧 generation 拒绝（中文）](research/2026-10-29-stripe-readback.md).
Local ownership generations only; no automatic lease or external payment-effect fencing.

**Stage 1657 / 2026-10-29:** [Atomic local readback acceptance (EN)](research/2026-10-29-stripe-atomic-readback.en.md)
| [同库回读接纳与支付写入门禁（中文）](research/2026-10-29-stripe-atomic-readback.md).
Opt-in shared transaction for active-claim validation, journal update and hint completion;
no provider freshness, new payment authority or remote atomicity.

**Stage 1658 / 2026-10-29:** [Durable Poppy assertion replay admission (EN)](research/2026-10-29-poppy-replay.en.md)
| [Poppy assertion 持久化重放接纳（中文）](research/2026-10-29-poppy-replay.md).
Published-0.2 Session assertion replay history survives restart; no JWT/DPoP
verification, token issuance or purchase authority is implied.

**Stage 1659 / 2026-10-29:** [Exact merchant request binding (EN)](research/2026-10-29-request-binding.en.md)
| [商户请求签名覆盖与原始字节绑定（中文）](research/2026-10-29-request-binding.md).
Opt-in one-signature snapshot/body binding; no RFC signature verification,
consumer authorization, replay consumption or economic mutation is implied.

**Stage 1660 / 2026-10-29:** [Signed checkout admission (EN)](research/2026-10-29-checkout-admission.en.md)
| [签名正文、可信报价与支付尝试接纳（中文）](research/2026-10-29-checkout-admission.md).
Opt-in strict JSON/trusted-quote matching before existing durable reservation;
no client-price authority, consent service or provider request is added.

**Stage 1661 / 2026-10-29:** [Atomic local approval admission (EN)](research/2026-10-29-approval-admission.en.md)
| [同库审批撤销与 reservation 门禁（中文）](research/2026-10-29-approval-admission.md).
Opt-in immutable approval/expiry/revocation checks and reservation in one local
transaction; no consent proof, remote cancellation or payment send is implied.

**Stage 1662 / 2026-10-29:** [First-admission provenance (EN)](research/2026-10-29-admission-provenance.en.md)
| [首次准入历史与禁止回填（中文）](research/2026-10-29-admission-provenance.md).
First-gate history commits with a new reservation; retries/legacy attempts never
backfill consent history. No authenticated consent, signed receipt or payment proof.

**Stage 1663 / 2026-10-29:** [Validated first PaymentIntent association (EN)](research/2026-10-29-stripe-association.en.md)
| [首次 PaymentIntent 关联前校验（中文）](research/2026-10-29-stripe-association.md).
Opt-in full readback validation before persisting a separately trusted reference;
association stays unknown and never infers consent, new dispatch or payment success.

**Stage 1664 / 2026-10-29:** [Post-lock Poppy assertion time (EN)](research/2026-10-29-poppy-admission-clock.en.md)
| [Poppy assertion 锁后时间采样（中文）](research/2026-10-29-poppy-admission-clock.md).
Required-clock opt-in admission shares the existing replay history, rejecting
assertions expired while queued; no JWT verification, token issuance or purchase authority.

**Stage 1665 / 2026-10-29:** [Trusted webhook secret overlap (EN)](research/2026-10-29-stripe-secret-rotation.en.md)
| [Webhook 可信密钥重叠与退役边界（中文）](research/2026-10-29-stripe-secret-rotation.md).
Additive same-endpoint active-secret tuples share existing verification and receipt
identity; no automatic retirement, new payment authority or provider outcome.

**Stage 1666 / 2026-10-29:** [Local merchant signer admission (EN)](research/2026-10-29-merchant-signer-admission.en.md)
| [商户 signer 撤销与同库准入（中文）](research/2026-10-29-merchant-signer-admission.md).
Opt-in scoped local signer permission shares approval/reservation transaction;
no cryptographic verification, signer provenance, remote revocation or payment send.

**Stage 1667 / 2026-10-29:** [Shared post-lock signature time (EN)](research/2026-10-29-merchant-signature-time.en.md)
| [签名窗口与 approval 共用锁后时间（中文）](research/2026-10-29-merchant-signature-time.md).
Opt-in same-signature time metadata shares one clock sample with approval/reservation;
no crypto, nonce consumption, time provenance or commit/send deadline is implied.

**Stage 1668 / 2026-10-29:** [First timed signer history (EN)](research/2026-10-29-timed-signer-history.en.md)
| [首次 timed signer 准入历史（中文）](research/2026-10-29-timed-signer-history.md).
New timed reservations commit a distinct first-branch record with attempt/approval;
no retry/legacy backfill, cryptographic proof, current authority or nonce consumption.

**Stage 1669 / 2026-10-29:** [Stripe receipt time boundaries (EN)](research/2026-10-29-stripe-receipt-clock.en.md)
| [Stripe receipt 入口与锁后时钟（中文）](research/2026-10-29-stripe-receipt-clock.md).
Opt-in two-sample admission rechecks signed delivery time after the writer lock;
old ingress-only API persists, without worker expiry, secret refresh or payment authority.

**Stage 1670 / 2026-10-29:** [Scoped receipt reader (EN)](research/2026-10-29-stripe-receipt-read.en.md)
| [五维 receipt 历史查询（中文）](research/2026-10-29-stripe-receipt-read.md).
Direct original-history lookup beyond bounded enumeration; no current-delivery,
ACK, worker or payment authority.

**Stage 1671 / 2026-10-30:** [Scoped Poppy replay history lookup (EN)](research/2026-10-30-poppy-replay-read.en.md)
| [Poppy assertion 作用域重放历史查询（中文）](research/2026-10-30-poppy-replay-read.md).
Read-only three-column PK lookup anchored to published 0.2 while contrasting Draft 0.3;
no pre-check admission, token-issuance proof or payment authority.

**Stage 1672 / 2026-10-31:** [Scoped Stripe readback claim state lookup (EN)](research/2026-10-31-stripe-claim-read.en.md)
| [Stripe readback claim 作用域状态查询（中文）](research/2026-10-31-stripe-claim-read.md).
Read-only claim-state lookup by five-dimensional receipt scope and Event ID; no claim creation,
handoff completion, worker liveness proof or payment authority.

**Stage 1673 / 2026-10-31:** [Source-monitor Stripe SPT noise filter (EN)](research/2026-10-31-source-monitor-noise-filter.en.md)
| [source-monitor 的 Stripe SPT 抖动降噪（中文）](research/2026-10-31-source-monitor-noise-filter.md).
Source-specific normalization redacts volatile `expires_at` sample timestamps before hashing;
preserves substantive text drift detection without treating second-level example jitter as release evidence.

**Stage 1674 / 2026-10-31:** [Stripe SPT selected-facts extraction in source monitor (EN)](research/2026-10-31-stripe-spt-facts.en.md)
| [source-monitor 的 Stripe SPT 稳定事实提取（中文）](research/2026-10-31-stripe-spt-facts.md).
Adds parser-backed Stripe SPT selected facts (preview API version, country-list cardinality/hash,
event markers) to distinguish stable contract signals from markdown hash drift.

**Stage 1675 / 2026-10-31:** [Source-fact-driven Stripe MCP deadline simulation (EN)](research/2026-10-31-mcp-deadline-source-facts.en.md)
| [基于 source facts 的 Stripe MCP 截止日仿真（中文）](research/2026-10-31-mcp-deadline-source-facts.md).
`lab.mcp_migration` can now load Stripe MCP selected facts from a daily source-monitor snapshot and
simulate migration/block boundaries against that observed deadline without adding live account checks.

**Stage 1676 / 2026-10-31:** [Stripe SPT Connect selected-facts extraction (EN)](research/2026-10-31-stripe-spt-connect-facts.en.md)
| [source-monitor 的 Stripe SPT Connect 稳定事实提取（中文）](research/2026-10-31-stripe-spt-connect-facts.md).
Adds parser-backed selected facts for the Connect-tab SPT markdown and records facts-level drift
separately from hash changes, while preserving offline-only monitoring boundaries.

**Stage 1677 / 2026-10-31:** [SPT seller/connect parity cross-check in source monitor (EN)](research/2026-10-31-spt-parity-cross-check.en.md)
| [source-monitor 的 SPT seller/connect 一致性检查（中文）](research/2026-10-31-spt-parity-cross-check.md).
Adds report-level `cross_source_checks` parity validation for seller/connect SPT country-list facts
to highlight selected-fact consistency without claiming a product release.

**Stage 1678 / 2026-10-31:** [SPT parity mismatch fail-fast gate (EN)](research/2026-10-31-spt-parity-mismatch-gate.en.md)
| [SPT 一致性不匹配显式失败门禁（中文）](research/2026-10-31-spt-parity-mismatch-gate.md).
Escalates `cross_source_checks` parity mismatches to a nonzero monitor exit code so seller/connect
fact divergence is surfaced as a blocking review signal rather than a silent warning.

**Stage 1679 / 2026-10-31:** [SPT Connect required-markers cross-check (EN)](research/2026-10-31-spt-connect-marker-check.en.md)
| [SPT Connect 必需标记互证检查（中文）](research/2026-10-31-spt-connect-marker-check.md).
Adds a second `cross_source_checks` gate that verifies required Connect-tab SPT markers remain present
and fails fast when any marker disappears from selected facts.

**Stage 1680 / 2026-10-31:** [SPT parser-version parity gate (EN)](research/2026-10-31-spt-parser-version-parity.en.md)
| [SPT 解析器版本一致性门禁（中文）](research/2026-10-31-spt-parser-version-parity.md).
Adds a third `cross_source_checks` gate enforcing reviewed seller/connect parser-version pairs and
failing fast when selected facts drift onto unreviewed parser grammars.

**Stage 1681 / 2026-10-31:** [Cross-source summary telemetry for SPT checks (EN)](research/2026-10-31-spt-cross-source-summary.en.md)
| [SPT 跨来源检查摘要信号（中文）](research/2026-10-31-spt-cross-source-summary.md).
Adds report-level `cross_source_summary` counters (`total/consistent/mismatch/unavailable/blocking`)
to simplify machine and human interpretation of current SPT gate health.

**Stage 1682 / 2026-10-31:** [Source monitor gate-health summary telemetry (EN)](research/2026-10-31-source-monitor-gate-health-summary.en.md)
| [source-monitor 运行门禁健康摘要信号（中文）](research/2026-10-31-source-monitor-gate-health-summary.md).
Adds report-level `gate_health` counters that combine fetch errors, policy parse errors, and
cross-source mismatches into one explicit blocking signal for deterministic automation gating.

**Stage 1683 / 2026-10-31:** [Source monitor gate-health blocking reasons (EN)](research/2026-10-31-source-monitor-gate-health-reasons.en.md)
| [source-monitor 运行门禁阻塞原因信号（中文）](research/2026-10-31-source-monitor-gate-health-reasons.md).
Extends `gate_health` with ordered `blocking_reasons` so automation can classify why a run blocked
without re-scanning per-observation details.

**Stage 1684 / 2026-10-31:** [Source monitor cross-source status index (EN)](research/2026-10-31-source-monitor-cross-source-status-index.en.md)
| [source-monitor 跨来源检查状态索引（中文）](research/2026-10-31-source-monitor-cross-source-status-index.md).
Adds report-level `cross_source_statuses` (`check_id -> status`) for deterministic machine parsing
without scanning the full `cross_source_checks` array.

**Stage 1685 / 2026-10-31:** [Source monitor cross-source status partitions (EN)](research/2026-10-31-source-monitor-cross-source-partitions.en.md)
| [source-monitor 跨来源检查状态分组（中文）](research/2026-10-31-source-monitor-cross-source-partitions.md).
Adds report-level `cross_source_partitions` to group check IDs by `consistent/mismatch/unavailable`
for direct blocker routing without scanning raw check objects.

**Stage 1686 / 2026-10-31:** [Source monitor blocking check IDs in gate health (EN)](research/2026-10-31-source-monitor-gate-health-blocking-checks.en.md)
| [source-monitor gate_health 阻塞检查 ID 信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-checks.md).
Adds `gate_health.cross_source_blocking_checks` so blocking check IDs are available directly in the
run-level gate object without cross-field joins.

**Stage 1687 / 2026-10-31:** [Source monitor report schema versioning (EN)](research/2026-10-31-source-monitor-schema-version.en.md)
| [source-monitor 报告 schema 版本标识（中文）](research/2026-10-31-source-monitor-schema-version.md).
Adds explicit `schema_version` to each daily report for deterministic consumer compatibility checks
as report fields continue to evolve.

**Stage 1688 / 2026-10-31:** [Source monitor observation summary telemetry (EN)](research/2026-10-31-source-monitor-observation-summary.en.md)
| [source-monitor 来源观察摘要信号（中文）](research/2026-10-31-source-monitor-observation-summary.md).
Adds report-level `observation_summary` counters (`ok/error` and `baseline/unchanged/changed/unknown`)
for deterministic source-fetch health and drift-shape monitoring.

**Stage 1689 / 2026-10-31:** [Source monitor observation partitions telemetry (EN)](research/2026-10-31-source-monitor-observation-partitions.en.md)
| [source-monitor 来源观察分组信号（中文）](research/2026-10-31-source-monitor-observation-partitions.md).
Adds report-level `observation_partitions` grouping source IDs by `ok/error` and
`baseline/unchanged/changed/unknown` to support deterministic alert routing without raw-array scans.

**Stage 1690 / 2026-10-31:** [Source monitor gate-health source IDs telemetry (EN)](research/2026-10-31-source-monitor-gate-health-source-ids.en.md)
| [source-monitor gate_health 源 ID 信号（中文）](research/2026-10-31-source-monitor-gate-health-source-ids.md).
Extends `gate_health` with `observation_error_sources` and `policy_error_sources` so source-level blockers
are directly consumable without per-observation joins.

**Stage 1691 / 2026-10-31:** [Source monitor gate-health blocking sources telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-sources.en.md)
| [source-monitor gate_health 阻塞源集合信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-sources.md).
Adds `gate_health.blocking_sources` as a deduplicated union of source-level error IDs for direct blocker routing.

**Stage 1692 / 2026-10-31:** [Source monitor gate-health blocking dimensions telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-dimensions.en.md)
| [source-monitor gate_health 阻塞维度分组信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-dimensions.md).
Adds `gate_health.blocking_dimensions` with per-dimension blocker lists
(`observation_errors`/`policy_errors`/`cross_source_mismatch`) for deterministic routing.

**Stage 1693 / 2026-10-31:** [Source monitor gate-health blocking fingerprint telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-fingerprint.en.md)
| [source-monitor gate_health 阻塞指纹信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-fingerprint.md).
Adds `gate_health.blocking_fingerprint` (SHA-256 of blocking dimensions + reasons) for stable gate-state change detection.

**Stage 1694 / 2026-10-31:** [Source monitor gate-health fingerprint version telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-fingerprint-version.en.md)
| [source-monitor gate_health 阻塞指纹版本信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-fingerprint-version.md).
Adds `gate_health.blocking_fingerprint_version` (`sha256-json-v1`) so downstream consumers can
bind comparison logic to an explicit digest-contract version.

**Stage 1695 / 2026-10-31:** [Source monitor gate-health blocking state ID telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-state-id.en.md)
| [source-monitor gate_health 阻塞状态 ID 信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-state-id.md).
Adds `gate_health.blocking_state_id` as `<blocking_fingerprint_version>:<blocking_fingerprint>`
for single-field, version-aware gate-state comparisons.

**Stage 1696 / 2026-10-31:** [Source monitor gate-health blocking state transition telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-state-transition.en.md)
| [source-monitor gate_health 阻塞状态迁移信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-state-transition.md).
Adds `gate_health.blocking_state_previous` and `gate_health.blocking_state_transition`
(`baseline`/`unchanged`/`changed`) to express state drift against the latest prior daily snapshot.

**Stage 1697 / 2026-10-31:** [Source monitor gate-health previous checkpoint telemetry (EN)](research/2026-10-31-source-monitor-gate-health-previous-checkpoint.en.md)
| [source-monitor gate_health 前态检查点信号（中文）](research/2026-10-31-source-monitor-gate-health-previous-checkpoint.md).
Adds `gate_health.blocking_state_previous_checked_at` to anchor transition comparisons to
the exact prior snapshot timestamp used by the monitor.

**Stage 1698 / 2026-10-31:** [Source monitor gate-health previous report-date telemetry (EN)](research/2026-10-31-source-monitor-gate-health-previous-report-date.en.md)
| [source-monitor gate_health 前态报告日期信号（中文）](research/2026-10-31-source-monitor-gate-health-previous-report-date.md).
Adds `gate_health.blocking_state_previous_report_date` so transition metadata includes
the concrete prior daily report date (`YYYY-MM-DD`) in addition to prior `checked_at`.

**Stage 1699 / 2026-10-31:** [Source monitor gate-health transition-reason telemetry (EN)](research/2026-10-31-source-monitor-gate-health-transition-reason.en.md)
| [source-monitor gate_health 迁移原因信号（中文）](research/2026-10-31-source-monitor-gate-health-transition-reason.md).
Adds `gate_health.blocking_state_transition_reason`
(`no_prior_state`/`state_unchanged`/`state_changed`) for deterministic transition interpretation.

**Stage 1700 / 2026-10-31:** [Source monitor gate-health transition fingerprint telemetry (EN)](research/2026-10-31-source-monitor-gate-health-transition-fingerprint.en.md)
| [source-monitor gate_health 迁移指纹信号（中文）](research/2026-10-31-source-monitor-gate-health-transition-fingerprint.md).
Adds `gate_health.blocking_transition_fingerprint` with version
`gate_health.blocking_transition_fingerprint_version` (`sha256-transition-v1`) for edge-level transition deduplication.

**Stage 1701 / 2026-10-31:** [Source monitor gate-health transition event telemetry (EN)](research/2026-10-31-source-monitor-gate-health-transition-event.en.md)
| [source-monitor gate_health 迁移事件信号（中文）](research/2026-10-31-source-monitor-gate-health-transition-event.md).
Adds `gate_health.blocking_transition_event` as a direct boolean event flag
(`true` when transition is `changed`) for alert routing without string parsing.

**Stage 1702 / 2026-10-31:** [Source monitor gate-health transition event ID telemetry (EN)](research/2026-10-31-source-monitor-gate-health-transition-event-id.en.md)
| [source-monitor gate_health 迁移事件 ID 信号（中文）](research/2026-10-31-source-monitor-gate-health-transition-event-id.md).
Adds `gate_health.blocking_transition_event_id` so changed transitions expose a stable
event identifier (`sha256-transition-v1:<transition_fingerprint>`) for idempotent downstream routing.

**Stage 1703 / 2026-10-31:** [Source monitor gate-health transition event-state telemetry (EN)](research/2026-10-31-source-monitor-gate-health-transition-event-state.en.md)
| [source-monitor gate_health 迁移事件状态对信号（中文）](research/2026-10-31-source-monitor-gate-health-transition-event-state.md).
Adds `gate_health.blocking_transition_event_state` so changed transitions expose a direct
`from_state_id/to_state_id` pair without downstream cross-field reconstruction.

**Stage 1704 / 2026-10-31:** [Source monitor gate-health transition event payload telemetry (EN)](research/2026-10-31-source-monitor-gate-health-transition-event-payload.en.md)
| [source-monitor gate_health 迁移事件载荷信号（中文）](research/2026-10-31-source-monitor-gate-health-transition-event-payload.md).
Adds `gate_health.blocking_transition_event_payload` to bundle `event_id/from_state_id/to_state_id/reason`
for changed transitions in one object, with `null` on baseline/unchanged runs.

**Stage 1705 / 2026-10-31:** [Source monitor gate-health transition event payload version telemetry (EN)](research/2026-10-31-source-monitor-gate-health-transition-event-payload-version.en.md)
| [source-monitor gate_health 迁移事件载荷版本信号（中文）](research/2026-10-31-source-monitor-gate-health-transition-event-payload-version.md).
Adds `gate_health.blocking_transition_event_payload_version` (`event-payload-v1`) so downstream
consumers can bind payload-schema parsing to an explicit version contract.

**Stage 1706 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta.en.md)
| [source-monitor gate_health 阻塞原因增量信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta.md).
Adds `gate_health.blocking_reasons_previous/added/removed` so downstream pipelines can consume
reason-level changes directly without reconstructing diffs across snapshots.

**Stage 1707 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta fingerprint telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-fingerprint.en.md)
| [source-monitor gate_health 阻塞原因增量指纹信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-fingerprint.md).
Adds `gate_health.blocking_reasons_delta_fingerprint` with version
`gate_health.blocking_reasons_delta_fingerprint_version` (`sha256-reasons-delta-v1`) for reason-delta deduplication.

**Stage 1708 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta event telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-event.en.md)
| [source-monitor gate_health 阻塞原因增量事件信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-event.md).
Adds `gate_health.blocking_reasons_delta_event` so downstream routers can quickly branch on whether
reason-level deltas are present, without inspecting delta arrays.

**Stage 1709 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta payload telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-payload.en.md)
| [source-monitor gate_health 阻塞原因增量载荷信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-payload.md).
Adds `gate_health.blocking_reasons_delta_payload` to bundle reason-delta event state, prior/current sets,
set differences, and deduplication fingerprint in one object for single-read downstream routing.

**Stage 1710 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta payload-version telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-payload-version.en.md)
| [source-monitor gate_health 阻塞原因增量载荷版本信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-payload-version.md).
Adds `gate_health.blocking_reasons_delta_payload_version` (`reasons-delta-payload-v1`) so downstream
consumers can bind reason-delta payload parsing to an explicit versioned contract.

**Stage 1711 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta payload-id telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-payload-id.en.md)
| [source-monitor gate_health 阻塞原因增量载荷 ID 信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-payload-id.md).
Adds `gate_health.blocking_reasons_delta_payload_id` as a version-prefixed single-value identifier
(`${payload_version}:${delta_fingerprint}`) for downstream idempotent routing and deduplication.

**Stage 1712 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta counts telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-counts.en.md)
| [source-monitor gate_health 阻塞原因增量计数信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-counts.md).
Adds `gate_health.blocking_reasons_delta_counts` with `{previous,current,added,removed}` counts
for low-overhead downstream aggregation without expanding full reason arrays.

**Stage 1713 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta total-changes telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-total-changes.en.md)
| [source-monitor gate_health 阻塞原因增量总变化数信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-total-changes.md).
Adds `gate_health.blocking_reasons_delta_total_changes` as a single-value `added + removed`
change-magnitude signal for threshold-based downstream routing.

**Stage 1714 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta direction telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-direction.en.md)
| [source-monitor gate_health 阻塞原因增量方向信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-direction.md).
Adds `gate_health.blocking_reasons_delta_direction` with stable enums
(`increase`/`decrease`/`mixed`/`none`) for direct downstream routing by change direction.

**Stage 1715 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta net-change telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-net-change.en.md)
| [source-monitor gate_health 阻塞原因增量净变化信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-net-change.md).
Adds `gate_health.blocking_reasons_delta_net_change` as signed
`len(current)-len(previous)` telemetry for threshold-based downstream routing.

**Stage 1716 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta net-change-magnitude telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-net-change-magnitude.en.md)
| [source-monitor gate_health 阻塞原因增量净变化绝对值信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-net-change-magnitude.md).
Adds `gate_health.blocking_reasons_delta_net_change_magnitude` as
`abs(len(current)-len(previous))` telemetry for sign-independent threshold routing.

**Stage 1717 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta has-change telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-has-change.en.md)
| [source-monitor gate_health 阻塞原因增量是否变化布尔信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-has-change.md).
Adds `gate_health.blocking_reasons_delta_has_change` as boolean
`blocking_reasons_delta_total_changes > 0` telemetry for direct change gating.

**Stage 1718 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta change-state telemetry (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state.en.md)
| [source-monitor gate_health 阻塞原因增量变化状态枚举信号（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state.md).
Adds `gate_health.blocking_reasons_delta_change_state` enum
(`changed`/`unchanged`) telemetry for direct state-based policy routing.

**Stage 1719 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta change-state version contract (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-version.en.md)
| [source-monitor gate_health 阻塞原因增量变化状态版本契约（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-version.md).
Adds `gate_health.blocking_reasons_delta_change_state_version` as fixed
`reasons-delta-change-state-v1` contract metadata for version-aware consumers.

**Stage 1720 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta change-state identifier (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-id.en.md)
| [source-monitor gate_health 阻塞原因增量变化状态标识符（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-id.md).
Adds `gate_health.blocking_reasons_delta_change_state_id` as versioned
`<change_state_version>:<change_state>` identifier for idempotent routing.

**Stage 1721 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta change-state structured payload (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-payload.en.md)
| [source-monitor gate_health 阻塞原因增量变化状态结构化载荷（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-payload.md).
Adds `gate_health.blocking_reasons_delta_change_state_payload` with
`{version, state, id}` for direct structured consumption.

**Stage 1722 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta change-state payload fingerprint (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-payload-fingerprint.en.md)
| [source-monitor gate_health 阻塞原因增量变化状态载荷指纹（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-payload-fingerprint.md).
Adds `gate_health.blocking_reasons_delta_change_state_payload_fingerprint`
as canonical-payload SHA-256 for single-value comparison.

**Stage 1723 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta change-state payload fingerprint version contract (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-payload-fingerprint-version.en.md)
| [source-monitor gate_health 阻塞原因增量变化状态载荷指纹版本契约（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-payload-fingerprint-version.md).
Adds `gate_health.blocking_reasons_delta_change_state_payload_fingerprint_version`
as fixed version metadata for fingerprint compatibility branching.

**Stage 1724 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta change-state payload fingerprint identifier (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-payload-fingerprint-id.en.md)
| [source-monitor gate_health 阻塞原因增量变化状态载荷指纹标识符（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-payload-fingerprint-id.md).
Adds `gate_health.blocking_reasons_delta_change_state_payload_fingerprint_id`
as versioned `<fingerprint_version>:<fingerprint>` key.

**Stage 1725 / 2026-10-31:** [Source monitor gate-health blocking-reasons delta change-state payload fingerprint structured payload (EN)](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-payload-fingerprint-payload.en.md)
| [source-monitor gate_health 阻塞原因增量变化状态载荷指纹结构化载荷（中文）](research/2026-10-31-source-monitor-gate-health-blocking-reasons-delta-change-state-payload-fingerprint-payload.md).
Adds `gate_health.blocking_reasons_delta_change_state_payload_fingerprint_payload`
to aggregate `{version,fingerprint,id}` into one direct-consumption object.

**Stage 1726 / 2026-10-31:** [Scoped read-only payment approval status lookup and authority boundary (EN)](research/2026-10-31-payment-approval-read.en.md)
| [PaymentApprovalStore.read_approval 作用域审批状态只读查询与权限边界（中文）](research/2026-10-31-payment-approval-read.md).
Adds `PaymentApprovalStore.read_approval(operation)` and `PaymentApprovalStatus`
for lock-free local approval metadata inspection without clock sampling or dispatch authority.

**Stage 1727 / 2026-10-31:** [Scoped read-only merchant signer permission lookup and authority boundary (EN)](research/2026-10-31-merchant-signer-permission-read.en.md)
| [MerchantSignerStore.read_permission 作用域签名密钥权限只读查询与权限边界（中文）](research/2026-10-31-merchant-signer-permission-read.md).
Adds `MerchantSignerStore.read_permission(scope)` and `MerchantSignerPermissionStatus`
for lock-free local merchant signer permission inspection without signature verification or admission authority.

**Stage 1728 / 2026-10-31:** [Scoped read-only payment attempt lookup and unreserved-vs-conflict disambiguation (EN)](research/2026-10-31-payment-attempt-read.en.md)
| [PaymentAttemptJournal.read_attempt 本地支付尝试状态只读查询与未预留/绑定冲突消歧（中文）](research/2026-10-31-payment-attempt-read.md).
Adds `PaymentAttemptJournal.read_attempt(operation)` for lock-free local attempt inspection
that returns `None` when unreserved while raising `AttemptConflict` on fingerprint tampering or corrupted state.

**Stage 1729 / 2026-11-01:** [Optional read-only first-admission history lookup and unadmitted-vs-conflict disambiguation (EN)](research/2026-11-01-payment-admission-find.en.md)
| [PaymentApprovalStore.find_admission 本地首次审批准入历史可选只读查询与未准入/绑定冲突消歧（中文）](research/2026-11-01-payment-admission-find.md).
Adds `PaymentApprovalStore.find_admission(operation)` for lock-free first-admission provenance inspection
that returns `None` when unadmitted while raising `PaymentApprovalError` on fingerprint mismatch or invalid stored timestamps.

**Stage 1730 / 2026-11-01:** [Optional read-only timed-signer admission lookup and non-timed path disambiguation (EN)](research/2026-11-01-timed-signer-admission-find.en.md)
| [MerchantSignerStore.find_timed_admission 计时签名准入历史可选只读查询与非计时路径/绑定冲突消歧（中文）](research/2026-11-01-timed-signer-admission-find.md).
Adds `MerchantSignerStore.find_timed_admission(operation)` for lock-free timed-signer provenance inspection
that returns `None` when unadmitted or admitted via a non-timed path while raising `MerchantSignerError` on fingerprint mismatch or corrupted stored metadata.

**Stage 1731 / 2026-11-01:** [StripeEventInbox persisted receipt and readback claim integrity validation (EN)](research/2026-11-01-stripe-receipt-integrity.en.md)
| [StripeEventInbox 持久化收据与回读认领完整性校验（中文）](research/2026-11-01-stripe-receipt-integrity.md).
Hardens `InboxReceipt` and `InboxDecision` construction invariants, validates hydrated SQLite receipt columns before claiming or reading,
and detects orphan or state-corrupted `stripe_readback_claims` rows across `read_claim()`, `active_claims()`, `finish_readback()`, and `accept_stripe_readback()`.

**Stage 1732 / 2026-11-01:** [Single-snapshot cross-table admission provenance lookup (EN)](research/2026-11-01-operation-admission-provenance.en.md)
| [跨表准入溯源单快照只读审计（中文）](research/2026-11-01-operation-admission-provenance.md).
Adds `OperationAdmissionProvenance`, `MerchantSignerStore.find_provenance()`, and `MerchantSignerStore.read_provenance()`
to inspect `payment_attempts`, `payment_admissions`, and `merchant_timed_admissions` in a single lock-free `SELECT` snapshot while failing closed on orphan rows, fingerprint drift, or clock split-brain.

## 1. Flagship Interactive Deliverables & Core Benchmarks

| Deliverable / Cohort | Primary Entry Points | Key Metrics & Verification |
|---|---|---|
| **Microsoft Web IQ × Agentic Commerce Interactive Workbench** | [`live-demo.html`](../live-demo.html) · [`live-demo.en.html`](../live-demo.en.html) · [`benchmark-cards.html`](../benchmark-cards.html) · [`benchmark-cards.en.html`](../benchmark-cards.en.html) | `18/18` normal checkout pass (`100%`), `12/12` DOM prompt-injection blocked (`100%`), `0.0 pt` option-reversal drift, `1.52s` vs `4.18s` (`2.75x` parallel grounding speedup) |
| **Web IQ Grounding & Multi-Protocol Engine** | [`lab/webiq_commerce_demo.py`](../lab/webiq_commerce_demo.py) · [`src/agentic_commerce/webiq_demo_engine.py`](../src/agentic_commerce/webiq_demo_engine.py) · [`tests/test_webiq_commerce_demo.py`](../tests/test_webiq_commerce_demo.py) | `13/13` unit tests passing (`P95 = 240ms` grounding, `0.002 USDC/call` x402 settlement, `AP2_PRICE_CEILING_EXCEEDED` circuit breaker) |
| **Core 7-Scenario End-to-End Lab Suite** | [`reports/agentic-commerce-7card-deck/index.html`](../reports/agentic-commerce-7card-deck/index.html) · [`report.json`](../reports/agentic-commerce-7card-deck/report.json) · [`lab/runner.py`](../lab/runner.py) | `SC-01..SC-07` (`7/7` pass, `0.0 pt` perturbation drift, `3.21x` async batch speedup) |
| **2026-10-26 Web IQ Deep-Dive Report** | [`docs/research/2026-10-26-webiq-agentic-commerce-demo.md`](research/2026-10-26-webiq-agentic-commerce-demo.md) · [`English`](research/2026-10-26-webiq-agentic-commerce-demo.en.md) | 4-Layer Architecture (`Web IQ` + `ACP/UCP` + `AP2/x402/TAP` + `7-Card Harness`) |
| **2026-10-27 Daily Research Synthesis** | [`docs/research/2026-10-27-daily-research.md`](research/2026-10-27-daily-research.md) · [`research/daily/2026-10-27.md`](../research/daily/2026-10-27.md) | Consolidated protocol interoperability, security guardrails, and benchmark summary |

---

## 2. Historical Stage Benchmark Cohorts (`reports/`)

Instead of listing 800+ individual links on the main README, the historical automated regression cohorts under `reports/` are organized into six functional tracks:

| Stage Cohort | Directory Pattern under `reports/` | Protocol Focus & Guardrail Scope | Cumulative Test Status |
|---|---|---|---|
| **Stages 001 – 065** | `reports/agentic-commerce-7card-deck/` .. `reports/agentic-commerce-ucp-schema-*-bench/` | Foundational ACP (`2026-01-30`), UCP (`2026-01-23`), AP2 v0.1 `MandateVC`, x402 V2 (`eip155:8453`), MCP `2026-10-31` deprecation gate, Visa TAP RFC 9421 signatures, and Sierra $\tau$-bench 2.0 | `284/284` deterministic tests passing |
| **Stages 066 – 195** | `reports/agentic-commerce-x402-*-bench/` & `reports/agentic-commerce-ucp-*-bench/` | Multi-rail x402 (`EVM`, `SVM`, `Stellar`, `XRPL`, `Algorand`, `Cardano`, `TRON`), UCP split-payment schedules & food/lodging checkout, AP2 dispute evidence packs (`ATDRP-0.1`), and MCP `SEP-1932`/`SEP-2792`/`SEP-3415` | `800/800` deterministic tests passing |
| **Stages 196 – 279** | `reports/agentic-commerce-visa-tap-*-bench/` .. `reports/agentic-commerce-x402-eip3009-*-bench/` | Visa TAP mTLS & webhook integrity, Stripe Shared Payment Token (`SPT`) recurring guards, Coinbase AgentKit firewall & preflight checks, Google A2A v1.0 multi-language SDK conformance | `972/972` deterministic tests passing |
| **Stages 280 – 503** | `reports/agentic-commerce-x402-erc*-bench/` (ERC-7683 .. ERC-8950) | Cross-chain intent settlement, Tempo MPP (`draft-httpauth-payment-01`), AP2 verifiable credentials & pay-by-bank, UCP Hydrogen/CheckoutKit bindings, and MCP OAuth 2.1 / PKCE / DPoP | `1,440/1,440` deterministic tests passing |
| **Stages 504 – 618** | `reports/agentic-commerce-x402-erc8960-*-bench/` .. `reports/agentic-commerce-x402-erc9255-*-bench/` | Enterprise cloud service bindings, CloudEvents & OpenTelemetry collector trace correlation, multi-tenant A2A routing, and deterministic replay protection | `1,672/1,672` deterministic tests passing |
| **Stages 619 – 773** | `reports/agentic-commerce-x402-erc9260-*-bench/` .. `reports/agentic-commerce-x402-erc9645-*-bench/` | High-concurrency ERC-9260..ERC-9645 stress cohorts, multi-region settlement failover, and Microsoft Web IQ grounding integration (`reports/agentic-commerce-webiq-grounding-demo-bench/`) | `1,995/1,995` deterministic tests passing |

---

## 3. How to Browse or Re-Run Any Archive Cohort Locally

```bash
# Run the flagship Microsoft Web IQ + ACP/UCP/AP2/x402 benchmark & regenerate 7-card HTML
python -m lab.webiq_commerce_demo

# Run the core 7-scenario Agentic Commerce suite
python -m lab.runner

# List or inspect any specific archived report directory
ls reports/agentic-commerce-webiq-grounding-demo-bench/

# Run the pytest verification suite
pytest tests/test_webiq_commerce_demo.py -q
```
