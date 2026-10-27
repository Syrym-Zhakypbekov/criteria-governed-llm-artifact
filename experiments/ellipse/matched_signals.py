# Round-7 matched before/after analysis (27.10.2026): on the SAME held-out folds (200 partitions x 2 = 400 fold evaluations),
# the SAME three signals, the SAME 20% budget, the SAME random tie-breaks and the SAME error threshold (>= 0.5), compare
#   raw:        prediction = clip(round_half(mean C), 1, 5)
#   calibrated: prediction = clip(round_half(a + b * mean C), 1, 5), OLS fitted on the calibration half.
# Per fold: capture - random expectation for each target; paired difference (calibrated - raw) of that advantage.
# Reported: means and 2.5-97.5 percentiles over folds (split variability, not confidence intervals) and share of folds > 0.
# usage: python matched_signals.py jobs.json ellipse_flashlite.jsonl ellipse_flash38.jsonl
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
cm = lambda d, c: np.array([np.mean(d[(i, c)]) if d.get((i, c)) else np.nan for i in ids])
rh = lambda v: np.clip(np.round(v * 2) / 2, 1, 5)
rng = np.random.default_rng(727); out = {"threshold": 0.5, "budget": 0.2, "fold_evaluations": 400}
for name, d in D.items():
    other = D["flash38" if name == "flashlite" else "flashlite"]; x = cm(d, "C")
    sig = {"repeat": np.array([np.ptp(d[(i, "C")]) if len(d.get((i, "C"), [])) > 1 else np.nan for i in ids]),
           "between": np.nanstd(np.vstack([cm(d, c) for c in "ABC"]), axis=0), "cross": np.abs(x - cm(other, "C"))}
    ok = np.where(~np.isnan(x) & ~np.isnan(sig["repeat"]) & ~np.isnan(sig["between"]) & ~np.isnan(sig["cross"]))[0]
    acc = {k: {"raw": [], "cal": [], "delta": []} for k in sig}; nl = {"raw": [], "cal": []}; sizes = []
    for _ in range(200):
        idx = rng.permutation(ok); h = len(idx) // 2
        for cal, tst in ((idx[:h], idx[h:]), (idx[h:], idx[:h])):
            b, a = np.polyfit(x[cal], H[cal], 1); sizes.append(len(tst))
            T = {"raw": np.abs(rh(x[tst]) - H[tst]) >= 0.5, "cal": np.abs(rh(a + b * x[tst]) - H[tst]) >= 0.5}
            for t in T: nl[t].append(int(T[t].sum()))
            k = max(1, round(0.2 * len(tst)))
            for sn, s in sig.items():
                order = np.lexsort((rng.random(len(tst)), -s[tst]))[:k]   # same ranking for both targets
                adv = {t: T[t][order].sum() - k * T[t].sum() / len(tst) for t in T}
                acc[sn]["raw"].append(adv["raw"]); acc[sn]["cal"].append(adv["cal"]); acc[sn]["delta"].append(adv["cal"] - adv["raw"])
    res = {"n": int(len(ok)), "held_out_sizes": sorted(set(sizes)), "large_errors_mean": {t: round(float(np.mean(v)), 2) for t, v in nl.items()}}
    pct = lambda v: [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]
    for sn, v in acc.items():
        res[sn] = {t: {"mean_advantage": round(float(np.mean(v[t])), 2), "range": pct(v[t]), "share_folds_gt0": round(float(np.mean(np.array(v[t]) > 0)), 2)} for t in ("raw", "cal", "delta")}
    out[name] = res
    print(name, res["n"], res["held_out_sizes"], res["large_errors_mean"])
    for sn in sig: print("  ", sn, {t: (res[sn][t]["mean_advantage"], res[sn][t]["range"], res[sn][t]["share_folds_gt0"]) for t in ("raw", "cal", "delta")})
json.dump(out, open("matched_signals_results.json", "w"), indent=1)
