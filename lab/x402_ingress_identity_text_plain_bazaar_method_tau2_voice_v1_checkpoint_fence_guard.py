"""Stage 188 deterministic guardrails for:

1. x402 Foundation §5.5 Settlement and Refusal Identity Invariant
   (`x402-foundation/x402` PR #3776, implementing #3772, 2026-10-23T17:52:07Z):
   - Single immutable ingress snapshot derivation over all 9 required named
     decoded fields (`method`, `path`, `query`, `body`, `payTo`, `asset`,
     `network`, `amount`, `scheme`), invariant to JSON key order or whitespace
     and NEVER derived over raw wire bytes.
   - Strict normalization (`network` in canonical CAIP-2 `^[a-z0-9]{3,8}:[-_a-zA-Z0-9]{1,32}$`,
     EVM addresses lowercased, timestamps in RFC 3339 `Z` form, URLs not
     normalized) and true absence omission (absent members omitted from the
     hashed set, NEVER coerced to `null`, `""`, or `0`; destroyed member names
     rejected).
   - Countersignature verification & "Absence is not difference": counterparty
     recomputes fingerprint from observed bytes and MUST distinguish
     `refused_value_mismatch` vs. `refused_comparison_impossible` (never
     collapsing unobserved/absent inputs into a pass or generic mismatch).
   - Three distinct signed-artifact identifiers (`operation_identity`,
     `captured_artifact_digest`, `signed_content_identifier`) and strict
     Request-layer vs. Outcome-layer separation (forbidding mid-attempt
     re-derivation or folding outcome metering/delivery data into identity).

2. x402 HTTP 402 `text/plain` Error Body Preservation (`PR #3901` & `#3902`,
   merged 2026-10-23T16:20:45Z), Bazaar Input-Shape Method Resolution
   (`PR #3880`, merged 2026-10-23T16:16:25Z), and Stellar SDK / Axios Floor
   (`PR #3904`, merged 2026-10-23T16:17:49Z):
   - Preserves raw UTF-8 text (including newlines) when a 402 response declares
     `Content-Type: text/plain` and a string `body`, forbidding JSON string
     double-encoding.
   - Resolves Bazaar `info.input.method` and narrows `schema...method.enum` to
     fit the declared input shape (`bodyType != None` -> `POST`/`PUT`/`PATCH`
     with `POST` fallback when probed with `GET`; `bodyType == None` ->
     `GET`/`HEAD`/`DELETE` with `GET` fallback when probed with `POST`; skips
     `input.type == "mcp"`).
   - Enforces `stellar-sdk >= 16.4.1` and `axios >= 1.20.0`.

3. Sierra tau2-bench `voice-v1` Canonical Task Binding Reload (`PR #673`,
   merged 2026-10-22T19:41:25Z), Atomic Checkpoint Replacement Preserving Prior
   Trajectory on Write Failure (`PR #533`, 2026-10-22T19:24:46Z), and
   Whole-Response Fenced JSON Unwrapping in NL Assertion Judge (`PR #562`,
   2026-10-22T17:26:33Z).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence


CAIP2_CANONICAL_RE = re.compile(r"^[a-z0-9]{3,8}:[-_a-zA-Z0-9]{1,32}$")
REQUIRED_INGRESS_FIELDS = (
    "method",
    "path",
    "query",
    "body",
    "payTo",
    "asset",
    "network",
    "amount",
    "scheme",
)

QUERY_METHODS = frozenset({"GET", "HEAD", "DELETE"})
BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


@dataclass(frozen=True)
class X402IngressIdentityEvaluation:
    allowed: bool
    reason_code: str
    operation_identity: str | None
    captured_artifact_digest: str | None
    signed_content_identifier: str | None
    countersignature_status: str


def _normalize_ingress_member(key: str, value: Any, network: str) -> Any:
    if key == "network":
        return str(value).strip()
    if key in ("payTo", "asset") and str(network).startswith("eip155:"):
        return str(value).lower()
    if key == "method":
        return str(value).upper()
    if key == "body" and isinstance(value, Mapping):
        return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":")))
    return value


def evaluate_x402_ingress_settlement_refusal_identity(
    ingress_snapshot: Mapping[str, Any],
    *,
    absent_fields: Sequence[str] = (),
    destroyed_field_names: Sequence[str] = (),
    coerced_null_or_empty_fields: Sequence[str] = (),
    derived_from_wire_bytes: bool = False,
    downstream_rederived_snapshot: Mapping[str, Any] | None = None,
    outcome_layer_folded_into_identity: bool = False,
    counterparty_observed_snapshot: Mapping[str, Any] | None = None,
    counterparty_missing_observed_bytes: bool = False,
    collapse_absence_into_mismatch: bool = False,
    wire_serialization_a: bytes = b'{"a":1,"b":2}',
    wire_serialization_b: bytes = b'{\n  "b": 2,\n  "a": 1\n}',
    signed_typed_payload: Mapping[str, Any] | None = None,
    collapse_three_artifact_identifiers: bool = False,
) -> X402IngressIdentityEvaluation:
    """Validate x402 §5.5 Settlement and Refusal Identity Invariant (`PR #3776`)."""
    if derived_from_wire_bytes:
        return X402IngressIdentityEvaluation(
            allowed=False,
            reason_code="x402_ingress_identity_wire_encoding_dependent",
            operation_identity=None,
            captured_artifact_digest=None,
            signed_content_identifier=None,
            countersignature_status="rejected",
        )

    if destroyed_field_names or coerced_null_or_empty_fields:
        return X402IngressIdentityEvaluation(
            allowed=False,
            reason_code="x402_ingress_identity_destroyed_or_null_coerced_member",
            operation_identity=None,
            captured_artifact_digest=None,
            signed_content_identifier=None,
            countersignature_status="rejected",
        )

    absent_set = set(absent_fields)
    for field in REQUIRED_INGRESS_FIELDS:
        if field not in absent_set and field not in ingress_snapshot:
            return X402IngressIdentityEvaluation(
                allowed=False,
                reason_code="x402_ingress_identity_incomplete_snapshot",
                operation_identity=None,
                captured_artifact_digest=None,
                signed_content_identifier=None,
                countersignature_status="rejected",
            )

    network = str(ingress_snapshot.get("network", ""))
    if not CAIP2_CANONICAL_RE.match(network):
        return X402IngressIdentityEvaluation(
            allowed=False,
            reason_code="x402_ingress_identity_unnormalized_caip2_network",
            operation_identity=None,
            captured_artifact_digest=None,
            signed_content_identifier=None,
            countersignature_status="rejected",
        )

    normalized_map: dict[str, Any] = {}
    for k in sorted(ingress_snapshot.keys()):
        if k in absent_set:
            continue
        normalized_map[k] = _normalize_ingress_member(k, ingress_snapshot[k], network)

    op_id = hashlib.sha256(
        json.dumps(normalized_map, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()

    if outcome_layer_folded_into_identity:
        return X402IngressIdentityEvaluation(
            allowed=False,
            reason_code="x402_ingress_identity_outcome_layer_folded",
            operation_identity=op_id,
            captured_artifact_digest=None,
            signed_content_identifier=None,
            countersignature_status="rejected",
        )

    if downstream_rederived_snapshot is not None:
        down_map = {
            k: _normalize_ingress_member(k, v, str(downstream_rederived_snapshot.get("network", network)))
            for k, v in sorted(downstream_rederived_snapshot.items())
            if k not in absent_set
        }
        down_id = hashlib.sha256(
            json.dumps(down_map, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if down_id != op_id:
            return X402IngressIdentityEvaluation(
                allowed=False,
                reason_code="x402_ingress_identity_downstream_divergence_prohibited",
                operation_identity=op_id,
                captured_artifact_digest=None,
                signed_content_identifier=None,
                countersignature_status="rejected",
            )

    # Countersignature verification & "Absence is not difference"
    if counterparty_missing_observed_bytes:
        status = (
            "refused_value_mismatch"
            if collapse_absence_into_mismatch
            else "refused_comparison_impossible"
        )
        reason = (
            "x402_countersignature_absence_collapsed_into_mismatch"
            if collapse_absence_into_mismatch
            else "x402_countersignature_refused_comparison_impossible"
        )
        return X402IngressIdentityEvaluation(
            allowed=False,
            reason_code=reason,
            operation_identity=op_id,
            captured_artifact_digest=None,
            signed_content_identifier=None,
            countersignature_status=status,
        )

    if counterparty_observed_snapshot is not None:
        cp_map = {
            k: _normalize_ingress_member(k, v, str(counterparty_observed_snapshot.get("network", network)))
            for k, v in sorted(counterparty_observed_snapshot.items())
            if k not in absent_set
        }
        cp_id = hashlib.sha256(
            json.dumps(cp_map, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if cp_id != op_id:
            return X402IngressIdentityEvaluation(
                allowed=False,
                reason_code="x402_countersignature_refused_value_mismatch",
                operation_identity=op_id,
                captured_artifact_digest=None,
                signed_content_identifier=None,
                countersignature_status="refused_value_mismatch",
            )

    # Three distinct identifiers for signed-artifact references
    cap_a = hashlib.sha256(wire_serialization_a).hexdigest()
    cap_b = hashlib.sha256(wire_serialization_b).hexdigest()
    typed_obj = signed_typed_payload or {"domain": "x402", "amount": str(ingress_snapshot["amount"])}
    signed_content_id = hashlib.sha256(
        json.dumps(typed_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    if collapse_three_artifact_identifiers or cap_a == cap_b or op_id == cap_a:
        return X402IngressIdentityEvaluation(
            allowed=False,
            reason_code="x402_signed_artifact_three_identifiers_collapsed",
            operation_identity=op_id,
            captured_artifact_digest=cap_a,
            signed_content_identifier=signed_content_id,
            countersignature_status="rejected",
        )

    return X402IngressIdentityEvaluation(
        allowed=True,
        reason_code="ok",
        operation_identity=op_id,
        captured_artifact_digest=cap_a,
        signed_content_identifier=signed_content_id,
        countersignature_status="verified",
    )


@dataclass(frozen=True)
class X402MiddlewareAndBazaarEvaluation:
    allowed: bool
    reason_code: str
    rendered_402_body_bytes: bytes
    resolved_bazaar_method: str | None
    bazaar_method_enum: tuple[str, ...]


def evaluate_x402_text_plain_bazaar_method_and_stellar_floor(
    *,
    content_type_header: str = "text/plain; charset=utf-8",
    error_body: str | Mapping[str, Any] = "Payment required.\nPreview line 2.",
    middleware_json_encoded_plain_text: bool = False,
    bazaar_input: Mapping[str, Any] | None = None,
    probe_method: str = "GET",
    advertised_method: str | None = None,
    stellar_sdk_version: tuple[int, int, int] = (16, 4, 1),
    axios_version: tuple[int, int, int] = (1, 20, 0),
) -> X402MiddlewareAndBazaarEvaluation:
    """Validate x402 PR #3901/#3902 (`text/plain` 402 body), PR #3880 (Bazaar method), and PR #3904 (Stellar floor)."""
    if stellar_sdk_version < (16, 4, 1) or axios_version < (1, 20, 0):
        return X402MiddlewareAndBazaarEvaluation(
            allowed=False,
            reason_code="x402_stellar_sdk_or_axios_below_security_floor",
            rendered_402_body_bytes=b"",
            resolved_bazaar_method=None,
            bazaar_method_enum=(),
        )

    media_type = content_type_header.split(";", 1)[0].strip().lower()
    if media_type == "text/plain" and isinstance(error_body, str):
        if middleware_json_encoded_plain_text:
            return X402MiddlewareAndBazaarEvaluation(
                allowed=False,
                reason_code="x402_text_plain_402_body_json_encoded",
                rendered_402_body_bytes=json.dumps(error_body).encode("utf-8"),
                resolved_bazaar_method=None,
                bazaar_method_enum=(),
            )
        rendered_bytes = error_body.encode("utf-8")
    else:
        rendered_bytes = json.dumps(error_body or {}).encode("utf-8")

    if bazaar_input is not None:
        if bazaar_input.get("type") == "mcp":
            return X402MiddlewareAndBazaarEvaluation(
                allowed=True,
                reason_code="ok",
                rendered_402_body_bytes=rendered_bytes,
                resolved_bazaar_method=None,
                bazaar_method_enum=(),
            )
        has_body = bazaar_input.get("bodyType") is not None
        allowed_methods = BODY_METHODS if has_body else QUERY_METHODS
        fallback = "POST" if has_body else "GET"
        p_upper = probe_method.upper()
        expected_method = p_upper if p_upper in allowed_methods else fallback
        actual_method = (advertised_method or expected_method).upper()
        if actual_method != expected_method:
            return X402MiddlewareAndBazaarEvaluation(
                allowed=False,
                reason_code="x402_bazaar_probe_method_mismatches_declared_input_shape",
                rendered_402_body_bytes=rendered_bytes,
                resolved_bazaar_method=actual_method,
                bazaar_method_enum=(actual_method,),
            )
        return X402MiddlewareAndBazaarEvaluation(
            allowed=True,
            reason_code="ok",
            rendered_402_body_bytes=rendered_bytes,
            resolved_bazaar_method=expected_method,
            bazaar_method_enum=(expected_method,),
        )

    return X402MiddlewareAndBazaarEvaluation(
        allowed=True,
        reason_code="ok",
        rendered_402_body_bytes=rendered_bytes,
        resolved_bazaar_method=None,
        bazaar_method_enum=(),
    )


