"""Stage 60 deterministic protocol guards for UCP, ACP, Google AP2, and Sierra tau2-bench 2.0.

Covers:
1. Universal-Commerce-Protocol/ucp PRs #948, #903, #900, #882, #869:
   - Root-array schema anti-pattern prohibition (`"type": "array"` at root of capability,
     extension, or operation payload schemas prevents non-breaking sibling fields, `allOf`
     property composition, and ambient `ucp` member hosting).
   - Order (`dev.ucp.shopping.order`) directional annotation hygiene (no stray
     `"ucp_request": "omit"` on `currency`, `policies`, or `attribution` that strips them from
     OpenAPI 3.1 `order_event_webhook` `requestBody` resolution; no redundant
     `"ucp_response": "optional"` on `payment_terms.json` order overlay).
   - Vendor-specific namespace self-hosting (`com.{vendor}.*`, `org.{org}.*` must be self-hosted
     on the organization's own domain, never in core `dev.ucp.*` repo).
   - User-authentication gate on business-populated stored user state (`buyer`,
     `payment.instruments[]`, `loyalty` require a user-authenticated request and operation
     authorization, returning only the user's own minimized values).
   - Conformance corpus export (`--export-corpus examples.json`) completeness and extension
     schema validation.

2. agentic-commerce-protocol/agentic-commerce-protocol PRs #270, #261, #254, #252:
   - CheckoutSessionCreateRequest and CheckoutSessionUpdateRequest `line_items` reference
     alignment to `#/components/schemas/LineItem` (requiring `id`, nested `item`, `quantity >= 1`,
     and `totals[]` rather than bare `Item`).
   - `DelegateAuthenticationSessionWithResult` flat `type: object` schema with
     `additionalProperties: false` (eliminating the unsatisfiable `allOf` over
     `DelegateAuthenticationSessionBase` that rejected `authentication_result`).
   - Full consistency validation across `agentic_checkout`, `delegate_authentication`,
     `delegate_payment`, and `feed` examples, embedded `$defs`/`components.schemas` examples,
     and OpenAPI `requestBody`/`responses` inline `$ref` examples.

3. google-agentic-commerce/AP2 PRs #349, #333, #329, #351, #365, #364:
   - Exact versioned VCT constants (`mandate.payment.open.1`, `mandate.checkout.open.1`,
     `mandate.payment.1`, `mandate.checkout.1`).
   - `PaymentInstrument` type-specific extension field preservation (`additionalProperties: true` /
     `ConfigDict(extra='allow')` so x402 `payee_address` and `facilitator` survive signing).
   - `~~`-first multi-hop dSD-JWT delegation chain splitting (preventing hop 1 from being misread
     as hop 0's trailing `kbJwt` and dropping hop 1 disclosures).
   - `ReceiptClient.verify_receipt` acceptance of both raw EC public keys (`JWK.from_pyca`) and
     `JWK`, verifying signatures before invoking `has_reference_in_store_cb`.
   - Redaction of sensitive payment tokens, mandates, `risk_data`, and prompts from MCP/A2A logs.

4. sierra-research/tau2-bench PRs #636, #619, #616, #645, #632:
   - ElevenLabs Voice Design API-unit `guidance_scale` (`default=5`, valid API range `1..20`,
     rejecting UI slider percentage `38` which degrades benchmark performance by up to 10%).
   - Unpinned `data/tau2/voice_design/<lang>.yaml` for all 6 `voice-v2` languages
     (`en`, `es`, `pt`, `hi`, `zh`, `ko`) with `eleven_ttv_v3` personas without polluting
     `pack_sha256` pins.
   - Inline text-matrix `results.json` file-path resolution in `export_submission` (preventing
     directory-path `voice` layout detection from dropping all inline `text-v1` trials).
   - Domain `reward_basis` `RewardType.ACTION` ground truth (`32` telecom tasks and `9`
     `banking_knowledge` tasks use `ACTION`; `0` in airline/retail) and bounded single-attempt
     `factory_draft_repair` (`repair_attempts <= 1`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


UCP_FORBIDDEN_ROOT_ARRAY_CATEGORIES: frozenset[str] = frozenset(
    {"capability", "extension", "operation_payload"}
)
UCP_ORDER_REQUIRED_SNAPSHOT_FIELDS: frozenset[str] = frozenset(
    {"id", "checkout_id", "currency", "line_items", "totals", "policies", "attribution"}
)
UCP_STORED_USER_STATE_FIELDS: frozenset[str] = frozenset(
    {"buyer", "payment.instruments", "loyalty"}
)

ACP_DELEGATE_AUTH_VALID_STATUSES: frozenset[str] = frozenset(
    {
        "action_required",
        "pending",
        "not_supported",
        "authenticated",
        "attempted",
        "not_authenticated",
        "rejected",
        "unavailable",
        "expired",
        "challenge_abandoned",
    }
)
ACP_REQUIRED_EXAMPLE_SPECS: frozenset[str] = frozenset(
    {"agentic_checkout", "delegate_authentication", "delegate_payment", "feed"}
)

AP2_VERSIONED_VCT_BY_MODEL: Mapping[str, str] = {
    "OpenPaymentMandate": "mandate.payment.open.1",
    "OpenCheckoutMandate": "mandate.checkout.open.1",
    "PaymentMandate": "mandate.payment.1",
    "CheckoutMandate": "mandate.checkout.1",
}

TAU2_VOICE_V2_LANGUAGES: frozenset[str] = frozenset({"en", "es", "pt", "hi", "zh", "ko"})
TAU2_EXPECTED_ACTION_TASK_COUNTS: Mapping[str, int] = {
    "airline": 0,
    "retail": 0,
    "telecom": 32,
    "banking_knowledge": 9,
}


@dataclass(frozen=True)
class UcpRootArrayOrderAndAuthStateGuardResult:
    """Result of validating UCP PRs #948, #903, #900, #882, and #869."""

    allowed: bool
    decision_code: str
    schema_name: str
    root_schema_type: str
    order_webhook_preserved_fields: tuple[str, ...]
    reason: str


