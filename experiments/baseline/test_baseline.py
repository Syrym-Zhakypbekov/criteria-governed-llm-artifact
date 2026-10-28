"""Offline contract, trace, statistical-parity and unchanged-file tests."""
import ast
import copy
import hashlib
import json
import math
import unittest

import baseline_schema as b


VALID = {
    "supplier": {"name": "Test", "bin": "123456789012", "address": "", "phone": "",
                 "email": "test@example.org", "iban": "", "bank": "", "bik": "", "director": ""},
    "contract": {"number": "", "date": "", "basis": "", "vat_rate": 16, "with_vat": True,
                 "kind": "goods", "from": "", "until": "", "addendum": None},
    "items": [{"name": "Item", "description": "", "qty": 2, "unit": "piece",
               "unit_price_with_vat": 2.5, "ktru_hints": []}],
    "third_party": None,
}
PARTY = {"fio": "Person", "iin": "123456789012", "email": "p@example.org", "phone": "", "role": ""}
ADDENDUM = {"base_number": "A-1", "base_date": "2024-02-29"}


class BaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expect = b.load_expect((b.ABLATION / "ablation_replay.ts").read_text(encoding="utf-8"))

    def setUp(self):
        self.raw = copy.deepcopy(VALID)

    def traced(self, raw, defects, baseline="B1"):
        return b.evaluate_trace(b.baselines(raw)[baseline], defects, self.expect)

    def test_valid_and_no_mutation(self):
        before = copy.deepcopy(self.raw)
        result = b.baselines(self.raw)
        self.assertFalse(result["B1"]["routed"])
        self.assertFalse(result["B2"]["routed"])
        self.assertEqual(self.raw, before)

    def test_strict_numeric_fields(self):
        for key, obj in [("qty", "item"), ("unit_price_with_vat", "item"), ("vat_rate", "contract")]:
            for bad in ["2450", "2.5", "", True, False, None, [], {}]:
                with self.subTest(key=key, bad=bad):
                    raw = copy.deepcopy(VALID)
                    (raw["items"][0] if obj == "item" else raw["contract"])[key] = bad
                    self.assertTrue(b.baselines(raw)["B1"]["routed"])

    def test_strict_boolean(self):
        for bad in [0, 1, "true", "false", None]:
            self.raw["contract"]["with_vat"] = bad
            self.assertTrue(b.baselines(self.raw)["B1"]["routed"])

    def test_bin_no_coercion(self):
        for bad in [123456789012, "12345678901", "1234567890123", "", " 123456789012", "123-456789012"]:
            self.raw["supplier"]["bin"] = bad
            self.assertTrue(self.traced(self.raw, ["bin_short"])["traced"])

    def test_price_zero_vs_negative(self):
        self.raw["items"][0]["unit_price_with_vat"] = 0
        result = b.baselines(self.raw)
        self.assertFalse(result["B1"]["routed"])
        self.assertTrue(result["B2"]["routed"])
        self.raw["items"][0]["unit_price_with_vat"] = -1
        self.assertTrue(b.baselines(self.raw)["B1"]["routed"])

    def test_vat_no_domain_condition(self):
        self.raw["contract"]["vat_rate"] = 0
        self.assertFalse(b.baselines(self.raw)["B2"]["routed"])
        for rate in [7.5, 12, 16, 100]:
            self.raw["contract"]["vat_rate"] = rate
            self.assertFalse(b.baselines(self.raw)["B2"]["routed"])
        for rate in [-1, 101]:
            self.raw["contract"]["vat_rate"] = rate
            self.assertFalse(b.baselines(self.raw)["B1"]["routed"])
            self.assertTrue(b.baselines(self.raw)["B2"]["routed"])

    def test_email_formats(self):
        for value in ["", "not-an-email"]:
            self.raw["supplier"]["email"] = value
            self.assertTrue(b.baselines(self.raw)["B1"]["routed"])
        self.raw["supplier"]["email"] = "user@localhost"
        result = b.baselines(self.raw)
        self.assertFalse(result["B1"]["routed"])
        self.assertTrue(result["B2"]["routed"])

    def test_dates(self):
        for value in ["", "2024-02-29", "2026-10-28"]:
            self.raw["contract"]["date"] = value
            self.assertFalse(b.baselines(self.raw)["B1"]["routed"])
        for value in ["2026-02-29", "28.10.2026", "20261028", "2026-1-1", None, "2026-10-28T00:00:00Z"]:
            self.raw["contract"]["date"] = value
            self.assertTrue(b.baselines(self.raw)["B1"]["routed"])

    def test_nonempty_and_optional_fields(self):
        self.raw["supplier"]["name"] = "   "
        self.assertFalse(b.baselines(self.raw)["B1"]["routed"])
        self.assertTrue(b.baselines(self.raw)["B2"]["routed"])
        self.assertFalse(b.baselines(copy.deepcopy(VALID))["B2"]["routed"])

    def test_nullable_objects_and_required_children(self):
        self.raw["third_party"] = copy.deepcopy(PARTY)
        self.raw["contract"]["addendum"] = copy.deepcopy(ADDENDUM)
        self.assertFalse(b.baselines(self.raw)["B2"]["routed"])
        del self.raw["third_party"]["email"]
        result = self.traced(self.raw, ["third_party"])
        self.assertIn("third_party.email", result["failing_fields"])
        self.assertTrue(result["traced"])
        self.raw["third_party"] = None
        del self.raw["contract"]["addendum"]["base_number"]
        self.assertTrue(self.traced(self.raw, ["addendum_nobase"])["traced"])

    def test_empty_addendum_b2_only(self):
        self.raw["contract"]["addendum"] = {"base_number": "", "base_date": ""}
        self.assertFalse(b.baselines(self.raw)["B1"]["routed"])
        self.assertTrue(self.traced(self.raw, ["addendum_nobase"], "B2")["traced"])

    def test_parent_failures_not_invented_child_traces(self):
        del self.raw["supplier"]
        result = self.traced(self.raw, ["bin_missing"])
        self.assertTrue(result["routed"])
        self.assertFalse(result["traced"])

    def test_compound_requires_every_planted_defect(self):
        self.raw["supplier"]["bin"] = ""
        self.raw["items"][0]["unit_price_with_vat"] = 0
        self.assertFalse(self.traced(self.raw, ["bin_missing", "no_price"])["traced"])
        self.assertTrue(self.traced(self.raw, ["bin_missing", "no_price"], "B2")["traced"])
        self.raw["contract"]["vat_rate"] = 0
        self.assertFalse(self.traced(self.raw, ["bin_missing", "no_price", "vat_no_rate"], "B2")["traced"])

    def test_unrelated_error_cannot_trace(self):
        self.raw["unexpected"] = 1
        result = self.traced(self.raw, ["no_price"])
        self.assertTrue(result["routed"])
        self.assertFalse(result["traced"])

    def test_empty_items_and_unknown_defect(self):
        self.raw["items"] = []
        self.assertTrue(self.traced(self.raw, ["no_items"])["traced"])
        with self.assertRaises(ValueError):
            self.traced(self.raw, ["new_unknown_label"])

    def test_absent_raw_fail_closed_without_trace(self):
        result = self.traced(None, ["bin_missing"])
        self.assertTrue(result["routed"])
        self.assertFalse(result["traced"])

    def test_totals_boundary_and_decimal(self):
        for value, passed in [(5, True), (4, True), (6, True), (3.99, False), (6.01, False)]:
            self.raw["total"] = value
            result = b.baselines(self.raw)
            self.assertFalse(result["B1"]["routed"])
            self.assertEqual(not result["B2"]["routed"], passed)
            self.assertEqual(result["B2"]["totals_check"]["status"], "passed" if passed else "failed")
        self.raw["items"][0].update(qty=3, unit_price_with_vat=0.1)
        self.raw["total"] = 0.3
        self.assertEqual(b.baselines(self.raw)["B2"]["totals_check"]["checks"][0]["absolute_difference"], "0.0")

    def test_totals_missing_invalid_and_two_locations(self):
        self.assertEqual(b.baselines(self.raw)["B2"]["totals_check"]["status"], "not_applicable")
        self.raw["total"] = "5"
        result = b.baselines(self.raw)
        self.assertTrue(result["B1"]["routed"])
        self.assertEqual(result["B2"]["totals_check"]["status"], "not_evaluable")
        self.raw["total"] = 5
        self.raw["contract"]["total"] = 20
        self.assertTrue(b.baselines(self.raw)["B2"]["routed"])
        self.raw["contract"]["total"] = None
        self.assertFalse(b.baselines(self.raw)["B2"]["routed"])

    def test_mutation_matrix_schema_equivalence(self):
        specimen = copy.deepcopy(VALID)
        specimen["third_party"] = copy.deepcopy(PARTY)
        specimen["contract"]["addendum"] = copy.deepcopy(ADDENDUM)
        def paths(value, prefix=()):
            yield prefix
            if isinstance(value, dict):
                for k,v in value.items():
                    yield from paths(v,prefix+(k,))
            elif isinstance(value, list):
                for k,v in enumerate(value):
                    yield from paths(v,prefix+(k,))
        trials = 0
        for path in paths(specimen):
            for value in [None, False, True, 0, 1, -1, 1.5, "", "1", "bad", [], {}]:
                raw = copy.deepcopy(specimen)
                if not path:
                    raw = value
                else:
                    parent = raw
                    for part in path[:-1]:
                        parent = parent[part]
                    parent[path[-1]] = value
                pe, je = b.schema_errors(raw)  # raises on acceptance disagreement
                self.assertEqual(bool(pe), bool(je))
                trials += 1
        self.assertGreater(trials, 400)

    def test_stats_edge_cases(self):
        self.assertEqual(b.mcnemar_midp([True], [True]), (0,0,1.0))
        self.assertEqual(b.mcnemar_midp([True]*4,[False]*4), (0,4,0.0625))
        self.assertEqual(b.mcnemar_midp([True,False],[False,True]), (1,1,1.0))
        self.assertEqual(b.holm([.01,.03,.04]), [.03,.06,.06])
        with self.assertRaises(ValueError):
            b.mcnemar_midp([True], [])

    def test_original_scipy_statistics_parity(self):
        try:
            import scipy  # noqa: F401
        except ImportError:
            self.skipTest("Optional SciPy reference check; not a baseline dependency")
        source = (b.ABLATION/"ablation_stats.py").read_text(encoding="utf-8")
        module = ast.parse(source)
        selected = [n for n in module.body if isinstance(n,ast.ImportFrom)
                    or isinstance(n,ast.FunctionDef) and n.name in {"cp","mcnemar_midp","holm"}]
        namespace = {}
        exec(compile(ast.Module(body=selected,type_ignores=[]),"original_stats_functions","exec"),namespace)
        for n in [8,10,28,33,36,43]:
            for k in range(n+1):
                self.assertEqual(b.cp(k,n),list(namespace["cp"](k,n)))
        for n in range(44):
            for k in range(n+1):
                a, c = [True]*k+[False]*(n-k), [False]*k+[True]*(n-k)
                actual, expected = b.mcnemar_midp(a,c), namespace["mcnemar_midp"](a,c)
                self.assertEqual(actual[:2],expected[:2])
                self.assertTrue(math.isclose(actual[2],expected[2],rel_tol=1e-12,abs_tol=1e-15))
        ps = [.03,.0002,1,.06,.06]
        self.assertEqual(b.holm(ps),namespace["holm"](ps))

    def test_all_frozen_records_and_result_hashes(self):
        results = json.loads((b.HERE/"baseline_results.json").read_text(encoding="utf-8"))
        self.assertEqual(len(results["documents"]),244)
        self.assertEqual(len(results["summary"]),6)
        for rec in results["summary"]:
            self.assertTrue(rec["reference_reproduced"])
            self.assertEqual(rec["totals_check_status"],{"not_applicable":rec["n_documents"]})
        for path,sha in results["input_sha256"].items():
            self.assertEqual(hashlib.sha256((b.ROOT/path).read_bytes()).hexdigest(),sha,path)

    def test_preexisting_files_unchanged(self):
        before = json.loads((b.HERE/"preexisting_files.sha256.json").read_text(encoding="utf-8"))
        after = {f.relative_to(b.ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest()
                 for f in b.ROOT.rglob("*") if f.is_file() and ".git" not in f.relative_to(b.ROOT).parts
                 and not f.is_relative_to(b.HERE)}
        self.assertEqual(before,after,"Existing files changed or new files exist outside baseline")


if __name__ == "__main__":
    unittest.main(verbosity=2)
