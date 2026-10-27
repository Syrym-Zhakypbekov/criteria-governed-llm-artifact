# Round-4 reanalysis (27.10.2026): three disagreement signals kept SEPARATE, same error target, same budgets.
# Target: large error = |three-run mean of configuration C - mean of two raters| >= 0.75 (uncalibrated, as in Section 6.4).
# Signals per essay: within = range of the 3 repeats of configuration C; between = SD of the three configuration means (A,B,C);
# cross = |C mean of this model - C mean of the other model|. Ties broken at random, averaged over 1000 tie-breaks.
# Baseline = random review with the same budget (expected k*L/N). Uncertainty: paired bootstrap over essays (2000).
# usage: python uncertainty_signals.py jobs.json ellipse_flashlite.jsonl ellipse_flash38.jsonl
import json, sys, numpy as np
JOBS, F1, F2 = sys.argv[1:4]
gold = json.load(open(JOBS, encoding="utf-8"))["gold"]; ids = sorted(gold); H = np.array([gold[i]["Overall"] for i in ids])
def load(f):
    d = {}
    for l in open(f, encoding="utf-8"):
        r = json.loads(l)
        if "out" in r and isinstance(r["out"].get("overall"), (int, float)): d.setdefault((r["id"], r["cfg"]), []).append(r["out"]["overall"])
    return d
D = {"flashlite": load(F1), "flash38": load(F2)}
def cmean(d, c): return np.array([np.mean(d[(i, c)]) if d.get((i, c)) else np.nan for i in ids])
out = {"target": "|mean C - rater mean| >= 0.75", "budgets": [0.1, 0.2, 0.3]}
rng = np.random.default_rng(27)
for name, d in D.items():
    other = D["flash38" if name == "flashlite" else "flashlite"]
    mc = cmean(d, "C"); large = np.abs(mc - H) >= 0.75
    sig = {"within": np.array([np.ptp(d[(i, "C")]) if len(d.get((i, "C"), [])) > 1 else np.nan for i in ids]),
           "between": np.nanstd(np.vstack([cmean(d, c) for c in "ABC"]), axis=0),
           "cross": np.abs(mc - cmean(other, "C"))}
    ok = ~np.isnan(mc) & ~np.isnan(sig["within"]) & ~np.isnan(sig["between"]) & ~np.isnan(sig["cross"])
    L = large[ok]; N = int(ok.sum()); res = {"n": N, "large": int(L.sum())}
    def caught(s, lg, k, rr):  # mean over random tie-breaks
        return np.mean([lg[np.lexsort((rr.random(len(s)), -s))[:k]].sum() for _ in range(200)])
    for sn, s in sig.items():
        s = s[ok]; res[sn] = {"distinct_values": int(len(np.unique(s)))}
        for b in out["budgets"]:
            k = max(1, round(b * N)); c = caught(s, L, k, rng); exp = k * L.sum() / N
            bs = []
            for _ in range(2000):
                idx = rng.integers(0, N, N); lb = L[idx]; sb = s[idx]
                bs.append(lb[np.lexsort((rng.random(N), -sb))[:k]].sum() - k * lb.sum() / N)
            res[sn][f"{int(b*100)}"] = {"k": k, "caught": round(float(c), 2), "random_expected": round(float(exp), 2),
                                       "diff": round(float(c - exp), 2), "diff_ci": [round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)]}
    out[name] = res
    print(name, "N", N, "large", int(L.sum()))
    for sn in sig: print("  ", sn, "distinct", res[sn]["distinct_values"], {b: (res[sn][b]["caught"], res[sn][b]["random_expected"], res[sn][b]["diff_ci"]) for b in ("10", "20", "30")})
json.dump(out, open("uncertainty_signals_results.json", "w"), indent=1)