def verify_ucp_root_array_order_annotations_and_auth_state(
    *,
    schema_name: str,
    schema_category: str,
    root_schema_type: str,
    is_core_ucp_repo_submission: bool = True,
    order_field_ucp_request_annotations: Mapping[str, str] | None = None,
    order_payment_terms_ucp_response_annotation: str | None = None,
    order_event_webhook_resolved_fields: Sequence[str] = (
        "id",
        "checkout_id",
        "currency",
        "line_items",
        "totals",
        "policies",
        "attribution",
    ),
    populated_stored_user_fields: Sequence[str] = (),
    is_user_authenticated: bool = True,
    is_authorized_for_operation: bool = True,
    belongs_to_authenticated_user: bool = True,
    corpus_example_is_complete: bool = True,
    corpus_example_extension_validated: bool = True,
) -> UcpRootArrayOrderAndAuthStateGuardResult:
    """Validate UCP root-array prohibition, Order directional annotations, vendor self-hosting, and auth state."""
    normalized_name = schema_name.strip()
    normalized_category = schema_category.strip().lower()
    normalized_root_type = root_schema_type.strip().lower()
    preserved_fields = tuple(str(f).strip() for f in order_event_webhook_resolved_fields)

    # 1. PR #882: Vendor-specific capabilities/extensions/handlers must be self-hosted
    if is_core_ucp_repo_submission and not normalized_name.startswith("dev.ucp."):
        return UcpRootArrayOrderAndAuthStateGuardResult(
            allowed=False,
            decision_code="UCP_VENDOR_EXTENSION_MUST_BE_SELF_HOSTED",
            schema_name=normalized_name,
            root_schema_type=normalized_root_type,
            order_webhook_preserved_fields=preserved_fields,
            reason=(
                f"Schema '{normalized_name}' uses a vendor/organization namespace outside 'dev.ucp.*' "
                "and must be self-hosted on the organization's own domain (PR #882)."
            ),
        )

    # 2. PR #948: Capability, extension, and operation payload schemas MUST NOT use root array
    if (
        normalized_category in UCP_FORBIDDEN_ROOT_ARRAY_CATEGORIES
        and normalized_root_type == "array"
    ):
        return UcpRootArrayOrderAndAuthStateGuardResult(
            allowed=False,
            decision_code="UCP_ROOT_ARRAY_SCHEMA_FORBIDDEN",
            schema_name=normalized_name,
            root_schema_type=normalized_root_type,
            order_webhook_preserved_fields=preserved_fields,
            reason=(
                f"Schema '{normalized_name}' ({normalized_category}) declares root 'type: array', "
                "which prevents non-breaking sibling fields, allOf property composition, and "
                "the ambient 'ucp' object member (PR #948)."
            ),
        )

    # 3. PR #903: Order schema must not carry stray ucp_request annotations or strip webhook fields
    annotations = dict(order_field_ucp_request_annotations or {})
    if annotations:
        return UcpRootArrayOrderAndAuthStateGuardResult(
            allowed=False,
            decision_code="UCP_ORDER_STRAY_DIRECTIONAL_ANNOTATION_FORBIDDEN",
            schema_name=normalized_name,
            root_schema_type=normalized_root_type,
            order_webhook_preserved_fields=preserved_fields,
            reason=(
                f"Order schema contains stray ucp_request annotations {annotations} that strip "
                "fields during OpenAPI order_event_webhook requestBody resolution (PR #903)."
            ),
        )

    if order_payment_terms_ucp_response_annotation is not None:
        return UcpRootArrayOrderAndAuthStateGuardResult(
            allowed=False,
            decision_code="UCP_ORDER_STRAY_DIRECTIONAL_ANNOTATION_FORBIDDEN",
            schema_name=normalized_name,
            root_schema_type=normalized_root_type,
            order_webhook_preserved_fields=preserved_fields,
            reason=(
                "payment_terms.json order overlay must not carry redundant "
                f"ucp_response='{order_payment_terms_ucp_response_annotation}' annotation (PR #903)."
            ),
        )

    missing_webhook_fields = UCP_ORDER_REQUIRED_SNAPSHOT_FIELDS.difference(preserved_fields)
    if missing_webhook_fields:
        return UcpRootArrayOrderAndAuthStateGuardResult(
            allowed=False,
            decision_code="UCP_ORDER_WEBHOOK_REQUIRED_FIELDS_STRIPPED",
            schema_name=normalized_name,
            root_schema_type=normalized_root_type,
            order_webhook_preserved_fields=preserved_fields,
            reason=(
                "order_event_webhook payload is missing required Order snapshot fields: "
                f"{sorted(missing_webhook_fields)} (PR #903)."
            ),
        )

    # 4. PR #869: Stored user-specific state requires user-authenticated request & ownership
    populated_set = {str(f).strip() for f in populated_stored_user_fields if str(f).strip()}
    if populated_set.intersection(UCP_STORED_USER_STATE_FIELDS):
        if not (
            is_user_authenticated
            and is_authorized_for_operation
            and belongs_to_authenticated_user
        ):
            return UcpRootArrayOrderAndAuthStateGuardResult(
                allowed=False,
                decision_code="UCP_UNAUTHENTICATED_STORED_USER_STATE_LEAK_FORBIDDEN",
                schema_name=normalized_name,
                root_schema_type=normalized_root_type,
                order_webhook_preserved_fields=preserved_fields,
                reason=(
                    f"Business-populated stored user state {sorted(populated_set)} cannot be "
                    "returned unless the request is user-authenticated, authorized, and scoped "
                    "to the authenticated user's own data (PR #869)."
                ),
            )

    # 5. PR #900: Exported conformance corpus examples must be complete and extension-validated
    if not corpus_example_is_complete or not corpus_example_extension_validated:
        return UcpRootArrayOrderAndAuthStateGuardResult(
            allowed=False,
            decision_code="UCP_CONFORMANCE_CORPUS_INCOMPLETE_OR_EXTENSION_INVALID",
            schema_name=normalized_name,
            root_schema_type=normalized_root_type,
            order_webhook_preserved_fields=preserved_fields,
            reason=(
                "Documentation examples exported to examples.json conformance corpus must be "
                "complete (non-elided) and validated against composed extension schemas (PR #900)."
            ),
        )

    return UcpRootArrayOrderAndAuthStateGuardResult(
        allowed=True,
        decision_code="UCP_ROOT_ARRAY_ORDER_AND_AUTH_STATE_VERIFIED",
        schema_name=normalized_name,
        root_schema_type=normalized_root_type,
        order_webhook_preserved_fields=preserved_fields,
        reason=(
            "UCP root-object schema rule, Order webhook directional hygiene, dev.ucp.* namespace "
            "boundary, auth-gated user state, and conformance corpus validation verified."
        ),
    )


