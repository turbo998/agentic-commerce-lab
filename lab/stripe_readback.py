"""Atomic local acceptance of trusted readbacks, not provider transactions."""

from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
import re

from lab.merchant_signers import (
    AdmissionProvenancePath,
    MerchantSignerError,
    MerchantSignerPermissionStatus,
    MerchantSignerScope,
    MerchantSignerStore,
    OperationAdmissionProvenance,
    TimedSignerAdmission,
)
from lab.payment_approvals import (
    ApprovalAdmission,
    PaymentApprovalError,
    PaymentApprovalStatus,
    PaymentApprovalStore,
)
from lab.payment_attempts import AttemptConflict, PaymentAttempt, PaymentAttemptJournal, PaymentOperation
from lab.stripe_inbox import (
    InboxReceipt,
    ReadbackClaim,
    ReadbackClaimStatus,
    StripeEventInbox,
    StripeInboxScope,
)
from lab.stripe_observation import validate_stripe_intent


class StripeReadbackError(ValueError):
    """The configured stores, active claim or operation do not share a binding."""


@dataclass(frozen=True)
class StripeReadbackProvenance:
    """Single-snapshot local readback provenance, never remote provider authority."""

    scope: StripeInboxScope
    event_id: str
    fingerprint: str
    attempt: PaymentAttempt | None
    receipt: InboxReceipt | None
    claim_status: ReadbackClaimStatus | None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, StripeInboxScope):
            raise StripeReadbackError("A trusted StripeInboxScope is required.")
        if not isinstance(self.event_id, str) or re.fullmatch(r"evt_[A-Za-z0-9_]+", self.event_id) is None:
            raise StripeReadbackError("A snapshot Event ID is required.")
        if not isinstance(self.fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", self.fingerprint) is None:
            raise StripeReadbackError("Provenance operation fingerprint is invalid.")
        if self.attempt is not None and not isinstance(self.attempt, PaymentAttempt):
            raise StripeReadbackError("Provenance attempt must be a PaymentAttempt or None.")
        if self.receipt is not None and not isinstance(self.receipt, InboxReceipt):
            raise StripeReadbackError("Provenance receipt must be an InboxReceipt or None.")
        if self.claim_status is not None and not isinstance(self.claim_status, ReadbackClaimStatus):
            raise StripeReadbackError("Provenance claim status must be a ReadbackClaimStatus or None.")
        if self.attempt is None and self.receipt is None:
            raise StripeReadbackError(
                "Readback provenance requires a reserved attempt or a recorded receipt."
            )
        if self.receipt is not None and self.receipt.event_id != self.event_id:
            raise StripeReadbackError("Receipt Event ID differs from the provenance lookup key.")
        if self.claim_status is not None and self.receipt is None:
            raise StripeReadbackError("Readback claim status cannot exist without a recorded receipt.")
        if self.claim_status is not None and (
            self.claim_status.claim.scope != self.scope
            or self.claim_status.claim.receipt != self.receipt
        ):
            raise StripeReadbackError(
                "Readback claim status does not match provenance scope or receipt."
            )
        if (
            self.attempt is not None
            and self.attempt.provider_reference is not None
            and self.receipt is not None
            and self.attempt.provider_reference != self.receipt.provider_reference
        ):
            raise StripeReadbackError(
                "Receipt differs from the trusted PaymentIntent association."
            )


def find_stripe_readback_provenance(
    inbox: StripeEventInbox,
    journal: PaymentAttemptJournal,
    scope: StripeInboxScope,
    event_id: str,
    operation: PaymentOperation,
) -> StripeReadbackProvenance | None:
    """Read coupled attempt, receipt and claim state in one lock-free snapshot.

    Returns None only when neither the payment attempt nor the scoped webhook
    receipt exists. Fails closed on store mismatch, scope/operation drift,
    corrupted columns, orphan claim rows, or conflicting PaymentIntent IDs.
    """
    if (
        not isinstance(inbox, StripeEventInbox)
        or not isinstance(journal, PaymentAttemptJournal)
        or not isinstance(scope, StripeInboxScope)
        or not isinstance(operation, PaymentOperation)
    ):
        raise StripeReadbackError(
            "Trusted inbox, journal, inbox scope and payment operation are required."
        )
    key = inbox._require_event_lookup(scope, event_id)
    if (
        scope.tenant_id != operation.tenant_id
        or scope.provider_account != operation.provider_account
        or operation.provider != ("stripe:live" if scope.livemode else "stripe:test")
    ):
        raise StripeReadbackError("Inbox scope differs from the bound payment operation.")
    if inbox.path.resolve(strict=True) != journal.path.resolve(strict=True):
        raise StripeReadbackError("Readback provenance requires the same resolved SQLite file.")
    with closing(inbox._connect()) as db:
        row = db.execute(
            "SELECT "
            "att.fingerprint AS att_fingerprint, "
            "att.approval_id AS att_approval_id, "
            "att.provider AS att_provider, "
            "att.provider_account AS att_provider_account, "
            "att.idempotency_key AS att_idempotency_key, "
            "att.outcome AS att_outcome, "
            "att.provider_reference AS att_provider_reference, "
            "i.event_id AS i_event_id, "
            "i.event_type AS i_event_type, "
            "i.provider_reference AS i_provider_reference, "
            "i.payload_sha256 AS i_payload_sha256, "
            "c.event_id AS c_event_id, "
            "c.worker_id AS c_worker_id, "
            "c.generation AS c_generation, "
            "c.state AS c_state "
            "FROM (SELECT 1) "
            "LEFT JOIN payment_attempts att "
            "ON att.tenant_id=? AND att.operation_id=? "
            "LEFT JOIN stripe_event_inbox i "
            "ON i.tenant_id=? AND i.endpoint_id=? "
            "AND i.provider_account=? AND i.livemode=? AND i.event_id=? "
            "LEFT JOIN stripe_readback_claims c "
            "ON c.tenant_id=? AND c.endpoint_id=? "
            "AND c.provider_account=? AND c.livemode=? AND c.event_id=?",
            (operation.tenant_id, operation.operation_id, *key, *key),
        ).fetchone()
    if row is None or (
        row["att_fingerprint"] is None
        and row["i_event_id"] is None
        and row["c_event_id"] is None
    ):
        return None

    attempt: PaymentAttempt | None = None
    if row["att_fingerprint"] is not None:
        if (
            row["att_fingerprint"] != operation.fingerprint
            or row["att_approval_id"] != operation.approval_id
            or row["att_provider"] != operation.provider
            or row["att_provider_account"] != operation.provider_account
            or row["att_idempotency_key"] != operation.idempotency_key
        ):
            raise AttemptConflict("Operation binding differs from the reserved attempt.")
        attempt = journal._attempt(
            {
                "outcome": row["att_outcome"],
                "provider_reference": row["att_provider_reference"],
            }
        )

    receipt: InboxReceipt | None = None
    if row["i_event_id"] is not None or row["c_event_id"] is not None:
        receipt = inbox._receipt(
            {
                "event_id": row["i_event_id"] if row["i_event_id"] is not None else row["c_event_id"],
                "event_type": row["i_event_type"],
                "provider_reference": row["i_provider_reference"],
                "payload_sha256": row["i_payload_sha256"],
            }
        )

    claim_status: ReadbackClaimStatus | None = None
    if row["c_event_id"] is not None:
        assert receipt is not None
        claim_status = ReadbackClaimStatus(
            ReadbackClaim(scope, receipt, row["c_worker_id"], row["c_generation"]),
            row["c_state"],
        )

    return StripeReadbackProvenance(
        scope=scope,
        event_id=event_id,
        fingerprint=operation.fingerprint,
        attempt=attempt,
        receipt=receipt,
        claim_status=claim_status,
    )


def read_stripe_readback_provenance(
    inbox: StripeEventInbox,
    journal: PaymentAttemptJournal,
    scope: StripeInboxScope,
    event_id: str,
    operation: PaymentOperation,
) -> StripeReadbackProvenance:
    """Read coupled attempt, receipt and claim provenance or fail closed when absent."""
    provenance = find_stripe_readback_provenance(
        inbox, journal, scope, event_id, operation,
    )
    if provenance is None:
        raise StripeReadbackError(
            "No payment attempt or webhook receipt exists for this operation and event."
        )
    return provenance


@dataclass(frozen=True)
class StripeLifecycleProvenance:
    """Single-snapshot cross-plane lifecycle provenance, never remote or live authority."""

    scope: StripeInboxScope
    event_id: str
    fingerprint: str
    attempt: PaymentAttempt | None
    approval_status: PaymentApprovalStatus | None
    approval_admission: ApprovalAdmission | None
    signer_permission: MerchantSignerPermissionStatus | None
    timed_signer_admission: TimedSignerAdmission | None
    receipt: InboxReceipt | None
    claim_status: ReadbackClaimStatus | None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, StripeInboxScope):
            raise StripeReadbackError("A trusted StripeInboxScope is required.")
        if not isinstance(self.event_id, str) or re.fullmatch(r"evt_[A-Za-z0-9_]+", self.event_id) is None:
            raise StripeReadbackError("A snapshot Event ID is required.")
        if not isinstance(self.fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", self.fingerprint) is None:
            raise StripeReadbackError("Provenance operation fingerprint is invalid.")
        if self.attempt is not None and not isinstance(self.attempt, PaymentAttempt):
            raise StripeReadbackError("Provenance attempt must be a PaymentAttempt or None.")
        if self.approval_status is not None and not isinstance(
            self.approval_status, PaymentApprovalStatus
        ):
            raise StripeReadbackError(
                "Provenance approval_status must be a PaymentApprovalStatus or None."
            )
        if self.approval_admission is not None and not isinstance(
            self.approval_admission, ApprovalAdmission
        ):
            raise StripeReadbackError(
                "Provenance approval_admission must be an ApprovalAdmission or None."
            )
        if self.signer_permission is not None and not isinstance(
            self.signer_permission, MerchantSignerPermissionStatus
        ):
            raise StripeReadbackError(
                "Provenance signer_permission must be a MerchantSignerPermissionStatus or None."
            )
        if self.timed_signer_admission is not None and not isinstance(
            self.timed_signer_admission, TimedSignerAdmission
        ):
            raise StripeReadbackError(
                "Provenance timed_signer_admission must be a TimedSignerAdmission or None."
            )
        if self.receipt is not None and not isinstance(self.receipt, InboxReceipt):
            raise StripeReadbackError("Provenance receipt must be an InboxReceipt or None.")
        if self.claim_status is not None and not isinstance(self.claim_status, ReadbackClaimStatus):
            raise StripeReadbackError("Provenance claim status must be a ReadbackClaimStatus or None.")
        if (
            self.attempt is None
            and self.approval_status is None
            and self.approval_admission is None
            and self.signer_permission is None
            and self.timed_signer_admission is None
            and self.receipt is None
            and self.claim_status is None
        ):
            raise StripeReadbackError(
                "Lifecycle provenance requires at least one recorded lifecycle artifact."
            )
        if self.approval_status is not None and self.approval_status.fingerprint != self.fingerprint:
            raise StripeReadbackError("Approval record differs from the bound operation.")
        if self.approval_admission is not None:
            if self.approval_admission.fingerprint != self.fingerprint:
                raise StripeReadbackError(
                    "Approval admission record differs from the bound operation."
                )
            if self.attempt is None:
                raise StripeReadbackError(
                    "Orphan approval admission record exists without a reserved payment attempt."
                )
            if self.approval_status is None:
                raise StripeReadbackError(
                    "Orphan approval admission record exists without a recorded approval."
                )
            if self.approval_admission.expires_at != self.approval_status.expires_at:
                raise StripeReadbackError(
                    "Approval admission expiry differs from recorded approval."
                )
        if self.timed_signer_admission is not None:
            if self.timed_signer_admission.fingerprint != self.fingerprint:
                raise StripeReadbackError(
                    "Timed-admission record differs from the bound operation."
                )
            if self.attempt is None:
                raise StripeReadbackError(
                    "Orphan timed-admission record exists without a reserved payment attempt."
                )
            if self.approval_admission is None:
                raise StripeReadbackError(
                    "Orphan timed-admission record exists without an approval admission."
                )
            if self.signer_permission is None:
                raise StripeReadbackError(
                    "Orphan timed-admission record exists without a recorded signer permission."
                )
            if self.signer_permission.scope != self.timed_signer_admission.scope:
                raise StripeReadbackError(
                    "Signer permission scope differs from timed-admission scope."
                )
            if self.timed_signer_admission.scope.tenant_id != self.scope.tenant_id:
                raise StripeReadbackError(
                    "Timed-admission tenant differs from provenance scope."
                )
            if self.timed_signer_admission.admitted_at != self.approval_admission.admitted_at:
                raise StripeReadbackError(
                    "Timed-admission clock sample differs from approval admission."
                )
            if not 0 <= self.timed_signer_admission.admitted_at < self.approval_admission.expires_at:
                raise StripeReadbackError(
                    "Timed-admission clock sample is outside approval admission expiry."
                )
        elif self.signer_permission is not None:
            raise StripeReadbackError(
                "Signer permission status requires a timed-admission route/key binding."
            )
        if self.receipt is not None and self.receipt.event_id != self.event_id:
            raise StripeReadbackError("Receipt Event ID differs from the provenance lookup key.")
        if self.claim_status is not None and self.receipt is None:
            raise StripeReadbackError("Readback claim status cannot exist without a recorded receipt.")
        if self.claim_status is not None and (
            self.claim_status.claim.scope != self.scope
            or self.claim_status.claim.receipt != self.receipt
        ):
            raise StripeReadbackError(
                "Readback claim status does not match provenance scope or receipt."
            )
        if (
            self.attempt is not None
            and self.attempt.provider_reference is not None
            and self.receipt is not None
            and self.attempt.provider_reference != self.receipt.provider_reference
        ):
            raise StripeReadbackError(
                "Receipt differs from the trusted PaymentIntent association."
            )

    @property
    def admission_path(self) -> AdmissionProvenancePath | None:
        if self.attempt is None:
            return None
        if self.timed_signer_admission is not None:
            return "timed_signer_admission"
        if self.approval_admission is not None:
            return "approval_admission"
        return "direct_reservation"

    @property
    def admission_provenance(self) -> OperationAdmissionProvenance | None:
        if self.attempt is None:
            return None
        return OperationAdmissionProvenance(
            self.fingerprint,
            self.attempt,
            self.approval_admission,
            self.timed_signer_admission,
        )

    @property
    def readback_provenance(self) -> StripeReadbackProvenance | None:
        if self.attempt is None and self.receipt is None:
            return None
        return StripeReadbackProvenance(
            scope=self.scope,
            event_id=self.event_id,
            fingerprint=self.fingerprint,
            attempt=self.attempt,
            receipt=self.receipt,
            claim_status=self.claim_status,
        )


def find_stripe_lifecycle_provenance(
    inbox: StripeEventInbox,
    journal: PaymentAttemptJournal,
    approvals: PaymentApprovalStore,
    scope: StripeInboxScope,
    event_id: str,
    operation: PaymentOperation,
    *,
    signers: MerchantSignerStore | None = None,
) -> StripeLifecycleProvenance | None:
    """Read cross-plane admission and readback state in one lock-free SQLite snapshot.

    Joins 5 tables (payment_attempts, payment_admissions, payment_approvals,
    stripe_event_inbox, stripe_readback_claims) or 7 tables when signers is
    supplied (adding merchant_timed_admissions and merchant_signer_permissions).
    """
    if (
        not isinstance(inbox, StripeEventInbox)
        or not isinstance(journal, PaymentAttemptJournal)
        or not isinstance(approvals, PaymentApprovalStore)
        or not isinstance(scope, StripeInboxScope)
        or not isinstance(operation, PaymentOperation)
        or (signers is not None and not isinstance(signers, MerchantSignerStore))
    ):
        raise StripeReadbackError(
            "Trusted inbox, journal, approvals, inbox scope and payment operation are required."
        )
    key = inbox._require_event_lookup(scope, event_id)
    if (
        scope.tenant_id != operation.tenant_id
        or scope.provider_account != operation.provider_account
        or operation.provider != ("stripe:live" if scope.livemode else "stripe:test")
    ):
        raise StripeReadbackError("Inbox scope differs from the bound payment operation.")
    resolved_inbox = inbox.path.resolve(strict=True)
    if (
        resolved_inbox != journal.path.resolve(strict=True)
        or resolved_inbox != approvals.path.resolve(strict=True)
        or (signers is not None and resolved_inbox != signers.path.resolve(strict=True))
    ):
        raise StripeReadbackError(
            "Lifecycle provenance requires the same resolved SQLite file across all stores."
        )
    with closing(inbox._connect()) as db:
        if signers is None:
            row = db.execute(
                "SELECT "
                "att.fingerprint AS att_fingerprint, "
                "att.approval_id AS att_approval_id, "
                "att.provider AS att_provider, "
                "att.provider_account AS att_provider_account, "
                "att.idempotency_key AS att_idempotency_key, "
                "att.outcome AS att_outcome, "
                "att.provider_reference AS att_provider_reference, "
                "adm.fingerprint AS adm_fingerprint, "
                "adm.admitted_at AS adm_admitted_at, "
                "adm.expires_at AS adm_expires_at, "
                "app.fingerprint AS app_fingerprint, "
                "app.expires_at AS app_expires_at, "
                "app.revoked AS app_revoked, "
                "NULL AS tmd_fingerprint, "
                "NULL AS tmd_target_uri, "
                "NULL AS tmd_key_id, "
                "NULL AS tmd_signature_label, "
                "NULL AS tmd_created, "
                "NULL AS tmd_expires, "
                "NULL AS tmd_admitted_at, "
                "NULL AS perm_revoked, "
                "i.event_id AS i_event_id, "
                "i.event_type AS i_event_type, "
                "i.provider_reference AS i_provider_reference, "
                "i.payload_sha256 AS i_payload_sha256, "
                "c.event_id AS c_event_id, "
                "c.worker_id AS c_worker_id, "
                "c.generation AS c_generation, "
                "c.state AS c_state "
                "FROM ("
                "SELECT ? AS tenant_id, ? AS operation_id, ? AS approval_id"
                ") k "
                "LEFT JOIN payment_attempts att USING (tenant_id, operation_id) "
                "LEFT JOIN payment_admissions adm USING (tenant_id, operation_id) "
                "LEFT JOIN payment_approvals app "
                "ON app.tenant_id = k.tenant_id AND app.approval_id = k.approval_id "
                "LEFT JOIN stripe_event_inbox i "
                "ON i.tenant_id=? AND i.endpoint_id=? "
                "AND i.provider_account=? AND i.livemode=? AND i.event_id=? "
                "LEFT JOIN stripe_readback_claims c "
                "ON c.tenant_id=? AND c.endpoint_id=? "
                "AND c.provider_account=? AND c.livemode=? AND c.event_id=?",
                (
                    operation.tenant_id,
                    operation.operation_id,
                    operation.approval_id,
                    *key,
                    *key,
                ),
            ).fetchone()
        else:
            row = db.execute(
                "SELECT "
                "att.fingerprint AS att_fingerprint, "
                "att.approval_id AS att_approval_id, "
                "att.provider AS att_provider, "
                "att.provider_account AS att_provider_account, "
                "att.idempotency_key AS att_idempotency_key, "
                "att.outcome AS att_outcome, "
                "att.provider_reference AS att_provider_reference, "
                "adm.fingerprint AS adm_fingerprint, "
                "adm.admitted_at AS adm_admitted_at, "
                "adm.expires_at AS adm_expires_at, "
                "app.fingerprint AS app_fingerprint, "
                "app.expires_at AS app_expires_at, "
                "app.revoked AS app_revoked, "
                "tmd.fingerprint AS tmd_fingerprint, "
                "tmd.target_uri AS tmd_target_uri, "
                "tmd.key_id AS tmd_key_id, "
                "tmd.signature_label AS tmd_signature_label, "
                "tmd.created AS tmd_created, "
                "tmd.expires AS tmd_expires, "
                "tmd.admitted_at AS tmd_admitted_at, "
                "perm.revoked AS perm_revoked, "
                "i.event_id AS i_event_id, "
                "i.event_type AS i_event_type, "
                "i.provider_reference AS i_provider_reference, "
                "i.payload_sha256 AS i_payload_sha256, "
                "c.event_id AS c_event_id, "
                "c.worker_id AS c_worker_id, "
                "c.generation AS c_generation, "
                "c.state AS c_state "
                "FROM ("
                "SELECT ? AS tenant_id, ? AS operation_id, ? AS approval_id, ? AS merchant"
                ") k "
                "LEFT JOIN payment_attempts att USING (tenant_id, operation_id) "
                "LEFT JOIN payment_admissions adm USING (tenant_id, operation_id) "
                "LEFT JOIN payment_approvals app "
                "ON app.tenant_id = k.tenant_id AND app.approval_id = k.approval_id "
                "LEFT JOIN merchant_timed_admissions tmd USING (tenant_id, operation_id) "
                "LEFT JOIN merchant_signer_permissions perm "
                "ON perm.tenant_id = k.tenant_id "
                "AND perm.merchant = k.merchant "
                "AND perm.target_uri = tmd.target_uri "
                "AND perm.key_id = tmd.key_id "
                "LEFT JOIN stripe_event_inbox i "
                "ON i.tenant_id=? AND i.endpoint_id=? "
                "AND i.provider_account=? AND i.livemode=? AND i.event_id=? "
                "LEFT JOIN stripe_readback_claims c "
                "ON c.tenant_id=? AND c.endpoint_id=? "
                "AND c.provider_account=? AND c.livemode=? AND c.event_id=?",
                (
                    operation.tenant_id,
                    operation.operation_id,
                    operation.approval_id,
                    operation.checkout.merchant,
                    *key,
                    *key,
                ),
            ).fetchone()
    if row is None or (
        row["att_fingerprint"] is None
        and row["adm_fingerprint"] is None
        and row["app_fingerprint"] is None
        and row["tmd_fingerprint"] is None
        and row["i_event_id"] is None
        and row["c_event_id"] is None
    ):
        return None

    attempt: PaymentAttempt | None = None
    if row["att_fingerprint"] is not None:
        if (
            row["att_fingerprint"] != operation.fingerprint
            or row["att_approval_id"] != operation.approval_id
            or row["att_provider"] != operation.provider
            or row["att_provider_account"] != operation.provider_account
            or row["att_idempotency_key"] != operation.idempotency_key
        ):
            raise AttemptConflict("Operation binding differs from the reserved attempt.")
        attempt = journal._attempt(
            {
                "outcome": row["att_outcome"],
                "provider_reference": row["att_provider_reference"],
            }
        )

    approval_status: PaymentApprovalStatus | None = None
    if row["app_fingerprint"] is not None:
        if row["app_fingerprint"] != operation.fingerprint:
            raise StripeReadbackError("Approval record differs from the bound operation.")
        app_expires_at, app_revoked = row["app_expires_at"], row["app_revoked"]
        if type(app_expires_at) is not int or not 0 < app_expires_at <= 2**63 - 1:
            raise StripeReadbackError("Stored approval expiry is invalid.")
        if type(app_revoked) is not int or app_revoked not in (0, 1):
            raise StripeReadbackError("Stored approval revocation state is invalid.")
        approval_status = PaymentApprovalStatus(
            row["app_fingerprint"],
            app_expires_at,
            "revoked" if app_revoked else "active",
        )

    approval_admission: ApprovalAdmission | None = None
    if row["adm_fingerprint"] is not None:
        if row["adm_fingerprint"] != operation.fingerprint:
            raise StripeReadbackError(
                "Approval admission record differs from the bound operation."
            )
        if attempt is None:
            raise StripeReadbackError(
                "Orphan approval admission record exists without a reserved payment attempt."
            )
        if approval_status is None:
            raise StripeReadbackError(
                "Orphan approval admission record exists without a recorded approval."
            )
        try:
            approval_admission = ApprovalAdmission(
                row["adm_fingerprint"],
                row["adm_admitted_at"],
                row["adm_expires_at"],
            )
        except PaymentApprovalError as exc:
            raise StripeReadbackError(str(exc)) from exc
        if approval_admission.expires_at != approval_status.expires_at:
            raise StripeReadbackError(
                "Approval admission expiry differs from recorded approval."
            )

    signer_permission: MerchantSignerPermissionStatus | None = None
    timed_signer_admission: TimedSignerAdmission | None = None
    if row["tmd_fingerprint"] is not None:
        if row["tmd_fingerprint"] != operation.fingerprint:
            raise StripeReadbackError(
                "Timed-admission record differs from the bound operation."
            )
        if attempt is None:
            raise StripeReadbackError(
                "Orphan timed-admission record exists without a reserved payment attempt."
            )
        if approval_admission is None:
            raise StripeReadbackError(
                "Orphan timed-admission record exists without an approval admission."
            )
        try:
            signer_scope = MerchantSignerScope(
                operation.tenant_id,
                operation.checkout.merchant,
                row["tmd_target_uri"],
                row["tmd_key_id"],
            )
            timed_signer_admission = TimedSignerAdmission(
                row["tmd_fingerprint"],
                signer_scope,
                row["tmd_signature_label"],
                row["tmd_created"],
                row["tmd_expires"],
                row["tmd_admitted_at"],
            )
        except MerchantSignerError as exc:
            raise StripeReadbackError(str(exc)) from exc
        perm_revoked = row["perm_revoked"]
        if perm_revoked is None:
            raise StripeReadbackError(
                "Orphan timed-admission record exists without a recorded signer permission."
            )
        if type(perm_revoked) is not int or perm_revoked not in (0, 1):
            raise StripeReadbackError(
                "Stored signer permission revocation state is invalid."
            )
        signer_permission = MerchantSignerPermissionStatus(
            signer_scope,
            "revoked" if perm_revoked else "active",
        )

    receipt: InboxReceipt | None = None
    if row["i_event_id"] is not None or row["c_event_id"] is not None:
        receipt = inbox._receipt(
            {
                "event_id": row["i_event_id"] if row["i_event_id"] is not None else row["c_event_id"],
                "event_type": row["i_event_type"],
                "provider_reference": row["i_provider_reference"],
                "payload_sha256": row["i_payload_sha256"],
            }
        )

    claim_status: ReadbackClaimStatus | None = None
    if row["c_event_id"] is not None:
        assert receipt is not None
        claim_status = ReadbackClaimStatus(
            ReadbackClaim(scope, receipt, row["c_worker_id"], row["c_generation"]),
            row["c_state"],
        )

    return StripeLifecycleProvenance(
        scope=scope,
        event_id=event_id,
        fingerprint=operation.fingerprint,
        attempt=attempt,
        approval_status=approval_status,
        approval_admission=approval_admission,
        signer_permission=signer_permission,
        timed_signer_admission=timed_signer_admission,
        receipt=receipt,
        claim_status=claim_status,
    )


def read_stripe_lifecycle_provenance(
    inbox: StripeEventInbox,
    journal: PaymentAttemptJournal,
    approvals: PaymentApprovalStore,
    scope: StripeInboxScope,
    event_id: str,
    operation: PaymentOperation,
    *,
    signers: MerchantSignerStore | None = None,
) -> StripeLifecycleProvenance:
    """Read cross-plane lifecycle provenance or fail closed when absent."""
    provenance = find_stripe_lifecycle_provenance(
        inbox,
        journal,
        approvals,
        scope,
        event_id,
        operation,
        signers=signers,
    )
    if provenance is None:
        raise StripeReadbackError(
            "No lifecycle provenance exists for this operation and event."
        )
    return provenance


def accept_stripe_readback(
    inbox: StripeEventInbox, journal: PaymentAttemptJournal, claim: ReadbackClaim,
    operation: PaymentOperation, *,
    retrieved_account: str, intent: Mapping[str, object],
) -> PaymentAttempt:
    """Commit a fenced journal update and hint completion in one local transaction.

    Stores must share a canonical SQLite file. The caller authenticates workers,
    retrieval and freshness outside this transaction; a claim is not authority.
    Already-handled acceptance rejects, including a retry after a lost response.
    """
    if (
        not isinstance(inbox, StripeEventInbox)
        or not isinstance(journal, PaymentAttemptJournal)
        or not isinstance(claim, ReadbackClaim)
        or not isinstance(operation, PaymentOperation)
    ):
        raise StripeReadbackError(
            "Trusted inbox, journal, readback claim and payment operation are required."
        )
    if inbox.path.resolve(strict=True) != journal.path.resolve(strict=True):
        raise StripeReadbackError("Atomic acceptance requires the same resolved SQLite file.")
    with closing(inbox._connect()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        current = inbox._current_claim(db, claim)
        if current["state"] != "active":
            raise StripeReadbackError("Already-handled hints cannot authorize acceptance.")
        if (
            claim.scope.tenant_id != operation.tenant_id
            or claim.scope.provider_account != operation.provider_account
            or operation.provider != ("stripe:live" if claim.scope.livemode else "stripe:test")
        ):
            raise StripeReadbackError("Claim scope differs from the bound payment operation.")
        row = journal._find(db, operation)
        if row is None:
            raise AttemptConflict("Operation was never reserved.")
        previous = journal._attempt(row)
        if previous.provider_reference != claim.receipt.provider_reference:
            raise StripeReadbackError("Receipt differs from the trusted PaymentIntent association.")
        observation = validate_stripe_intent(
            operation, previous, retrieved_account=retrieved_account, intent=intent,
        )
        result = journal._reconcile_in_transaction(
            db, operation, observation=observation,
            provider_reference=claim.receipt.provider_reference,
        )
        inbox._finish_in_transaction(db, claim)
    return result
