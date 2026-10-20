"""Stage 110 deterministic protocol guardrails:
1. UCP (#659, #657, #655, #653): Order webhook `webhook-id` & `webhook-timestamp` signature gate,
   ambient `ucp` namespace with `map_order` & `request_constraints`, and `quantity_unit` sale-basis steps.
2. ACP (#118, #114, #100, #99): `MessageError.type == "intervention_required"`, `dev.acp.seller_backed.*`
   payment handlers (`saved_card`, `gift_card`, `points`, `store_credit`), and `version_mismatch` `supported_versions`.
3. Google AP2 (#377, #378) + Coinbase x402 (#317): ISO 4217 `Decimal` `payment.budget.max` minor-unit conversion,
   chronological ISO 8601 `execution_date` window comparison, and x402 `no-wallet` extension anti-lock-in & shell-exec guard.
4. Sierra tau2-bench (#651, #634, #611): `voice-v2-banking`/`voice-v2-entity` package suffix & no-judge gate,
   `log_verification` `time_verified` canonicalization, and active-line enforcement for `refuel_data`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
import re
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class Stage110GuardResult:
    allowed: bool
    decision_code: str
    detail: str
    metadata: dict[str, Any]


_ALLOWED_UCP_MEMBERS = frozenset({"version", "capabilities", "services", "payment_handlers", "map_order", "request_constraints"})
_ALLOWED_REQUEST_CONSTRAINT_KEYS = frozenset({"required", "properties", "enum", "const"})


def validate_ucp_webhook_sig_namespace_and_quantity_unit_guard(
    payload: Mapping[str, Any],
) -> Stage110GuardResult:
    """Validate UCP #659 webhook signing gate, #657/#655 ambient `ucp` namespace, and #653 `quantity_unit` steps."""
    # 1. #659: webhook-id and webhook-timestamp must be covered in Signature-Input when present
    webhook = payload.get("order_webhook", {})
    if isinstance(webhook, Mapping) and webhook:
        headers = {str(k).lower(): str(v) for k, v in webhook.get("headers", {}).items()}
        sig_input = str(webhook.get("signature_input", "")).lower()
        for required_hdr in ("webhook-id", "webhook-timestamp"):
            if required_hdr in headers and f'"{required_hdr}"' not in sig_input:
                return Stage110GuardResult(
                    False,
                    "UCP_WEBHOOK_HEADER_UNSIGNED_REJECTED",
                    f"Order webhook carrying `{required_hdr}` must cover `{required_hdr}` in Signature-Input (#659).",
                    {"missing_signed_component": required_hdr},
                )

    # 2. #657 & #655: ambient `ucp` namespace, `map_order`, and `request_constraints`
    ucp_env = payload.get("ucp", {})
    if not isinstance(ucp_env, Mapping):
        return Stage110GuardResult(
            False,
            "UCP_NAMESPACE_INVALID",
            "Ambient `ucp` member must be a JSON object (#657).",
            {},
        )
    unknown_members = set(ucp_env.keys()) - _ALLOWED_UCP_MEMBERS
    if unknown_members:
        return Stage110GuardResult(
            False,
            "UCP_UNREGISTERED_NAMESPACE_MEMBER_REJECTED",
            "Ambient `ucp` object contains unregistered vocabulary members (#657).",
            {"unknown_members": sorted(unknown_members)},
        )

    for reg_name in ("payment_handlers", "services", "capabilities"):
        reg_obj = ucp_env.get(reg_name, {})
        if isinstance(reg_obj, Mapping) and ("ucp" in reg_obj or "map_order" in reg_obj):
            return Stage110GuardResult(
                False,
                "UCP_RESERVED_KEY_IN_REGISTRY_REJECTED",
                "Reserved protocol names `ucp` and `map_order` are forbidden as registry keys (#657).",
                {"registry": reg_name},
            )

    req_constraints = ucp_env.get("request_constraints")
    submitted_input = payload.get("submitted_request", {})
    if isinstance(req_constraints, Mapping):
        bad_kw = set(req_constraints.keys()) - _ALLOWED_REQUEST_CONSTRAINT_KEYS
        if bad_kw:
            return Stage110GuardResult(
                False,
                "UCP_REQUEST_CONSTRAINTS_GRAMMAR_VIOLATION",
                "`ucp.request_constraints` only permits closed keywords `required`, `properties`, `enum`, `const` (#655).",
                {"invalid_keywords": sorted(bad_kw)},
            )
        req_fields = req_constraints.get("required", [])
        if isinstance(req_fields, Sequence) and isinstance(submitted_input, Mapping):
            for field in req_fields:
                if field not in submitted_input or submitted_input[field] in (None, ""):
                    return Stage110GuardResult(
                        False,
                        "UCP_REQUEST_CONSTRAINT_REQUIRED_FIELD_MISSING",
                        f"Transaction-specific `ucp.request_constraints` requires `{field}` (#655).",
                        {"missing_field": str(field)},
                    )
        prop_constraints = req_constraints.get("properties", {})
        if isinstance(prop_constraints, Mapping) and isinstance(submitted_input, Mapping):
            for prop_name, rule in prop_constraints.items():
                if isinstance(rule, Mapping) and "const" in rule:
                    if submitted_input.get(prop_name) != rule["const"]:
                        return Stage110GuardResult(
                            False,
                            "UCP_REQUEST_CONSTRAINT_CONST_VIOLATION",
                            f"Field `{prop_name}` violated `ucp.request_constraints` const value (#655).",
                            {"field": str(prop_name), "expected": rule["const"], "actual": submitted_input.get(prop_name)},
                        )

    # 3. #653: sale-basis steps for quantities (`quantity_unit`)
    line_item = payload.get("line_item", {})
    if isinstance(line_item, Mapping) and line_item:
        qty = line_item.get("quantity")
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            return Stage110GuardResult(
                False,
                "UCP_QUANTITY_STEP_NON_INTEGER_REJECTED",
                "Line item `quantity` must be a positive integer count of sale-basis steps (#653).",
                {"quantity": qty},
            )
        item = line_item.get("item", {})
        price = item.get("price", 0)
        q_unit = item.get("quantity_unit")
        scale = 0
        if isinstance(q_unit, Mapping):
            unit_code = str(q_unit.get("unit", ""))
            scale = int(q_unit.get("scale", 0))
            display_text = str(q_unit.get("display_text", "")).strip()
            if not unit_code or not display_text or scale < 0:
                return Stage110GuardResult(
                    False,
                    "UCP_QUANTITY_UNIT_DESCRIPTOR_INVALID",
                    "`quantity_unit` requires non-empty `unit`, `display_text`, and non-negative integer `scale` (#653).",
                    {"quantity_unit": dict(q_unit)},
                )
            if unit_code == "C62" and scale != 0:
                return Stage110GuardResult(
                    False,
                    "UCP_EACH_UNIT_NONZERO_SCALE_REJECTED",
                    "UN/CEFACT `C62` (`each`) cannot use a nonzero `scale` (#653).",
                    {"unit": unit_code, "scale": scale},
                )
        expected_total = int(
            (Decimal(str(price)) * Decimal(str(qty)) * (Decimal(10) ** Decimal(-scale))).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        declared_total = line_item.get("declared_total_minor")
        if declared_total is not None and int(declared_total) != expected_total:
            return Stage110GuardResult(
                False,
                "UCP_SALE_BASIS_LINE_TOTAL_MISMATCH",
                "Line total does not match `round(price * quantity * 10^-scale)` (#653).",
                {"expected_total_minor": expected_total, "declared_total_minor": declared_total},
            )

    return Stage110GuardResult(
        True,
        "UCP_WEBHOOK_SIG_NAMESPACE_AND_QUANTITY_UNIT_VERIFIED",
        "UCP #659 webhook signing gate, #657/#655 ambient `ucp` namespace, and #653 `quantity_unit` verified.",
        {},
    )


_ALLOWED_MESSAGE_ERROR_TYPES = frozenset(
    {
        "missing",
        "invalid",
        "out_of_stock",
        "payment_declined",
        "requires_sign_in",
        "requires_3ds",
        "intervention_required",
    }
)
_SELLER_BACKED_HANDLERS = frozenset(
    {
        "dev.acp.seller_backed.saved_card",
        "dev.acp.seller_backed.gift_card",
        "dev.acp.seller_backed.points",
        "dev.acp.seller_backed.store_credit",
    }
)


def validate_acp_seller_backed_intervention_and_version_mismatch_guard(
    payload: Mapping[str, Any],
) -> Stage110GuardResult:
    """Validate ACP #118 `intervention_required`, #114 `dev.acp.seller_backed.*`, and #99 `supported_versions`."""
    msg_err = payload.get("message_error", {})
    if isinstance(msg_err, Mapping) and msg_err:
        err_type = str(msg_err.get("type", ""))
        if err_type == "interventioned_required" or err_type not in _ALLOWED_MESSAGE_ERROR_TYPES:
            return Stage110GuardResult(
                False,
                "ACP_MESSAGE_ERROR_TYPE_INVALID",
                "ACP `MessageError.type` must use canonical `intervention_required` (rejecting typo `interventioned_required`) (#118).",
                {"type": err_type},
            )

    handler = payload.get("seller_backed_handler", {})
    if isinstance(handler, Mapping) and handler:
        h_name = str(handler.get("name", ""))
        if h_name not in _SELLER_BACKED_HANDLERS:
            return Stage110GuardResult(
                False,
                "ACP_SELLER_BACKED_HANDLER_NAME_INVALID",
                "Seller-backed payment handler must be one of `dev.acp.seller_backed.{saved_card,gift_card,points,store_credit}` (#114).",
                {"name": h_name},
            )
        if handler.get("requires_delegate_payment") is not True or handler.get("requires_pci_compliance") is not False:
            return Stage110GuardResult(
                False,
                "ACP_SELLER_BACKED_PCI_DELEGATE_FLAGS_INVALID",
                "Seller-backed handlers require `requires_delegate_payment: true` and `requires_pci_compliance: false` (#114).",
                {
                    "requires_delegate_payment": handler.get("requires_delegate_payment"),
                    "requires_pci_compliance": handler.get("requires_pci_compliance"),
                },
            )
        if handler.get("raw_credentials_transferred") is True:
            return Stage110GuardResult(
                False,
                "ACP_SELLER_BACKED_RAW_CREDENTIAL_LEAK_BLOCKED",
                "Seller-backed payment handlers must resolve on seller backend via `delegate_payment` without transferring raw credentials (#114).",
                {},
            )
        if h_name == "dev.acp.seller_backed.points":
            balance = int(handler.get("points_balance_minor", 0))
            purchase = int(handler.get("purchase_amount_minor", 0))
            if balance < purchase:
                return Stage110GuardResult(
                    False,
                    "ACP_SELLER_BACKED_POINTS_INSUFFICIENT_BALANCE",
                    "`dev.acp.seller_backed.points` is only eligible when points balance >= purchase amount (#114).",
                    {"points_balance_minor": balance, "purchase_amount_minor": purchase},
                )

    ver_err = payload.get("version_mismatch_error", {})
    if isinstance(ver_err, Mapping) and ver_err:
        sup = ver_err.get("supported_versions")
        if not isinstance(sup, Sequence) or isinstance(sup, (str, bytes)) or len(sup) == 0:
            return Stage110GuardResult(
                False,
                "ACP_VERSION_MISMATCH_SUPPORTED_VERSIONS_MISSING",
                "Version mismatch error responses must include non-empty `supported_versions` array (#99).",
                {},
            )

    return Stage110GuardResult(
        True,
        "ACP_SELLER_BACKED_INTERVENTION_AND_VERSION_VERIFIED",
        "ACP #118 `intervention_required`, #114 `dev.acp.seller_backed.*`, and #99 `supported_versions` verified.",
        {},
    )


_ISO4217_EXPONENTS: dict[str, int] = {
    "BIF": 0, "CLP": 0, "DJF": 0, "GNF": 0, "ISK": 0, "JPY": 0, "KMF": 0, "KRW": 0,
    "PYG": 0, "RWF": 0, "UGX": 0, "UYI": 0, "VND": 0, "VUV": 0, "XAF": 0, "XOF": 0, "XPF": 0,
    "BHD": 3, "IQD": 3, "JOD": 3, "KWD": 3, "LYD": 3, "OMR": 3, "TND": 3,
    "CLF": 4, "UYW": 4,
}


def major_to_minor_units_iso4217(value: float | int | str | Decimal, currency: str) -> int:
    exp = _ISO4217_EXPONENTS.get(currency.upper(), 2)
    scaled = Decimal(str(value)) * (Decimal(10) ** Decimal(exp))
    return int(scaled.to_integral_value(rounding=ROUND_FLOOR))


def _parse_iso8601_value(raw: str) -> date | datetime:
    text = raw.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return date.fromisoformat(text)
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _within_execution_window(exec_raw: str, not_before_raw: str, not_after_raw: str) -> bool:
    exec_val = _parse_iso8601_value(exec_raw)
    nb_val = _parse_iso8601_value(not_before_raw)
    na_val = _parse_iso8601_value(not_after_raw)
    if isinstance(exec_val, date) and not isinstance(exec_val, datetime):
        nb_date = nb_val.date() if isinstance(nb_val, datetime) else nb_val
        na_date = na_val.date() if isinstance(na_val, datetime) else na_val
        return nb_date <= exec_val <= na_date
    exec_dt = exec_val if isinstance(exec_val, datetime) else datetime(exec_val.year, exec_val.month, exec_val.day, tzinfo=timezone.utc)
    nb_dt = nb_val if isinstance(nb_val, datetime) else datetime(nb_val.year, nb_val.month, nb_val.day, tzinfo=timezone.utc)
    na_dt = na_val if isinstance(na_val, datetime) else datetime(na_val.year, na_val.month, na_val.day, 23, 59, 59, tzinfo=timezone.utc)
    return nb_dt.astimezone(timezone.utc) <= exec_dt.astimezone(timezone.utc) <= na_dt.astimezone(timezone.utc)


def validate_ap2_budget_iso8601_and_x402_nowallet_guard(
    payload: Mapping[str, Any],
) -> Stage110GuardResult:
    """Validate AP2 #377 ISO 4217 budget minor units, #378 ISO 8601 execution window, and x402 #317 `no-wallet`."""
    budget = payload.get("ap2_budget", {})
    if isinstance(budget, Mapping) and budget:
        currency = str(budget.get("currency", "USD")).upper()
        max_major = budget.get("max", 0)
        requested_minor = int(budget.get("requested_amount_minor", 0))
        cap_minor = major_to_minor_units_iso4217(max_major, currency)
        if requested_minor > cap_minor:
            return Stage110GuardResult(
                False,
                "AP2_BUDGET_ISO4217_CAP_EXCEEDED",
                "Requested payment minor units exceed ISO 4217 `Decimal`-converted `payment.budget.max` cap (#377).",
                {"currency": currency, "cap_minor": cap_minor, "requested_minor": requested_minor},
            )

    window = payload.get("ap2_execution_window", {})
    if isinstance(window, Mapping) and window:
        try:
            ok = _within_execution_window(
                str(window.get("execution_date", "")),
                str(window.get("not_before", "")),
                str(window.get("not_after", "")),
            )
        except Exception:
            return Stage110GuardResult(
                False,
                "AP2_EXECUTION_DATE_ISO8601_PARSE_FAILED",
                "Invalid ISO 8601 `execution_date` or window bounds must fail closed (#378).",
                {},
            )
        if not ok:
            return Stage110GuardResult(
                False,
                "AP2_EXECUTION_DATE_OUTSIDE_CHRONOLOGICAL_WINDOW",
                "Mandate `execution_date` falls outside chronological UTC `[not_before, not_after]` window (#378).",
                {"execution_date": window.get("execution_date")},
            )

    no_wallet = payload.get("x402_no_wallet", {})
    if isinstance(no_wallet, Mapping) and no_wallet:
        if not isinstance(no_wallet.get("requires"), Mapping) or not no_wallet.get("requires"):
            return Stage110GuardResult(
                False,
                "X402_NO_WALLET_REQUIRES_FIELD_MISSING",
                "x402 `no-wallet` extension must include non-empty `requires` asset/network specification (#317).",
                {},
            )
        if no_wallet.get("anyWalletWorks") is not True:
            return Stage110GuardResult(
                False,
                "X402_NO_WALLET_PROPRIETARY_LOCKIN_REJECTED",
                "x402 `no-wallet` extension requires `anyWalletWorks: true` to prevent single-wallet lock-in (#317).",
                {},
            )
        if no_wallet.get("auto_execute_install_command") is True:
            return Stage110GuardResult(
                False,
                "X402_NO_WALLET_UNTRUSTED_INSTALL_EXEC_BLOCKED",
                "Clients must never auto-execute untrusted `install` shell commands from a 402 response (#317).",
                {},
            )
        wallets = no_wallet.get("wallets", [])
        if isinstance(wallets, Sequence):
            for w in wallets:
                if not isinstance(w, Mapping) or not isinstance(w.get("custodial"), bool):
                    return Stage110GuardResult(
                        False,
                        "X402_NO_WALLET_CUSTODIAL_FLAG_MISSING",
                        "Every wallet entry in `no-wallet.wallets` must declare boolean `custodial` (#317).",
                        {},
                    )

    return Stage110GuardResult(
        True,
        "AP2_BUDGET_ISO8601_AND_X402_NOWALLET_VERIFIED",
        "AP2 #377 ISO 4217 budget cap, #378 chronological ISO 8601 window, and x402 #317 `no-wallet` verified.",
        {},
    )


_CANONICAL_TIME_RE = re.compile(
    r"(?:Current time is\s+)?(?P<date>\d{4}-\d{2}-\d{2})[T ](?P<hm>\d{2}:\d{2})(?::(?P<sec>\d{2}))?(?:\s*EST)?\.?$"
)


def canonicalize_tau2_time_verified(raw: str, gold_canonical: str = "2025-11-14 03:40:00 EST") -> str:
    text = raw.strip()
    if any(bad_tz in text for bad_tz in ("PST", "UTC", "+00:00")) or text.endswith("Z"):
        return text
    m = _CANONICAL_TIME_RE.match(text)
    if not m:
        return text
    sec = m.group("sec") or "00"
    candidate = f"{m.group('date')} {m.group('hm')}:{sec} EST"
    return candidate if candidate == gold_canonical else text


def validate_tau2_historical_packages_time_verified_and_active_refuel_guard(
    payload: Mapping[str, Any],
) -> Stage110GuardResult:
    """Validate Sierra tau2-bench #651 historical domain packages, #634 `time_verified`, and #611 active-line refuel."""
    pkg = payload.get("historical_package", {})
    if isinstance(pkg, Mapping) and pkg:
        frame = str(pkg.get("benchmark_frame", "voice-v2"))
        pkg_name = str(pkg.get("package_name", ""))
        if frame == "voice-v2-banking" and not pkg_name.endswith("_banking"):
            return Stage110GuardResult(
                False,
                "TAU2_HISTORICAL_PACKAGE_SUFFIX_MISMATCH",
                "`voice-v2-banking` packages must end with `_banking` suffix (#651).",
                {"benchmark_frame": frame, "package_name": pkg_name},
            )
        if frame == "voice-v2-entity" and not pkg_name.endswith("_entity"):
            return Stage110GuardResult(
                False,
                "TAU2_HISTORICAL_PACKAGE_SUFFIX_MISMATCH",
                "`voice-v2-entity` packages must end with `_entity` suffix (#651).",
                {"benchmark_frame": frame, "package_name": pkg_name},
            )
        if frame in ("voice-v2-banking", "voice-v2-entity") and pkg.get("judges_root_supplied") is True:
            return Stage110GuardResult(
                False,
                "TAU2_NON_JUDGED_BENCHMARK_JUDGES_ROOT_REJECTED",
                "`--judges-root` must be rejected for unjudged `voice-v2-banking` and `voice-v2-entity` frames (#651).",
                {"benchmark_frame": frame},
            )
        fingerprints = pkg.get("cell_condition_fingerprints", [])
        if isinstance(fingerprints, Sequence) and len(set(fingerprints)) > 1:
            return Stage110GuardResult(
                False,
                "TAU2_MIXED_CELL_CONDITION_FINGERPRINTS_REJECTED",
                "All cells in a historical package must produce a single uniform `condition_fingerprint` (#651).",
                {"unique_fingerprints": len(set(fingerprints))},
            )

    time_check = payload.get("banking_time_verified", {})
    if isinstance(time_check, Mapping) and time_check:
        gold = str(time_check.get("gold_canonical", "2025-11-14 03:40:00 EST"))
        norm = canonicalize_tau2_time_verified(str(time_check.get("raw", "")), gold)
        if norm != gold:
            return Stage110GuardResult(
                False,
                "TAU2_TIME_VERIFIED_MISMATCH_OR_FABRICATED",
                "`log_verification` `time_verified` does not canonicalize to the environment clock (#634).",
                {"raw": time_check.get("raw"), "canonicalized": norm, "gold": gold},
            )

    refuel = payload.get("telecom_refuel", {})
    if isinstance(refuel, Mapping) and refuel:
        line_status = str(refuel.get("line_status", ""))
        if line_status != "Active":
            return Stage110GuardResult(
                False,
                "TAU2_TELECOM_INACTIVE_LINE_REFUEL_BLOCKED",
                "`refuel_data` requires `line_status == 'Active'` and must leave DB/billing unchanged for inactive lines (#611).",
                {"line_status": line_status},
            )

    return Stage110GuardResult(
        True,
        "TAU2_HISTORICAL_PACKAGES_TIME_AND_ACTIVE_REFUEL_VERIFIED",
        "Sierra tau2-bench #651 historical package rules, #634 `time_verified` canonicalization, and #611 active-line refuel verified.",
        {},
    )
