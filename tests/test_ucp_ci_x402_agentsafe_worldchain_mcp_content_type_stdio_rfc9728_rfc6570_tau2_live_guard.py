"""Unit tests for Stage 218 deterministic guard module (`PR-01..PR-16`)."""

from __future__ import annotations

import unittest

from lab.ucp_ci_x402_agentsafe_worldchain_mcp_content_type_stdio_rfc9728_rfc6570_tau2_live_guard import (
    SCENARIO_EVALUATORS,
    evaluate_stage218_scenario,
)


def build_valid_payloads() -> dict[str, dict]:
    return {
        "PR-01": {
            "prettier_schema_check_passed": True,
            "git_blame_ignore_revs_present": True,
            "fast_uri_version": (3, 1, 8),
            "workflow_action_refs": [
                "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
                "actions/github-script@60a0d83039c74a4aee543508d2ffcb1c3799cdea",
            ],
            "readonly_checkout_persists_credentials": False,
            "workflow_token_permissions": "contents:read",
        },
        "PR-02": {
            "kill_switch_active": False,
            "origin_pinned_payee": "0x2222222222222222222222222222222222222222",
            "challenge_pay_to": "0x2222222222222222222222222222222222222222",
            "call_amount_minor": 1500,
            "max_per_call_minor": 5000,
            "session_spent_minor": 10000,
            "session_budget_minor": 50000,
            "auth_window_seconds": 60,
            "max_auth_window_seconds": 300,
        },
        "PR-03": {
            "network": "eip155:480",
            "asset_address": "0x79A02482A880bCE3F13e09Da970dC34db4CD24d1",
            "decimals": 6,
            "eip712_name": "USDC",
            "eip712_version": "2",
            "pay_to": "0x3333333333333333333333333333333333333333",
            "inam_extension": {
                "linked_address": "0x3333333333333333333333333333333333333333",
                "receipt_history_score": 95,
                "min_required_score": 80,
            },
        },
        "PR-04": {
            "chain_family": "solana",
            "payer_on_ofac_sdn_list": False,
            "payee_on_ofac_sdn_list": False,
            "sdk_distributions": {
                "python": ["LICENSE", "NOTICE", "pyproject.toml"],
                "typescript": ["LICENSE", "NOTICE", "package.json"],
                "go": ["LICENSE", "NOTICE", "go.mod"],
            },
        },
        "PR-05": {
            "content_type_header": "Application/JSON; Charset=UTF-8",
            "transport_accepted_content_type": True,
            "body_is_valid_jsonrpc_request": False,
            "non_request_jsonrpc_error_code": -32600,
        },
        "PR-06": {
            "catalog_is_static": True,
            "opt_out_subscriptions_listen": True,
            "advertises_subscriptions_listen": False,
            "generic_context_has_live_request_context": True,
        },
        "PR-07": {
            "progress_callback_raised": True,
            "tool_execution_aborted_by_progress_callback": False,
            "single_post_transport_error_occurred": True,
            "session_kept_alive_after_post_error": True,
            "single_post_error_code": "CONNECTION_CLOSED",
        },
        "PR-08": {
            "peer_holds_stdin_open": True,
            "stdio_server_exited_without_hanging": True,
            "safe_join_rejected_symlink_or_junction_escape": True,
        },
        "PR-09": {
            "image_mime_type": "image/jpeg",
            "audio_mime_type": "audio/mpeg",
            "raw_scope_header": "read,write read offline_access",
            "union_scopes_result": ["offline_access", "read", "write"],
        },
        "PR-10": {
            "configured_tools_list_changed": False,
            "effective_tools_list_changed_after_register": False,
            "registered_resource_uri": "https://example.com",
            "resource_read_lookup_key": "https://example.com",
        },
        "PR-11": {
            "peak_stdin_drain_listeners": 1,
            "listeners_remaining_after_close": 0,
            "references_dom_only_headers_init": False,
        },
        "PR-12": {
            "uses_deprecated_skills_attach": False,
            "skills_extension_has_setup_fn": True,
            "registered_extension_ids": ["io.modelcontextprotocol/skills"],
        },
        "PR-13": {
            "resource_url": "https://server.com/resource/",
            "computed_protected_resource_metadata_url": "https://server.com/.well-known/oauth-protected-resource/resource/",
            "ajv_custom_options_preserved_dialect_dispatch": True,
        },
        "PR-14": {
            "event_bus_preserved_forwarded_meta": True,
            "filtered_by_authoritative_resource_uri": True,
            "undeclared_spec_handler_params_retained": [],
        },
        "PR-15": {
            "expansions": {
                "{x,half,y}": "1024,50%25,768",
                "{/who,dub}": "/fred/me%2Ftoo",
                "{.who,who}": ".fred.fred",
                "X{.list}": "X.red,green,blue",
                "{/list}": "/red,green,blue",
            }
        },
        "PR-16": {
            "openai_live_prompt_template_id": "openai-live-default-v1.0",
            "elicitation_evidence_link_reachable": True,
            "elicitation_figure_render_deterministic": True,
        },
    }


