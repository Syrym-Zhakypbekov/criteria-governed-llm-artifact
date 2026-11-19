"""Independent recount of the article's headline numbers from the stored per-call result files (MAKE revision, R2.7).

Written for the revision (November 2026) separately from the original analysis scripts (holdout_an.py, stability.py,
ablation_stats.py): it does not import them, and it recomputes every count directly from the per-document JSON records,
plus exact Clopper–Pearson 95% intervals with SciPy. Each recount is compared with the value printed in the article.
A mismatch is reported, not hidden.

Checks
  1. Frozen held-out contracts (43 docs: 33 defective, 10 clean), both models: routed = state vetoed/escalated
     (field `routed`), expected-criterion hit (field `criterionHit`).               Article: 33/33 and 0/10, CI 89.4–100 / 0–30.8
  2. Held-out business cards (25: 19 defective, 6 clean), gemini-3.5-flash-lite: state-based routing.  Article: 12/19 and 0/6
  3. Governance ablation on the confirmatory set holdout2, both models: routed defective per configuration C1–C5 and
     false alarms on clean documents, from the per-document files ablation_h2_<model>.json.
                                                                                     Article: C1 0, C2 12 / 6, C3 15, C4 = C5 33; 0 FA
Usage: python experiments/verification/recount_headlines.py      (exit 0 = all recounts equal the article)
"""
import json
import sys
from pathlib import Path

from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[2]
FAILS: list[str] = []


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def cp(k, n):
    lo = 0.0 if k == 0 else beta.ppf(0.025, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(0.975, k + 1, n - k)
    return round(float(100 * lo), 1), round(float(100 * hi), 1)


def check(label, got, want):
    ok = got == want
    if not ok:
        FAILS.append(f"{label}: recount {got} ≠ article {want}")
    print(f"{'OK ' if ok else 'BAD'} {label}: {got}" + ("" if ok else f"  (article {want})"))


def contracts():
    for model in ("gemini-3.8-flash", "gemini-3.1-flash-lite"):
        rows = load(f"experiments/contracts/holdout_{model}.json")
        defective = [r for r in rows if r["defects"]]
        clean = [r for r in rows if not r["defects"]]
        rd = sum(bool(r["routed"]) for r in defective)
        rc = sum(bool(r["routed"]) for r in clean)
        hit = sum(bool(r["criterionHit"]) for r in defective)
        check(f"contracts {model}: n defective / clean", (len(defective), len(clean)), (33, 10))
        check(f"contracts {model}: routed defective", rd, 33)
        check(f"contracts {model}: expected criterion fired", hit, 33)
        check(f"contracts {model}: routed clean", rc, 0)
        check(f"contracts {model}: CI routed defective", cp(rd, len(defective)), (89.4, 100.0))
        check(f"contracts {model}: CI routed clean", cp(rc, len(clean)), (0.0, 30.8))


def cards():
    rows = load("experiments/business_cards/cards_holdout_gemini-3.5-flash-lite.json")
    defective = [r for r in rows if r["defects"]]
    clean = [r for r in rows if not r["defects"]]
    routed = lambda r: r["state"] in ("vetoed", "escalated")
    check("cards flash-lite: n defective / clean", (len(defective), len(clean)), (19, 6))
    check("cards flash-lite: state-routed defective", sum(routed(r) for r in defective), 12)
    check("cards flash-lite: state-routed clean", sum(routed(r) for r in clean), 0)
    check("cards flash-lite: `routed` field agrees with state", all(bool(r["routed"]) == routed(r) for r in rows), True)


def ablation():
    want = {"gemini-3.8-flash": {"C1": 0, "C2": 12, "C3": 15, "C4": 33, "C5": 33},
            "gemini-3.1-flash-lite": {"C1": 0, "C2": 6, "C4": 33, "C5": 33}}
    for model, exp in want.items():
        rows = [r for r in load(f"experiments/ablation/ablation_h2_{model}.json") if not r.get("error")]
        defective = [r for r in rows if r["defective"]]
        clean = [r for r in rows if not r["defective"]]
        for cfg, n in exp.items():
            check(f"ablation holdout2 {model} {cfg}: routed defective", sum(bool(r[cfg]["routed"]) for r in defective), n)
        check(f"ablation holdout2 {model}: false alarms C1–C5", sum(bool(r[c]["routed"]) for r in clean for c in ("C1", "C2", "C3", "C4", "C5")), 0)
        summ = {s["model"]: s for s in load("experiments/ablation/ablation_summary_h2.json")}[model]["configs"]
        for cfg in ("C1", "C2", "C3", "C4", "C5"):
            check(f"ablation holdout2 {model} {cfg}: per-document recount = stored summary",
                  sum(bool(r[cfg]["routed"]) for r in defective), summ[cfg]["routed"])


if __name__ == "__main__":
    contracts()
    cards()
    ablation()
    print("ALL RECOUNTS EQUAL THE ARTICLE" if not FAILS else f"{len(FAILS)} MISMATCH(ES):\n  " + "\n  ".join(FAILS))
    sys.exit(1 if FAILS else 0)