@dataclass(frozen=True)
class AcpCheckoutLineItemAndDelegateAuthResultGuardResult:
    """Result of validating ACP PRs #270, #261, #254, and #252."""

    allowed: bool
    decision_code: str
    create_request_line_items_ref: str
    update_request_line_items_ref: str
    delegate_auth_status: str
    reason: str


def verify_acp_checkout_line_item_and_delegate_auth_result(
    *,
    create_request_line_items_ref: str,
    update_request_line_items_ref: str,
    request_line_items: Sequence[Mapping[str, Any]],
    delegate_auth_schema_uses_unsatisfiable_allof: bool = False,
    delegate_auth_session_payload: Mapping[str, Any] | None = None,
    mapped_example_specs: Sequence[str] = (
        "agentic_checkout",
        "delegate_authentication",
        "delegate_payment",
        "feed",
    ),
    embedded_schema_examples_validated: bool = True,
    openapi_inline_ref_examples_validated: bool = True,
) -> AcpCheckoutLineItemAndDelegateAuthResultGuardResult:
    """Validate ACP LineItem request schema alignment, DelegateAuthenticationSessionWithResult, and CI validators."""
    create_ref = create_request_line_items_ref.strip()
    update_ref = update_request_line_items_ref.strip()
    expected_ref = "#/components/schemas/LineItem"

    # 1. PR #270: CheckoutSessionCreateRequest and CheckoutSessionUpdateRequest must reference LineItem
    if create_ref != expected_ref or update_ref != expected_ref:
        return AcpCheckoutLineItemAndDelegateAuthResultGuardResult(
            allowed=False,
            decision_code="ACP_CHECKOUT_REQUEST_LINE_ITEM_SCHEMA_MISMATCH",
            create_request_line_items_ref=create_ref,
            update_request_line_items_ref=update_ref,
            delegate_auth_status="",
            reason=(
                f"Checkout request line_items must reference '{expected_ref}' (got "
                f"create='{create_ref}', update='{update_ref}') to preserve quantity (PR #270)."
            ),
        )

    if not request_line_items:
        return AcpCheckoutLineItemAndDelegateAuthResultGuardResult(
            allowed=False,
            decision_code="ACP_CHECKOUT_REQUEST_LINE_ITEM_SCHEMA_MISMATCH",
            create_request_line_items_ref=create_ref,
            update_request_line_items_ref=update_ref,
            delegate_auth_status="",
            reason="Checkout request line_items must contain at least 1 LineItem entry (PR #270).",
        )

    for idx, entry in enumerate(request_line_items):
        item_obj = entry.get("item")
        quantity = entry.get("quantity")
        totals = entry.get("totals")
        if (
            not isinstance(entry.get("id"), str)
            or not entry["id"].strip()
            or not isinstance(item_obj, Mapping)
            or not isinstance(item_obj.get("id"), str)
            or not isinstance(item_obj.get("unit_amount"), int)
            or not isinstance(quantity, int)
            or quantity < 1
            or not isinstance(totals, Sequence)
            or len(totals) == 0
        ):
            return AcpCheckoutLineItemAndDelegateAuthResultGuardResult(
                allowed=False,
                decision_code="ACP_CHECKOUT_REQUEST_LINE_ITEM_SCHEMA_MISMATCH",
                create_request_line_items_ref=create_ref,
                update_request_line_items_ref=update_ref,
                delegate_auth_status="",
                reason=(
                    f"line_items[{idx}] uses flat Item shape or is missing required LineItem "
                    "fields (id, nested item.{id,unit_amount}, quantity>=1, totals[]) (PR #270)."
                ),
            )

    # 2. PR #261: DelegateAuthenticationSessionWithResult flat object schema validation
    auth_payload = dict(delegate_auth_session_payload or {})
    auth_status = str(auth_payload.get("status", "")).strip()
    auth_session_id = str(auth_payload.get("authentication_session_id", "")).strip()
    allowed_keys = {"authentication_session_id", "status", "action", "authentication_result"}
    extra_keys = set(auth_payload.keys()).difference(allowed_keys)

    if (
        delegate_auth_schema_uses_unsatisfiable_allof
        or not auth_session_id
        or auth_status not in ACP_DELEGATE_AUTH_VALID_STATUSES
        or extra_keys
    ):
        return AcpCheckoutLineItemAndDelegateAuthResultGuardResult(
            allowed=False,
            decision_code="ACP_DELEGATE_AUTH_RESULT_SCHEMA_UNSATISFIABLE_OR_INVALID",
            create_request_line_items_ref=create_ref,
            update_request_line_items_ref=update_ref,
            delegate_auth_status=auth_status,
            reason=(
                "DelegateAuthenticationSessionWithResult must use flat object schema with "
                "additionalProperties: false, valid authentication_session_id/status, and "
                f"optional action/authentication_result (extra_keys={sorted(extra_keys)}) (PR #261)."
            ),
        )

    if "authentication_result" in auth_payload:
        auth_res = auth_payload["authentication_result"]
        if not isinstance(auth_res, Mapping) or not str(auth_res.get("outcome", "")).strip():
            return AcpCheckoutLineItemAndDelegateAuthResultGuardResult(
                allowed=False,
                decision_code="ACP_DELEGATE_AUTH_RESULT_SCHEMA_UNSATISFIABLE_OR_INVALID",
                create_request_line_items_ref=create_ref,
                update_request_line_items_ref=update_ref,
                delegate_auth_status=auth_status,
                reason="authentication_result must be an AuthenticationResult object with non-empty outcome (PR #261).",
            )

    # 3. PRs #261, #254, #252: Example consistency validators across all 4 specs, embedded & inline examples
    spec_set = {str(s).strip() for s in mapped_example_specs}
    if (
        not ACP_REQUIRED_EXAMPLE_SPECS.issubset(spec_set)
        or not embedded_schema_examples_validated
        or not openapi_inline_ref_examples_validated
    ):
        return AcpCheckoutLineItemAndDelegateAuthResultGuardResult(
            allowed=False,
            decision_code="ACP_UNVALIDATED_INLINE_OR_EMBEDDED_SCHEMA_EXAMPLE",
            create_request_line_items_ref=create_ref,
            update_request_line_items_ref=update_ref,
            delegate_auth_status=auth_status,
            reason=(
                "validate-consistency.js must map all 4 ACP specs and validate both embedded "
                "$defs/components.schemas examples and OpenAPI inline $ref examples (PRs #261, #254, #252)."
            ),
        )

    return AcpCheckoutLineItemAndDelegateAuthResultGuardResult(
        allowed=True,
        decision_code="ACP_CHECKOUT_LINE_ITEM_AND_DELEGATE_AUTH_RESULT_VERIFIED",
        create_request_line_items_ref=create_ref,
        update_request_line_items_ref=update_ref,
        delegate_auth_status=auth_status,
        reason=(
            "ACP Checkout LineItem schema references, flat DelegateAuthenticationSessionWithResult "
            "schema, and inline/embedded example validators verified."
        ),
    )


