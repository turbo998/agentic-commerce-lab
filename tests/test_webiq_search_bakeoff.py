import unittest

from lab.webiq_search_bakeoff import assert_not_fabricated, summarize


class WebIQSearchBakeoffTests(unittest.TestCase):
    def test_missing_credentials_stay_not_measured(self):
        report = summarize({})
        self.assertFalse(report["measured"])
        self.assertEqual(len(report["queries"]), 3)
        self.assertEqual(
            [row["provider"] for row in report["providers"]],
            ["webiq", "brightdata", "exa", "tavily", "parallel"],
        )
        for row in report["providers"]:
            self.assertEqual(row["credential"], "absent")
            self.assertEqual(row["latency"], "not_measured")
            self.assertNotIn("latency_ms", row)
        assert_not_fabricated(report)

    def test_present_key_is_not_called_and_not_scored(self):
        report = summarize({"WEBIQ_API_KEY": "present-but-not-used", "EXA_API_KEY": "x"})
        by_name = {row["provider"]: row for row in report["providers"]}
        self.assertEqual(by_name["webiq"]["credential"], "present")
        self.assertEqual(by_name["exa"]["credential"], "present")
        self.assertEqual(by_name["webiq"]["call"], "not_called")
        self.assertEqual(by_name["webiq"]["latency"], "not_measured")
        self.assertEqual(by_name["brightdata"]["credential"], "absent")
        self.assertNotIn("latency_ms", report["official_list_price"]["webiq"])
        self.assertEqual(report["official_list_price"]["webiq"]["per_1k_usd"]["web"], 7.0)
        self.assertEqual(report["official_list_price"]["brightdata"]["payg_usd_per_1k_successful"], 1.5)
        self.assertEqual(report["seven_card"], "withheld_until_measured_latency_exists")

    def test_blank_key_is_absent(self):
        report = summarize({"WEBIQ_API_KEY": "   "})
        self.assertEqual(report["providers"][0]["credential"], "absent")


if __name__ == "__main__":
    unittest.main()
