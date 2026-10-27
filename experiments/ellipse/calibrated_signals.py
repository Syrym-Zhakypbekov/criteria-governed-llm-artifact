# Round-6 reanalysis (27.10.2026): the SAME three signals as Table 9 (repeat range of configuration C, SD of the A/B/C means,
# |difference of configuration-C means between models|), evaluated AFTER calibration with a model-specific target:
# large error = |calibrated prediction - rater mean| >= 0.5, prediction = clip(round_half(a + b * mean C), 1, 5), with
# a, b fitted by OLS on the calibration half. 200 random half-splits x 2 folds; budget 20% of the held-out half; ties at
# random. Reported: mean capture, mean random expectation and 2.5-97.5 percentiles of (capture - random) across folds.
# usage: python calibrated_signals.py jobs.json ellipse_flashlite.jsonl ellipse_flash38.jsonl
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
rng = np.random.default_rng(627); out = {"target": "|clip(round_half(a+b*meanC),1,5) - rater mean| >= 0.5", "budget": 0.2, "splits": 200}
for name, d in D.items():
    other = D["flash38" if name == "flashlite" else "flashlite"]; x = cm(d, "C")
    sig = {"repeat": np.array([np.ptp(d[(i, "C")]) if len(d.get((i, "C"), [])) > 1 else np.nan for i in ids]),
           "between": np.nanstd(np.vstack([cm(d, c) for c in "ABC"]), axis=0), "cross": np.abs(x - cm(other, "C"))}
    ok = np.where(~np.isnan(x) & ~np.isnan(sig["repeat"]) & ~np.isnan(sig["between"]) & ~np.isnan(sig["cross"]))[0]
    acc = {k: {"cap": [], "rnd": [], "diff": []} for k in sig}; nl = []
    for _ in range(200):
        idx = rng.permutation(ok); h = len(idx) // 2
        for cal, tst in ((idx[:h], idx[h:]), (idx[h:], idx[:h])):
            b, a = np.polyfit(x[cal], H[cal], 1); p = np.clip(np.round((a + b * x[tst]) * 2) / 2, 1, 5)
            large = np.abs(p - H[tst]) >= 0.5; nl.append(int(large.sum())); k = max(1, round(0.2 * len(tst)))
            for sn, s in sig.items():
                st = s[tst]; order = np.lexsort((rng.random(len(st)), -st)); c = int(large[order[:k]].sum()); e = k * large.sum() / len(tst)
                acc[sn]["cap"].append(c); acc[sn]["rnd"].append(e); acc[sn]["diff"].append(c - e)
    res = {"n": int(len(ok)), "held_out": int(len(ok) - len(ok) // 2), "large_errors_mean": float(np.mean(nl))}
    for sn, v in acc.items():
        res[sn] = {"capture": round(float(np.mean(v["cap"])), 2), "random": round(float(np.mean(v["rnd"])), 2),
                   "diff_range": [round(float(np.percentile(v["diff"], 2.5)), 2), round(float(np.percentile(v["diff"], 97.5)), 2)],
                   "share_folds_above_random": round(float(np.mean(np.array(v["diff"]) > 0)), 2)}
    out[name] = res; print(name, {k: res[k] for k in ("n", "large_errors_mean")}, {sn: (res[sn]["capture"], res[sn]["random"], res[sn]["diff_range"]) for sn in sig})
json.dump(out, open("calibrated_signals_results.json", "w"), indent=1)