@dataclass(frozen=True)
class Ap2VctInstrumentExtensionsAndChainDecoderGuardResult:
    """Result of validating Google AP2 PRs #349, #333, #329, #351, #365, and #364."""

    allowed: bool
    decision_code: str
    mandate_model: str
    vct_value: str
    decoded_hop_count: int
    preserved_extension_keys: tuple[str, ...]
    reason: str


def verify_ap2_vct_instrument_extensions_and_chain_decoder(
    *,
    mandate_model: str,
    vct_value: str,
    payment_instrument_input_extensions: Mapping[str, Any],
    payment_instrument_signed_dump: Mapping[str, Any],
    dsd_jwt_token: str,
    split_double_tilde_first: bool = True,
    receipt_public_key_format: str = "ec_public_key",
    receipt_signature_valid: bool = True,
    reference_callback_invoked_before_sig_verify: bool = False,
    logs_contain_sensitive_payment_artifacts: bool = False,
    mcp_logging_include_payloads: bool = False,
) -> Ap2VctInstrumentExtensionsAndChainDecoderGuardResult:
    """Validate AP2 versioned VCTs, PaymentInstrument extensions, ~~ chain decoding, EC receipt keys, and redaction."""
    model_name = mandate_model.strip()
    vct = vct_value.strip()
    expected_vct = AP2_VERSIONED_VCT_BY_MODEL.get(model_name)

    # 1. PR #349: Exact versioned VCT constant check
    if expected_vct is None or vct != expected_vct:
        return Ap2VctInstrumentExtensionsAndChainDecoderGuardResult(
            allowed=False,
            decision_code="AP2_UNVERSIONED_OR_INVALID_MANDATE_VCT",
            mandate_model=model_name,
            vct_value=vct,
            decoded_hop_count=0,
            preserved_extension_keys=(),
            reason=(
                f"Mandate model '{model_name}' requires exact versioned VCT '{expected_vct}', "
                f"got '{vct}' (PR #349)."
            ),
        )

    # 2. PRs #333 & #329: PaymentInstrument extension fields must survive model_dump() and signing
    missing_ext = [
        k
        for k, v in payment_instrument_input_extensions.items()
        if payment_instrument_signed_dump.get(k) != v
    ]
    preserved_keys = tuple(
        sorted(
            k
            for k in payment_instrument_input_extensions
            if k in payment_instrument_signed_dump
            and payment_instrument_signed_dump[k] == payment_instrument_input_extensions[k]
        )
    )
    if missing_ext:
        return Ap2VctInstrumentExtensionsAndChainDecoderGuardResult(
            allowed=False,
            decision_code="AP2_PAYMENT_INSTRUMENT_EXTENSION_FIELDS_DROPPED",
            mandate_model=model_name,
            vct_value=vct,
            decoded_hop_count=0,
            preserved_extension_keys=preserved_keys,
            reason=(
                "PaymentInstrument dropped type-specific extension fields during serialization/signing: "
                f"{missing_ext}; requires additionalProperties: true / ConfigDict(extra='allow') (PRs #333, #329)."
            ),
        )

    # 3. PR #351: dSD-JWT delegation chain must split on '~~' before single '~'
    raw_token = dsd_jwt_token.strip()
    hop_tokens = [h for h in raw_token.split("~~") if h]
    if len(hop_tokens) > 1 and not split_double_tilde_first:
        return Ap2VctInstrumentExtensionsAndChainDecoderGuardResult(
            allowed=False,
            decision_code="AP2_DSDJWT_CHAIN_SINGLE_TILDE_SPLIT_CORRUPTION",
            mandate_model=model_name,
            vct_value=vct,
            decoded_hop_count=1,
            preserved_extension_keys=preserved_keys,
            reason=(
                "Splitting a multi-hop dSD-JWT delegation chain on single '~' before '~~' "
                "misreads hop 1 as hop 0's trailing KB-JWT and drops hop 1 disclosures (PR #351)."
            ),
        )

    # 4. PR #365: ReceiptClient.verify_receipt accepts ec_public_key (via JWK.from_pyca) or jwk
    # and must never invoke has_reference_in_store_cb before verifying the signature
    if (
        receipt_public_key_format not in {"ec_public_key", "jwk"}
        or not receipt_signature_valid
        or reference_callback_invoked_before_sig_verify
    ):
        return Ap2VctInstrumentExtensionsAndChainDecoderGuardResult(
            allowed=False,
            decision_code="AP2_RECEIPT_KEY_FORMAT_OR_CALLBACK_ORDER_INVALID",
            mandate_model=model_name,
            vct_value=vct,
            decoded_hop_count=len(hop_tokens),
            preserved_extension_keys=preserved_keys,
            reason=(
                "ReceiptClient.verify_receipt must accept ec.EllipticCurvePublicKey (via JWK.from_pyca) "
                "or JWK and reject invalid signatures before calling has_reference_in_store_cb (PR #365)."
            ),
        )

    # 5. PR #364: Sensitive payment artifacts must never be written to logs
    if logs_contain_sensitive_payment_artifacts or mcp_logging_include_payloads:
        return Ap2VctInstrumentExtensionsAndChainDecoderGuardResult(
            allowed=False,
            decision_code="AP2_SENSITIVE_PAYMENT_ARTIFACT_LOG_LEAK",
            mandate_model=model_name,
            vct_value=vct,
            decoded_hop_count=len(hop_tokens),
            preserved_extension_keys=preserved_keys,
            reason=(
                "MCP/A2A servers and payment processors must disable include_payloads=True and "
                "redact payment tokens, checkout mandates, risk_data, and user prompts from logs (PR #364)."
            ),
        )

    return Ap2VctInstrumentExtensionsAndChainDecoderGuardResult(
        allowed=True,
        decision_code="AP2_VCT_INSTRUMENT_EXTENSIONS_AND_CHAIN_DECODER_VERIFIED",
        mandate_model=model_name,
        vct_value=vct,
        decoded_hop_count=len(hop_tokens),
        preserved_extension_keys=preserved_keys,
        reason=(
            "AP2 versioned VCTs, PaymentInstrument extension preservation, '~~' multi-hop chain "
            "decoding, EC/JWK receipt verification, and log redaction verified."
        ),
    )