def build_adversarial_payloads() -> dict[str, dict]:
    valid = build_valid_payloads()
    return {
        "PR-01": {**valid["PR-01"], "workflow_action_refs": ["actions/checkout@v5"]},
        "PR-02": {**valid["PR-02"], "challenge_pay_to": "0x9999999999999999999999999999999999999999"},
        "PR-03": {
            **valid["PR-03"],
            "inam_extension": {**valid["PR-03"]["inam_extension"], "linked_address": "0xdeadbeef"},
        },
        "PR-04": {**valid["PR-04"], "payer_on_ofac_sdn_list": True},
        "PR-05": {**valid["PR-05"], "non_request_jsonrpc_error_code": -32602},
        "PR-06": {**valid["PR-06"], "generic_context_has_live_request_context": False},
        "PR-07": {**valid["PR-07"], "tool_execution_aborted_by_progress_callback": True},
        "PR-08": {**valid["PR-08"], "stdio_server_exited_without_hanging": False},
        "PR-09": {**valid["PR-09"], "image_mime_type": "image/jpg"},
        "PR-10": {**valid["PR-10"], "effective_tools_list_changed_after_register": True},
        "PR-11": {**valid["PR-11"], "peak_stdin_drain_listeners": 11},
        "PR-12": {
            **valid["PR-12"],
            "registered_extension_ids": ["io.modelcontextprotocol/skills", "io.modelcontextprotocol/skills"],
        },
        "PR-13": {
            **valid["PR-13"],
            "computed_protected_resource_metadata_url": "https://server.com/.well-known/oauth-protected-resource/resource",
        },
        "PR-14": {**valid["PR-14"], "undeclared_spec_handler_params_retained": ["injectedField"]},
        "PR-15": {
            **valid["PR-15"],
            "expansions": {**valid["PR-15"]["expansions"], "X{.list}": "X.red.green.blue"},
        },
        "PR-16": {**valid["PR-16"], "openai_live_prompt_template_id": "adhoc-unversioned"},
    }


class TestStage218Guard(unittest.TestCase):
    def test_all_16_valid_scenarios_pass(self) -> None:
        valid = build_valid_payloads()
        self.assertEqual(len(valid), 16)
        for scenario_id, payload in valid.items():
            verdict = evaluate_stage218_scenario(scenario_id, payload)
            self.assertTrue(verdict.passed, f"{scenario_id} should pass: {verdict}")
            self.assertEqual(verdict.action, "Act automatically")

    def test_all_16_adversarial_scenarios_blocked(self) -> None:
        adversarial = build_adversarial_payloads()
        self.assertEqual(len(adversarial), 16)
        for scenario_id, payload in adversarial.items():
            verdict = evaluate_stage218_scenario(scenario_id, payload)
            self.assertFalse(verdict.passed, f"{scenario_id} should be blocked: {verdict}")
            self.assertEqual(verdict.action, "Send to a human")

    def test_evaluator_registry_completeness(self) -> None:
        expected = [f"PR-{i:02d}" for i in range(1, 17)]
        self.assertEqual(list(SCENARIO_EVALUATORS.keys()), expected)


if __name__ == "__main__":
    unittest.main()
