# Statistics for the governance ablation (27.10.2026). Input: ablation_<model>.json from ablation.ts (same frozen outputs for C1–C5).
# Per set × model × config: defects routed to a human (recall), defects traced to the planted criterion, false alarms on clean docs,
# all with Clopper–Pearson 95% intervals. Paired tests on the SAME documents: Cochran's Q across C1–C5 (Cochran 1950), pairwise
# McNemar mid-p (Fagerland et al. 2013) with Holm correction. Writes ablation_summary.json + prints a Markdown table.
# usage: python ablation_stats.py ablation_gemini-3.8-flash.json [ablation_gemini-3.1-flash-lite.json ...]
import json, sys
from scipy.stats import beta, binom, chi2

CFG = ["C1", "C2", "C3", "C4", "C5"]


def cp(k, n, a=0.05):
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return round(100 * lo, 1), round(100 * hi, 1)


def cochran_q(rows):  # rows: list of 0/1 lists (one per document) across k configs
    k = len(rows[0]); C = [sum(r[j] for r in rows) for j in range(k)]; R = [sum(r) for r in rows]; N = sum(R)
    den = k * N - sum(x * x for x in R)
    if den == 0:
        return 0.0, 1.0
    q = (k - 1) * (k * sum(c * c for c in C) - N * N) / den
    return q, float(chi2.sf(q, k - 1))


def mcnemar_midp(a, b):  # a, b: 0/1 lists on the same documents
    n01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1); n10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    n = n01 + n10
    if n == 0:
        return n01, n10, 1.0
    k = min(n01, n10)
    p = 2 * binom.cdf(k, n, 0.5) - binom.pmf(k, n, 0.5)
    return n01, n10, float(min(1.0, p))


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i]); adj = [0.0] * len(ps); run = 0.0
    for r, i in enumerate(order):
        run = max(run, (len(ps) - r) * ps[i]); adj[i] = min(1.0, run)
    return adj


out = []
for f in sys.argv[1:]:
    rows = json.load(open(f, encoding="utf-8"))
    model = rows[0]["model"]
    for s in [x for x in ["dev", "holdout", "holdout2"] if any(r["set"] == x for r in rows)]:
        R = [r for r in rows if r["set"] == s]; D = [r for r in R if r["defective"]]; C = [r for r in R if not r["defective"]]
        rec = {"model": model, "set": s, "n_defective": len(D), "n_clean": len(C), "errors": sum(1 for r in R if r.get("error")), "configs": {}}
        for c in CFG + ["PROD"]:
            k = sum(1 for r in D if r[c]["routed"]); t = sum(1 for r in D if r[c]["traced"]); fa = sum(1 for r in C if r[c]["routed"])
            rec["configs"][c] = {"routed": k, "routed_pct": round(100 * k / len(D), 1), "routed_ci": cp(k, len(D)), "traced": t,
                                 "traced_pct": round(100 * t / len(D), 1), "false_alarms": fa, "fa_ci": cp(fa, len(C))}
        mat = [[1 if r[c]["routed"] else 0 for c in CFG] for r in D]
        q, pq = cochran_q(mat); rec["cochran_q"] = {"Q": round(q, 2), "df": len(CFG) - 1, "p": pq}
        pairs = [("C1", "C2"), ("C2", "C3"), ("C3", "C4"), ("C4", "C5"), ("C2", "C4"), ("C2", "C5")]
        tests = [mcnemar_midp([1 if r[a]["routed"] else 0 for r in D], [1 if r[b]["routed"] else 0 for r in D]) for a, b in pairs]
        adj = holm([t[2] for t in tests])
        rec["mcnemar"] = [{"pair": f"{a} vs {b}", "only_first": t[1], "only_second": t[0], "p_midp": t[2], "p_holm": p}
                          for (a, b), t, p in zip(pairs, tests, adj)]
        out.append(rec)

json.dump(out, open("ablation_summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for rec in out:
    print(f"\n### {rec['model']} · {rec['set']} ({rec['n_defective']} defective, {rec['n_clean']} clean, errors {rec['errors']})")
    print("| Config | Defects routed | 95% CI | Traced to planted criterion | False alarms |")
    print("|---|---|---|---|---|")
    for c in CFG + ["PROD"]:
        x = rec["configs"][c]
        print(f"| {c} | {x['routed']}/{rec['n_defective']} ({x['routed_pct']}%) | {x['routed_ci'][0]}–{x['routed_ci'][1]} | {x['traced']}/{rec['n_defective']} | {x['false_alarms']}/{rec['n_clean']} |")
    print(f"Cochran's Q = {rec['cochran_q']['Q']}, df = {rec['cochran_q']['df']}, p = {rec['cochran_q']['p']:.2e}")
    for m in rec["mcnemar"]:
        print(f"  McNemar {m['pair']}: discordant {m['only_first']}/{m['only_second']}, mid-p {m['p_midp']:.2e}, Holm {m['p_holm']:.2e}")