@dataclass(frozen=True)
class Tau2VoiceDesignScaleAndTextMatrixGuardResult:
    """Result of validating Sierra tau2-bench PRs #636, #619, #616, #645, and #632."""

    allowed: bool
    decision_code: str
    guidance_scale_api_value: int
    counted_inline_text_trials: int
    voice_design_languages: tuple[str, ...]
    reason: str


def verify_tau2_voice_design_scale_and_text_matrix_inline(
    *,
    guidance_scale_api_value: int = 5,
    voice_design_languages: Sequence[str] = ("en", "es", "pt", "hi", "zh", "ko"),
    voice_design_stored_outside_pinned_pack: bool = True,
    voice_design_model: str = "eleven_ttv_v3",
    export_submission_passes_results_json_file: bool = True,
    expected_inline_text_trials: int = 6,
    counted_inline_text_trials: int = 6,
    reported_action_task_counts: Mapping[str, int] | None = None,
    factory_draft_repair_attempts: int = 1,
) -> Tau2VoiceDesignScaleAndTextMatrixGuardResult:
    """Validate tau2-bench 2.0 Voice Design API scale, unpinned voice_design YAMLs, inline text trials, and ACTION counts."""
    langs = tuple(sorted({str(lang).strip() for lang in voice_design_languages if str(lang).strip()}))

    # 1. PR #636: ElevenLabs Voice Design guidance_scale must use API units (default 5, range 1..20), not UI 38%
    if guidance_scale_api_value < 1 or guidance_scale_api_value > 20:
        return Tau2VoiceDesignScaleAndTextMatrixGuardResult(
            allowed=False,
            decision_code="TAU2_VOICE_DESIGN_UI_PERCENTAGE_SENT_AS_API_SCALE",
            guidance_scale_api_value=guidance_scale_api_value,
            counted_inline_text_trials=counted_inline_text_trials,
            voice_design_languages=langs,
            reason=(
                f"setup_voices sent guidance_scale={guidance_scale_api_value} (e.g. UI slider 38%) "
                "outside valid ElevenLabs API units (default 5, range 1..20), producing slow, "
                "pause-heavy voices that skew benchmark performance by up to 10% (PR #636)."
            ),
        )

    # 2. PR #619: data/tau2/voice_design/<lang>.yaml for all 6 voice-v2 languages outside pack_sha256 pins
    if (
        set(langs) != TAU2_VOICE_V2_LANGUAGES
        or not voice_design_stored_outside_pinned_pack
        or voice_design_model.strip() != "eleven_ttv_v3"
    ):
        return Tau2VoiceDesignScaleAndTextMatrixGuardResult(
            allowed=False,
            decision_code="TAU2_VOICE_DESIGN_YAML_MISSING_OR_POLLUTES_PACK_PIN",
            guidance_scale_api_value=guidance_scale_api_value,
            counted_inline_text_trials=counted_inline_text_trials,
            voice_design_languages=langs,
            reason=(
                "voice_design/<lang>.yaml must cover all 6 voice-v2 languages (en, es, pt, hi, zh, ko) "
                "with model 'eleven_ttv_v3' in an unpinned directory outside data/tau2/multilingual/ (PR #619)."
            ),
        )

    # 3. PR #616: export_submission must pass results.json file path (not cell directory) so inline text trials are counted
    if (
        not export_submission_passes_results_json_file
        or (expected_inline_text_trials > 0 and counted_inline_text_trials != expected_inline_text_trials)
    ):
        return Tau2VoiceDesignScaleAndTextMatrixGuardResult(
            allowed=False,
            decision_code="TAU2_TEXT_MATRIX_DIRECTORY_PATH_DROPS_INLINE_TRIALS",
            guidance_scale_api_value=guidance_scale_api_value,
            counted_inline_text_trials=counted_inline_text_trials,
            voice_design_languages=langs,
            reason=(
                "Passing cell directory instead of cell/results.json triggers voice layout detection "
                f"and drops inline text-matrix simulations (counted={counted_inline_text_trials}, "
                f"expected={expected_inline_text_trials}) (PR #616)."
            ),
        )

    # 4. PRs #645 & #632: Telecom has 32 ACTION tasks, banking_knowledge has 9, and factory repair is bounded to <= 1 attempt
    action_counts = dict(reported_action_task_counts or TAU2_EXPECTED_ACTION_TASK_COUNTS)
    if (
        action_counts != dict(TAU2_EXPECTED_ACTION_TASK_COUNTS)
        or factory_draft_repair_attempts < 0
        or factory_draft_repair_attempts > 1
    ):
        return Tau2VoiceDesignScaleAndTextMatrixGuardResult(
            allowed=False,
            decision_code="TAU2_REWARD_BASIS_OR_UNBOUNDED_REPAIR_INVALID",
            guidance_scale_api_value=guidance_scale_api_value,
            counted_inline_text_trials=counted_inline_text_trials,
            voice_design_languages=langs,
            reason=(
                f"RewardType.ACTION task counts {action_counts} must match {dict(TAU2_EXPECTED_ACTION_TASK_COUNTS)} "
                f"(PR #645) and factory_draft_repair attempts ({factory_draft_repair_attempts}) must be <= 1 (PR #632)."
            ),
        )

    return Tau2VoiceDesignScaleAndTextMatrixGuardResult(
        allowed=True,
        decision_code="TAU2_VOICE_DESIGN_SCALE_AND_TEXT_MATRIX_VERIFIED",
        guidance_scale_api_value=guidance_scale_api_value,
        counted_inline_text_trials=counted_inline_text_trials,
        voice_design_languages=langs,
        reason=(
            "tau2-bench 2.0 Voice Design API guidance_scale=5, unpinned 6-language voice_design YAMLs, "
            "inline text-matrix results.json trial counting, and telecom ACTION reward_basis verified."
        ),
    )
