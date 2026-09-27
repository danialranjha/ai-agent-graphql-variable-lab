import json
import unittest
from experiment import CRAFTED, FIXTURES, ROOT, fixed_contract, load_function, mutations, run, run_case

class BoundaryTests(unittest.TestCase):
    def test_original_adds_marker_but_fixed_does_not(self):
        old = run_case("original", "marker", CRAFTED)
        new = run_case("fixed", "marker", CRAFTED)
        self.assertEqual(old["root_fields"], [
            {"field": "export", "response_key": "export"},
            {"field": "__typename", "response_key": "marker"},
            {"field": "export", "response_key": "spare"}])
        self.assertEqual(old["data"]["marker"], "Query")
        self.assertEqual(old["resolver_ids"], ["demo", "demo"])
        self.assertTrue(fixed_contract(new, CRAFTED))
        self.assertNotIn("marker", new["data"])

    def test_ordinary_twin(self):
        a = run_case("original", "ordinary", "demo")
        b = run_case("fixed", "ordinary", "demo")
        self.assertEqual(a["data"], b["data"])
        self.assertEqual(a["function_result"], b["function_result"])
        self.assertEqual(a["resolver_ids"], ["demo"])

    def test_fixed_preserves_every_fixture_as_one_identifier(self):
        queries = set()
        for label, identifier in FIXTURES:
            with self.subTest(label=label):
                r = run_case("fixed", label, identifier)
                self.assertTrue(fixed_contract(r, identifier))
                queries.add(r["request"]["query"])
        self.assertEqual(len(queries), 1)

    def test_quote_parse_error_has_no_resolver_effect(self):
        r = run_case("original", "quote", 'demo"note')
        self.assertFalse(r["parse_ok"])
        self.assertEqual(r["resolver_ids"], [])
        self.assertIsNone(r["data"])

    def test_backslash_changes_original_identifier(self):
        value = r"demo\nnext"
        a = run_case("original", "escape", value)
        b = run_case("fixed", "escape", value)
        self.assertEqual(a["resolver_ids"], ["demo\nnext"])
        self.assertEqual(b["resolver_ids"], [value])

    def test_parameterization_does_not_authorize_id(self):
        r = run_case("fixed", "unknown", "nonexistent-export")
        self.assertTrue(fixed_contract(r, "nonexistent-export"))
        self.assertEqual(r["data"]["export"]["id"], "nonexistent-export")

    def test_critical_regressions_are_detected(self):
        m = mutations()
        self.assertTrue(m["all_detected"])
        self.assertEqual(len(m["checks"]), 2)

    def test_artifact_matches_fresh_run(self):
        self.assertEqual(json.loads((ROOT / "artifacts/run.json").read_text()), run())

if __name__ == "__main__":
    unittest.main()