@dataclass(frozen=True)
class Tau2VoiceV1CheckpointAndFenceEvaluation:
    allowed: bool
    reason_code: str
    used_canonical_tasks: bool
    preserved_prior_checkpoint: bool
    parsed_judge_results: tuple[Mapping[str, Any], ...]


def unwrap_tau2_judge_json(response_text: str) -> dict[str, Any]:
    """Reproduce `sierra-research/tau2-bench` PR #562 whole-response fence unwrapping."""
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        lines = response_text.strip().split("\n")
        if (
            len(lines) < 3
            or lines[0].strip(" \t\r") not in ("```json", "```")
            or lines[-1].strip(" \t\r") != "```"
        ):
            raise
        data = json.loads("\n".join(lines[1:-1]))
    if not isinstance(data, dict):
        raise ValueError("Judge JSON root must be an object")
    return data


def evaluate_tau2_voice_v1_checkpoint_and_nl_fence(
    *,
    benchmark_version: str = "voice-v1",
    reload_used_canonical_tasks: bool = True,
    recorded_artifact_pins: Mapping[str, str] = {"retail": "sha256:canon_01"},
    reloaded_artifact_pins: Mapping[str, str] = {"retail": "sha256:canon_01"},
    recorded_task_sha256: str = "sha256:task_42",
    orchestrator_task_sha256: str = "sha256:task_42",
    replacement_write_failed: bool = False,
    deleted_old_trajectory_before_replace: bool = False,
    judge_raw_response: str = '```json\n{"results": [{"expectedOutcome": "confirm", "metExpectation": true, "reasoning": "User wrote ```not JSON``` inside chat."}]}\n```',
) -> Tau2VoiceV1CheckpointAndFenceEvaluation:
    """Validate tau2-bench PR #673 (`voice-v1` canonical reload), PR #533 (atomic checkpoint), and PR #562 (NL fence)."""
    expected_canonical = benchmark_version == "voice-v1"
    if reload_used_canonical_tasks != expected_canonical:
        return Tau2VoiceV1CheckpointAndFenceEvaluation(
            allowed=False,
            reason_code="tau2_voice_v1_canonical_task_reload_flag_mismatch",
            used_canonical_tasks=reload_used_canonical_tasks,
            preserved_prior_checkpoint=True,
            parsed_judge_results=(),
        )

    if dict(reloaded_artifact_pins) != dict(recorded_artifact_pins):
        return Tau2VoiceV1CheckpointAndFenceEvaluation(
            allowed=False,
            reason_code="tau2_voice_v1_published_language_artifacts_drift",
            used_canonical_tasks=reload_used_canonical_tasks,
            preserved_prior_checkpoint=True,
            parsed_judge_results=(),
        )

    if orchestrator_task_sha256 != recorded_task_sha256:
        return Tau2VoiceV1CheckpointAndFenceEvaluation(
            allowed=False,
            reason_code="tau2_voice_v1_task_digest_mismatch",
            used_canonical_tasks=reload_used_canonical_tasks,
            preserved_prior_checkpoint=True,
            parsed_judge_results=(),
        )

    if replacement_write_failed and deleted_old_trajectory_before_replace:
        return Tau2VoiceV1CheckpointAndFenceEvaluation(
            allowed=False,
            reason_code="tau2_checkpoint_replacement_deleted_before_atomic_write",
            used_canonical_tasks=reload_used_canonical_tasks,
            preserved_prior_checkpoint=False,
            parsed_judge_results=(),
        )

    try:
        parsed = unwrap_tau2_judge_json(judge_raw_response)
    except (json.JSONDecodeError, ValueError):
        return Tau2VoiceV1CheckpointAndFenceEvaluation(
            allowed=False,
            reason_code="tau2_nl_judge_malformed_or_non_whole_response_fence",
            used_canonical_tasks=reload_used_canonical_tasks,
            preserved_prior_checkpoint=True,
            parsed_judge_results=(),
        )

    results = tuple(parsed.get("results", ()))
    return Tau2VoiceV1CheckpointAndFenceEvaluation(
        allowed=True,
        reason_code="ok",
        used_canonical_tasks=reload_used_canonical_tasks,
        preserved_prior_checkpoint=True,
        parsed_judge_results=results,
    )
