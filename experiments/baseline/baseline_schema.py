"""Offline external baselines. Only raw model JSON enters B1/B2 validators.

Run with Python 3.11+: python -B experiments/baseline/baseline_schema.py
All writes are confined to this file's directory; no model/network calls.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import platform
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Literal

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ABLATION = ROOT / "experiments/ablation"
MODELS = ("gemini-3.8-flash", "gemini-3.1-flash-lite")
SETS = ("dev", "holdout", "holdout2")
PAIRS = (("B1", "C2"), ("B1", "C4"), ("B2", "C4"))
FORMATS = FormatChecker(formats=["email", "date"])
INPUTS: dict[str, str] = {}


def read_input(path: Path) -> str:
    data = path.read_bytes()
    INPUTS[path.relative_to(ROOT).as_posix()] = hashlib.sha256(data).hexdigest()
    return data.decode("utf-8-sig")


def load_input(path: Path) -> Any:
    return json.loads(read_input(path))


def email_format(value: str) -> str:
    if not FORMATS.conforms(value, "email"):
        raise ValueError("invalid email format")
    return value


def optional_date_format(value: str) -> str:
    # Empty string is the extraction contract's explicit missing-value sentinel.
    if value != "" and not FORMATS.conforms(value, "date"):
        raise ValueError("expected empty string or ISO YYYY-MM-DD calendar date")
    return value


Email = Annotated[str, AfterValidator(email_format), Field(json_schema_extra={"format": "email"})]
OptionalDate = Annotated[
    str, AfterValidator(optional_date_format),
    Field(json_schema_extra={"anyOf": [{"const": ""}, {"type": "string", "format": "date"}]}),
]
Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Nonnegative = Annotated[Number, Field(ge=0)]
Bin = Annotated[str, Field(pattern=r"^\d{12}$")]


class StrictObject(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", regex_engine="python-re")


class Supplier(StrictObject):
    name: str
    bin: Bin
    address: str
    phone: str
    email: Email
    iban: str
    bank: str
    bik: str
    director: str


class Addendum(StrictObject):
    base_number: str
    base_date: OptionalDate


class ThirdParty(StrictObject):
    fio: str
    iin: str
    email: Email
    phone: str
    role: str


class Contract(StrictObject):
    number: str
    date: OptionalDate
    basis: str
    # No VAT enum is declared in apex_jrd_frozen.ts or src/jrd-extract.ts.
    # Prompt examples 0, 12, 16 are not an exhaustive type declaration.
    vat_rate: Number
    with_vat: bool
    kind: Literal["goods", "services", "works"]
    from_: OptionalDate = Field(alias="from")
    until: OptionalDate
    addendum: Addendum | None
    total: Nonnegative | None = None


class Item(StrictObject):
    name: str
    description: str
    qty: Number
    unit: str
    unit_price_with_vat: Nonnegative
    ktru_hints: list[str]


class Extraction(StrictObject):
    supplier: Supplier
    contract: Contract
    items: Annotated[list[Item], Field(min_length=1)]
    third_party: ThirdParty | None
    # Optional extension for an independently extracted total. It is absent in
    # every frozen raw output. Never substitute truth.total or a derived total.
    total: Nonnegative | None = None


SCHEMA = Extraction.model_json_schema(by_alias=True)
SCHEMA["$schema"] = "https://json-schema.org/draft/2020-12/schema"
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FORMATS)


def field_path(parts) -> str:
    result = ""
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else ("." if result else "") + str(part)
    return result or "$"


def schema_errors(raw: Any) -> tuple[list[dict], list[dict]]:
    """Run both libraries; require agreement, retaining their original errors.

    JSON Schema gives canonical raw field paths, including inside nullable
    object unions. A parent-object failure is not expanded into imaginary leaf
    failures. Required errors name the actual missing field.
    """
    try:
        Extraction.model_validate(raw, strict=True)
        pe = []
    except ValidationError as exc:
        pe = [{"field": field_path(e["loc"]), "rule": e["type"], "message": e["msg"]}
              for e in exc.errors(include_url=False, include_context=False, include_input=False)]

    def unpack(error):
        if error.validator == "anyOf" and error.context:
            # Nullable-object union's failed null branch is incidental; retain
            # object failures, including required-property errors at the parent.
            relevant = [c for c in error.context
                        if not (c.validator == "type" and c.validator_value == "null")]
            if relevant:
                return [e for child in relevant for e in unpack(child)]
        if error.validator == "required" and isinstance(error.instance, dict):
            # iter_errors returns one error per missing property; parse its
            # message, then confirm against the schema's required properties.
            missing = [key for key in error.validator_value if key not in error.instance
                       and error.message == f"{key!r} is a required property"]
            return [{"field": field_path([*error.absolute_path, key]), "rule": "required",
                     "message": error.message} for key in missing]
        return [{"field": field_path(error.absolute_path), "rule": str(error.validator),
                 "message": error.message}]

    je = [e for error in VALIDATOR.iter_errors(raw) for e in unpack(error)]
    if bool(pe) != bool(je):
        raise AssertionError(f"Pydantic/JSON Schema acceptance mismatch: {pe!r} / {je!r}")
    return pe, je


def numeric(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def guardrail_errors(raw: Any) -> tuple[list[dict], dict]:
    """Reusable range/non-empty/regex/arithmetic checks, no labels or source."""
    failures = []

    def fail(path, rule, message):
        failures.append({"field": path, "rule": rule, "message": message})

    def nonempty(obj, fields, prefix):
        if isinstance(obj, dict):
            for key in fields:
                if key in obj and isinstance(obj[key], str) and not obj[key].strip():
                    fail(f"{prefix}.{key}", "non_empty", "must contain a non-whitespace character")

    def email_regex(obj, prefix):
        if isinstance(obj, dict) and isinstance(obj.get("email"), str):
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", obj["email"]):
                fail(f"{prefix}.email", "regex", "expected local@domain.suffix without whitespace")

    totals = {"status": "not_applicable", "reason": "no independently extracted total"}
    if not isinstance(raw, dict):
        return failures, totals
    supplier = raw.get("supplier")
    nonempty(supplier, ["name", "email"], "supplier")
    email_regex(supplier, "supplier")
    party = raw.get("third_party")
    nonempty(party, ["fio", "email"], "third_party")
    email_regex(party, "third_party")
    contract = raw.get("contract")
    if isinstance(contract, dict):
        nonempty(contract.get("addendum"), ["base_number", "base_date"], "contract.addendum")
        vat = contract.get("vat_rate")
        if numeric(vat) and not 0 <= vat <= 100:
            fail("contract.vat_rate", "valid_range", "must be in [0, 100]")
    items = raw.get("items")
    if isinstance(items, list):
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            nonempty(item, ["name", "unit"], f"items[{i}]")
            for key in ["qty", "unit_price_with_vat"]:
                if numeric(item.get(key)) and item[key] <= 0:
                    fail(f"items[{i}].{key}", "valid_range", "must be greater than zero")
    supplied = [("total", raw.get("total"))]
    if isinstance(contract, dict):
        supplied.append(("contract.total", contract.get("total")))
    supplied = [(path, value) for path, value in supplied if value is not None]
    if supplied:
        usable = (isinstance(items, list) and bool(items) and all(
            isinstance(i, dict) and numeric(i.get("qty")) and numeric(i.get("unit_price_with_vat"))
            for i in items) and all(numeric(v) for _, v in supplied))
        if not usable:
            totals = {"status": "not_evaluable", "reason": "invalid or absent arithmetic operands"}
        else:
            calculated = sum(Decimal(str(i["qty"])) * Decimal(str(i["unit_price_with_vat"])) for i in items)
            checks = []
            for path, value in supplied:
                delta = abs(calculated - Decimal(str(value)))
                passed = delta <= Decimal("1")
                checks.append({"field": path, "calculated": str(calculated), "reported": str(value),
                               "absolute_difference": str(delta), "passed": passed})
                if not passed:
                    fail(path, "totals", "abs(sum(qty * unit_price_with_vat) - total) must be <= 1 KZT")
            totals = {"status": "passed" if all(c["passed"] for c in checks) else "failed", "checks": checks}
    return failures, totals


def failure_codes(errors: list[dict]) -> list[str]:
    """Field -> replay criterion aliases; no source evidence codes are awarded."""
    codes = set()
    direct = {"supplier.bin": "bin", "items": "items", "contract.vat_rate": "vat_explicit",
              "third_party.email": "third_party_email", "contract.addendum.base_number": "addendum_base",
              "contract.addendum.base_date": "addendum_base"}
    for error in errors:
        field = error["field"]
        if field in direct:
            codes.add(direct[field])
        if re.fullmatch(r"items\[\d+\]\.unit_price_with_vat", field):
            codes.add("prices")
    return sorted(codes)


def baselines(raw: Any) -> dict:
    # This API deliberately cannot access r.text, r.truth, r.draft, or r.defects.
    pe, je = schema_errors(raw)
    ge, totals = guardrail_errors(raw)
    result = {}
    for name, errors in (("B1", je), ("B2", je + ge)):
        result[name] = {"state": "escalated" if errors else "provisional", "routed": bool(errors),
                        "codes": failure_codes(errors), "failing_fields": sorted({e["field"] for e in errors}),
                        "errors": errors}
    result["B1"]["pydantic_errors"] = pe
    result["B2"]["totals_check"] = totals
    return result


def load_expect(source: str) -> dict[str, list[str]]:
    block = re.search(r"const EXPECT: Record<string, string\[\]> = \{(.*?)\n\};", source, re.S)
    if not block:
        raise ValueError("Cannot locate replay EXPECT mapping")
    return {key: json.loads(values) for key, values in re.findall(r'(\w+):\s*(\[(?:"[^"]*"\s*,?\s*)*\])', block[1])}


def evaluate_trace(result: dict, defects: list[str], expect: dict) -> dict:
    if any(d not in expect for d in defects):
        raise ValueError(f"Unknown defect label: {defects}")
    result["traced"] = (all(set(expect[d]) & set(result["codes"]) for d in defects)
                        if defects and result["routed"] else None)
    return result


def replay_c2_c4(record: dict, expect: dict) -> dict:
    """Independent Python replay of C2/C4 on frozen raw + frozen draft.

    This reference path is separate from the baseline validators. All results
    must equal the archived per-document states/codes/route/trace before use.
    """
    if record.get("error") or not record.get("draft"):
        return {c: evaluate_trace({"state": "error", "codes": [], "routed": False}, record["defects"], expect)
                for c in ["C2", "C4"]}
    raw, d = record["raw"], record["draft"]
    sf = []
    nonempty = lambda x: isinstance(x, str) and bool(x.strip())
    if not isinstance(raw, dict):
        sf = ["schema:root"]
    else:
        supplier = raw.get("supplier")
        if not isinstance(supplier, dict):
            sf.append("schema:supplier")
        else:
            if not nonempty(supplier.get("name")):
                sf.append("schema:supplier.name")
            if not str(supplier.get("bin") if supplier.get("bin") is not None else "").strip():
                sf.append("schema:supplier.bin")
        if not isinstance(raw.get("contract"), dict):
            sf.append("schema:contract")
        items = raw.get("items")
        if not isinstance(items, list) or not items:
            sf.append("schema:items")
        else:
            for i, item in enumerate(items):
                item = item if isinstance(item, dict) else {}
                if not nonempty(item.get("name")):
                    sf.append(f"schema:items[{i}].name")
                price = item.get("unit_price_with_vat")
                if not (numeric(price) or (nonempty(price) and re.search(r"[0-9]", price))):
                    sf.append(f"schema:items[{i}].price")
    c2 = {"state": "escalated" if sf else "provisional", "codes": sf.copy()}
    items = d["items"]
    ad, tp = d["contract"]["addendum"], d["thirdParty"]
    # Exactly the declaration order/weights in jrdCriteria, threshold 0.9.
    hard = [("bin", bool(re.fullmatch(r"[0-9]{12}", d["supplier"]["bin"]))), ("items", bool(items))]
    soft = [
        ("prices", sum(i["unitPriceWithVat"] > 0 for i in items) / len(items) if items else 0, 3),
        ("vat_explicit", int(not any(w.startswith("Ставка НДС") for w in d["warnings"])), 1),
        ("supplier_name", int(bool(d["supplier"]["name"])), 1),
        ("signer_email", int(bool(d["supplier"]["email"])), 1),
        ("addendum_base", int(not (ad is not None and not (ad["baseNumber"] and ad["baseDate"]))), 2),
        ("third_party_email", int(not (tp is not None and not tp["email"])), 1),
    ]
    bad_hard = [name for name, ok in hard if not ok]
    bad_soft = [name for name, score, _ in soft if score < 1]
    score = sum(s * w for _, s, w in soft) / sum(w for _, _, w in soft)
    state = "vetoed" if bad_hard else "escalated" if score < 0.9 else "provisional"
    codes = bad_hard + bad_soft
    c4 = ({"state": "escalated", "codes": sf.copy()} if state == "provisional" and sf
          else {"state": state, "codes": codes + sf})
    for result in (c2, c4):
        result["routed"] = result["state"] in ("escalated", "vetoed")
        evaluate_trace(result, record["defects"], expect)
    return {"C2": c2, "C4": c4}


def mcnemar_midp(a: list[bool], b: list[bool]) -> tuple[int, int, float]:
    if len(a) != len(b):
        raise ValueError("Paired arrays differ in length")
    n01 = sum(not x and y for x, y in zip(a, b))
    n10 = sum(x and not y for x, y in zip(a, b))
    n = n01 + n10
    k = min(n01, n10)
    # Algebraically identical to 2*binom.cdf(k,n,.5)-binom.pmf(k,n,.5).
    p = min(1.0, (2 * sum(math.comb(n, j) for j in range(k + 1)) - math.comb(n, k)) / 2**n) if n else 1.0
    return n01, n10, p


def holm(ps: list[float]) -> list[float]:
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(sorted(range(len(ps)), key=ps.__getitem__)):
        run = max(run, (len(ps) - rank) * ps[i])
        adj[i] = min(1.0, run)
    return adj


def binomial_tail(n: int, k: int, p: float) -> float:
    return sum(math.comb(n, j) * p**j * (1-p)**(n-j) for j in range(k, n+1))


def cp(k: int, n: int) -> list[float]:
    """Clopper-Pearson 95%, via binomial-tail inversion (no SciPy needed)."""
    def lower(successes, trials):
        if successes == 0:
            return 0.0
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if binomial_tail(trials, successes, mid) < 0.025:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    return [round(100 * lower(k, n), 1), round(100 * (1 - lower(n-k, n)), 1)]


def counts(rows: list[dict], config: str) -> dict:
    defective = [r for r in rows if r["defects"]]
    clean = [r for r in rows if not r["defects"]]
    k = sum(r[config]["routed"] for r in defective)
    t = sum(bool(r[config]["traced"]) for r in defective)
    fa = sum(r[config]["routed"] for r in clean)
    return {"routed": k, "routed_pct": round(100*k/len(defective), 1), "routed_ci": cp(k, len(defective)),
            "traced": t, "traced_pct": round(100*t/len(defective), 1), "false_alarms": fa, "fa_ci": cp(fa, len(clean))}


def paired_tests(rows: list[dict], endpoint="routed") -> list[dict]:
    tests = [mcnemar_midp([bool(r[a][endpoint]) for r in rows], [bool(r[b][endpoint]) for r in rows]) for a, b in PAIRS]
    return [{"pair": f"{a} vs {b}", "n_paired": len(rows), "only_first": t[1], "only_second": t[0],
             "p_midp": t[2], "p_holm": adjusted}
            for (a,b), t, adjusted in zip(PAIRS, tests, holm([t[2] for t in tests]))]


def table(summary: list[dict]) -> str:
    lines = ["# External baselines on the frozen governance ablation", "",
             "Table 8 column format. C2/C4 values are read from the original summaries and independently reproduced.",
             "Routing is not sufficient for tracing: every planted defect must be covered.", ""]
    for rec in summary:
        nd, nc = rec["n_defective"], rec["n_clean"]
        lines += [f"## {rec['model']} · {rec['set']} ({nd} defective, {nc} clean)", "",
                  "| Config | Defects routed | 95% CI | Traced to planted criterion | False alarms |",
                  "|---|---|---|---|---|"]
        for config in ["C2", "B1", "B2", "C4"]:
            c = rec["configs"][config]
            lines.append(f"| {config} | {c['routed']}/{nd} ({c['routed_pct']:.1f}%) | {c['routed_ci'][0]:.1f}–{c['routed_ci'][1]:.1f} | {c['traced']}/{nd} | {c['false_alarms']}/{nc} |")
        lines += ["", "Paired routing tests on defective documents; Holm family = the three requested comparisons.", "",
                  "| Pair | Only first | Only second | McNemar mid-p | Holm p |", "|---|---:|---:|---:|---:|"]
        for t in rec["mcnemar"]:
            lines.append(f"| {t['pair']} | {t['only_first']} | {t['only_second']} | {t['p_midp']:.8g} | {t['p_holm']:.8g} |")
        lines.append("")
    return "\n".join(lines)


def main():
    INPUTS.clear()
    # Read/hash all source files used to define or verify this experiment.
    for name in ["README.md", "ablation_stats.py", "apex_jrd_frozen.ts", "ablation.ts",
                 "freeze_contracts.ts", "freeze_holdout2.ts", "tsconfig.json"]:
        read_input(ABLATION / name)
    read_input(ROOT / "src/jrd-extract.ts")
    expect = load_expect(read_input(ABLATION / "ablation_replay.ts"))
    summaries = {path.name: load_input(path) for path in sorted(ABLATION.glob("ablation_summary*.json"))}
    canonical = {(r["model"], r["set"]): r for r in summaries["ablation_summary.json"]}
    if len(canonical) != 6:
        raise AssertionError("Expected exactly six model/set summary records")
    for name, records in summaries.items():
        for r in records:
            other = canonical[r["model"], r["set"]]
            for field in ["n_defective", "n_clean", "errors"]:
                assert r[field] == other[field], (name, field)
            for config in ["C2", "C4"]:
                assert r["configs"][config] == other["configs"][config], (name, config)
    rows = []
    for model in MODELS:
        for prefix in ["", "h2_"]:
            frozen = load_input(ABLATION / f"frozen_{prefix}{model}.json")
            archived = load_input(ABLATION / f"ablation_{prefix}{model}.json")
            index = {(r["model"], r["set"], r["id"]): r for r in archived}
            assert len(index) == len(archived) == len(frozen)
            seen = set()
            for record in frozen:
                key = (record["model"], record["set"], record["id"])
                assert key not in seen and record["model"] == model
                seen.add(key)
                original = index[key]
                assert record["defects"] == original["defects"]
                assert bool(record["defects"]) == original["defective"]
                results = baselines(record.get("raw"))
                for name in ["B1", "B2"]:
                    evaluate_trace(results[name], record["defects"], expect)
                reference = replay_c2_c4(record, expect)
                for config in ["C2", "C4"]:
                    for field in ["state", "codes", "routed", "traced"]:
                        assert reference[config][field] == original[config][field], (key, config, field)
                rows.append({"model": model, "set": record["set"], "id": record["id"],
                             "defects": record["defects"], "error": record.get("error"), **results, **reference})
            assert seen == set(index)
    summary = []
    for model in MODELS:
        for dataset in SETS:
            group = [r for r in rows if (r["model"],r["set"]) == (model,dataset)]
            d, c = [r for r in group if r["defects"]], [r for r in group if not r["defects"]]
            original = canonical[model, dataset]
            assert (len(group),len(d),len(c)) == ((36,28,8) if dataset == "dev" else (43,33,10))
            config_counts = {config: counts(group, config) for config in ["B1","B2","C2","C4"]}
            for config in ["C2", "C4"]:
                assert config_counts[config] == original["configs"][config], (model, dataset, config)
                config_counts[config] = original["configs"][config]
            summary.append({"model": model, "set": dataset, "n_documents": len(group), "n_defective": len(d),
                            "n_clean": len(c), "errors": sum(bool(r["error"]) for r in group),
                            "configs": config_counts, "mcnemar": paired_tests(d),
                            "supplementary_tests": {"traced_on_defective": paired_tests(d, "traced"),
                                                    "false_alarms_on_clean": paired_tests(c)},
                            "totals_check_status": dict(Counter(r["B2"]["totals_check"]["status"] for r in group)),
                            "reference_reproduced": True})
    versions = {name: importlib.metadata.version(name) for name in ["pydantic", "pydantic-core", "jsonschema"]}
    versions["python"] = platform.python_version()
    template = read_input(HERE / "README.template.md")
    read_input(HERE / "baseline_schema.py")
    read_input(HERE / "requirements.txt")
    read_input(HERE / "test_baseline.py")
    provenance = dict(sorted(INPUTS.items()))
    result = {"definitions": {"input": "raw frozen JSON only", "VAT_enum": None,
              "primary_endpoint": "routed on defective documents", "holm_family": "three requested pairs within each model-set",
              "supplementary_holm": "separate three-pair families per model-set and supplementary endpoint",
              "trace_expected_codes": expect, "schema_equivalence_checked_on_all_records": True,
              "reference_documents_verified": len(rows), "reference_summary_files_verified": list(summaries)},
              "versions": versions, "input_sha256": provenance, "summary": summary, "documents": rows}
    # Verify bytes of every input again before writing results.
    for path, expected in provenance.items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == expected, path
    (HERE / "baseline_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (HERE / "baseline_json_schema.json").write_text(json.dumps(SCHEMA, indent=2)+"\n", encoding="utf-8")
    (HERE / "baseline_table.md").write_text(table(summary), encoding="utf-8")
    hashes = "\n".join(f"| `{path}` | `{digest}` |" for path,digest in provenance.items())
    version_text = ", ".join(f"{name} **{version}**" for name,version in versions.items())
    (HERE / "README.md").write_text(template.replace("{{VERSIONS}}",version_text).replace("{{HASHES}}",hashes),encoding="utf-8")
    print(table(summary))
    print(f"Verified all C2/C4 states, codes, routing and tracing for {len(rows)} model-document records.")
    print(f"All C2/C4 counts, percentages and confidence intervals equal all {len(summaries)} summary files.")


if __name__ == "__main__":
    main()
