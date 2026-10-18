"""Unit tests for Stage 7 RFC 9421 Agent Identity Attestation & Anti-Sybil Quota Guard."""

from __future__ import annotations

import unittest

from lab.agent_identity_attestation_guard import (
    AgentHttpSignedRequest,
    DirectoryKeyEntry,
    REQUIRED_RFC9421_COMPONENTS,
    main,
    run_demo,
    sign_rfc9421_request,
    verify_rfc9421_agent_attestation_and_quota,
)


class AgentIdentityAttestationGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = {
            "tap_kid_active": DirectoryKeyEntry(
                kid="tap_kid_active",
                agent_provider="visa_tap",
                status="active",
                shared_verify_secret="secret_active_123",
                allowed_origins=("https://store.example.com",),
            ),
            "tap_kid_revoked": DirectoryKeyEntry(
                kid="tap_kid_revoked",
                agent_provider="stripe_agent_directory",
                status="revoked",
                shared_verify_secret="secret_revoked_456",
            ),
        }

    def _build_signed_request(
        self,
        *,
        nonce: str = "nonce_01",
        key_id: str = "tap_kid_active",
        secret: str = "secret_active_123",
        created_epoch: int = 1000,
        expires_epoch: int = 1030,
        covered_components: tuple[str, ...] = REQUIRED_RFC9421_COMPONENTS,
        is_webmcp: bool = False,
        webmcp_origin: str | None = None,
        principal_did: str = "did:web:buyer:alice",
        agent_instance_id: str = "agent_01",
        requested_qty: int = 1,
        tamper_body: bytes | None = None,
    ) -> AgentHttpSignedRequest:
        body = b'{"sku":"limited_gpu_01","qty":1}'
        digest, sig = sign_rfc9421_request(
            method="POST",
            authority="store.example.com",
            path="/ucp/v1/checkout",
            body_bytes=body,
            idempotency_key=f"idem_{nonce}",
            ap2_mandate_digest="sha-256=:mandate_digest_01:",
            covered_components=covered_components,
            created_epoch=created_epoch,
            expires_epoch=expires_epoch,
            nonce=nonce,
            key_id=key_id,
            shared_secret=secret,
        )
        return AgentHttpSignedRequest(
            method="POST",
            authority="store.example.com",
            path="/ucp/v1/checkout",
            body_bytes=tamper_body if tamper_body is not None else body,
            content_digest_header=digest,
            idempotency_key=f"idem_{nonce}",
            ap2_mandate_digest="sha-256=:mandate_digest_01:",
            covered_components=covered_components,
            created_epoch=created_epoch,
            expires_epoch=expires_epoch,
            nonce=nonce,
            key_id=key_id,
            signature_hex=sig,
            is_webmcp_browser_call=is_webmcp,
            webmcp_origin=webmcp_origin,
            principal_did=principal_did,
            agent_instance_id=agent_instance_id,
            sku_id="limited_gpu_01",
            requested_qty=requested_qty,
        )

    def test_valid_rfc9421_signature_and_nonce_replay_protection(self) -> None:
        nonces: set[str] = set()
        ledger: dict[tuple[str, str], int] = {}
        agents: dict[tuple[str, str], set[str]] = {}

        req = self._build_signed_request(nonce="nonce_valid_1")
        res1 = verify_rfc9421_agent_attestation_and_quota(
            req,
            now_epoch=1010,
            directory_registry=self.registry,
            seen_nonces=nonces,
            principal_sku_ledger=ledger,
            principal_agent_set=agents,
        )
        self.assertTrue(res1.allowed)
        self.assertEqual(res1.http_status, 200)
        self.assertEqual(res1.decision_code, "ATTESTED_AGENT_ADMITTED")

        # Replaying the exact same signed request must fail with 409 RFC9421_NONCE_REPLAYED
        res_replay = verify_rfc9421_agent_attestation_and_quota(
            req,
            now_epoch=1012,
            directory_registry=self.registry,
            seen_nonces=nonces,
            principal_sku_ledger=ledger,
            principal_agent_set=agents,
        )
        self.assertFalse(res_replay.allowed)
        self.assertEqual(res_replay.http_status, 409)
        self.assertEqual(res_replay.decision_code, "RFC9421_NONCE_REPLAYED")

    def test_missing_components_body_tamper_and_clock_window_rejected(self) -> None:
        nonces: set[str] = set()
        ledger: dict[tuple[str, str], int] = {}
        agents: dict[tuple[str, str], set[str]] = {}

        # 1. Missing x-ap2-mandate-digest component
        incomplete_req = self._build_signed_request(
            nonce="n_missing",
            covered_components=("@method", "@authority", "@path", "content-digest"),
        )
        res_missing = verify_rfc9421_agent_attestation_and_quota(
            incomplete_req,
            now_epoch=1010,
            directory_registry=self.registry,
            seen_nonces=nonces,
            principal_sku_ledger=ledger,
            principal_agent_set=agents,
        )
        self.assertFalse(res_missing.allowed)
        self.assertEqual(res_missing.decision_code, "RFC9421_MISSING_COVERED_COMPONENTS")

        # 2. Tampered body after signing
        tampered_req = self._build_signed_request(
            nonce="n_tamper",
            tamper_body=b'{"sku":"limited_gpu_01","qty":99}',
        )
        res_tamper = verify_rfc9421_agent_attestation_and_quota(
            tampered_req,
            now_epoch=1010,
            directory_registry=self.registry,
            seen_nonces=nonces,
            principal_sku_ledger=ledger,
            principal_agent_set=agents,
        )
        self.assertFalse(res_tamper.allowed)
        self.assertEqual(res_tamper.decision_code, "RFC9530_CONTENT_DIGEST_MISMATCH")

        # 3. TTL > 60s window rejected
        long_ttl_req = self._build_signed_request(
            nonce="n_ttl",
            created_epoch=1000,
            expires_epoch=1120,
        )
        res_ttl = verify_rfc9421_agent_attestation_and_quota(
            long_ttl_req,
            now_epoch=1010,
            directory_registry=self.registry,
            seen_nonces=nonces,
            principal_sku_ledger=ledger,
            principal_agent_set=agents,
        )
        self.assertFalse(res_ttl.allowed)
        self.assertEqual(res_ttl.decision_code, "RFC9421_SIGNATURE_WINDOW_INVALID")

    def test_revoked_directory_key_and_webmcp_cross_origin_blocked(self) -> None:
        nonces: set[str] = set()
        ledger: dict[tuple[str, str], int] = {}
        agents: dict[tuple[str, str], set[str]] = {}

        revoked_req = self._build_signed_request(
            nonce="n_revoked",
            key_id="tap_kid_revoked",
            secret="secret_revoked_456",
        )
        res_revoked = verify_rfc9421_agent_attestation_and_quota(
            revoked_req,
            now_epoch=1010,
            directory_registry=self.registry,
            seen_nonces=nonces,
            principal_sku_ledger=ledger,
            principal_agent_set=agents,
        )
        self.assertFalse(res_revoked.allowed)
        self.assertEqual(res_revoked.decision_code, "AGENT_DIRECTORY_KEY_REVOKED")

        cross_origin_req = self._build_signed_request(
            nonce="n_webmcp",
            is_webmcp=True,
            webmcp_origin="https://evil-phishing.example.net",
        )
        res_origin = verify_rfc9421_agent_attestation_and_quota(
            cross_origin_req,
            now_epoch=1010,
            directory_registry=self.registry,
            seen_nonces=nonces,
            principal_sku_ledger=ledger,
            principal_agent_set=agents,
        )
        self.assertFalse(res_origin.allowed)
        self.assertEqual(res_origin.decision_code, "WEBMCP_CROSS_ORIGIN_VIOLATION")

    def test_principal_bound_anti_sybil_scarcity_quota_and_agent_fanout(self) -> None:
        nonces: set[str] = set()
        ledger: dict[tuple[str, str], int] = {}
        agents: dict[tuple[str, str], set[str]] = {}

        # Principal buys 1 unit via agent_1, 1 unit via agent_2 (reaches max_qty=2)
        for idx in (1, 2):
            req = self._build_signed_request(
                nonce=f"n_sybil_{idx}",
                agent_instance_id=f"agent_{idx}",
                requested_qty=1,
            )
            res = verify_rfc9421_agent_attestation_and_quota(
                req,
                now_epoch=1010,
                directory_registry=self.registry,
                seen_nonces=nonces,
                principal_sku_ledger=ledger,
                principal_agent_set=agents,
                max_qty_per_principal_per_sku=2,
                max_distinct_agents_per_principal=2,
            )
            self.assertTrue(res.allowed)

        # Spawning a 3rd distinct agent for the same human principal trips SYBIL_SWARM_AGENT_FANOUT_EXCEEDED
        req_fanout = self._build_signed_request(
            nonce="n_sybil_3",
            agent_instance_id="agent_3",
            requested_qty=1,
        )
        res_fanout = verify_rfc9421_agent_attestation_and_quota(
            req_fanout,
            now_epoch=1012,
            directory_registry=self.registry,
            seen_nonces=nonces,
            principal_sku_ledger=ledger,
            principal_agent_set=agents,
            max_qty_per_principal_per_sku=5,
            max_distinct_agents_per_principal=2,
        )
        self.assertFalse(res_fanout.allowed)
        self.assertEqual(res_fanout.decision_code, "SYBIL_SWARM_AGENT_FANOUT_EXCEEDED")

        # Re-using an existing agent when principal quota (2 units) is full trips PRINCIPAL_SCARCITY_QUOTA_EXCEEDED
        req_over_qty = self._build_signed_request(
            nonce="n_sybil_4",
            agent_instance_id="agent_1",
            requested_qty=1,
        )
        res_over_qty = verify_rfc9421_agent_attestation_and_quota(
            req_over_qty,
            now_epoch=1015,
            directory_registry=self.registry,
            seen_nonces=nonces,
            principal_sku_ledger=ledger,
            principal_agent_set=agents,
            max_qty_per_principal_per_sku=2,
            max_distinct_agents_per_principal=3,
        )
        self.assertFalse(res_over_qty.allowed)
        self.assertEqual(res_over_qty.decision_code, "PRINCIPAL_SCARCITY_QUOTA_EXCEEDED")

    def test_demo_and_cli_exit_zero(self) -> None:
        summary = run_demo()
        self.assertTrue(summary["attested_agent_admitted"])
        self.assertTrue(summary["sybil_over_quota_blocked"])
        self.assertEqual(main([]), 0)


if __name__ == "__main__":
    unittest.main()
