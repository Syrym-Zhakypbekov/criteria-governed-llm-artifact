# Cross-model disagreement as an escalation criterion (cf. Hamidieh et al., ICLR 2026) versus self-disagreement and
# random review, and a calibrated two-model ensemble. All scores already collected (no new model calls).
# Large error = |calibrated ensemble (or each model) - human mean| >= 0.5 after held-out calibration; escalation budgets 10-30%.
# usage: python cross_model.py jobs.json ellipse_flashlite.jsonl ellipse_flash38.jsonl
import json, sys, numpy as np
from sklearn.metrics import cohen_kappa_score
JOBS, A_, B_ = sys.argv[1:4]
gold = json.load(open(JOBS, encoding="utf-8"))["gold"]; ids = sorted(gold); H = np.array([gold[i]["Overall"] for i in ids])
def load(f):
    d = {}
    for l in open(f, encoding="utf-8"):
        r = json.loads(l)
        if "out" in r and isinstance(r["out"].get("overall"), (int, float)): d.setdefault((r["id"], r["cfg"]), []).append(r["out"]["overall"])
    return d
LA, LB = load(A_), load(B_)
def mean(d, c): return np.array([np.mean(d.get((i, c), [np.nan])) for i in ids])
def spread(d): return np.array([np.ptp([x for c in "ABC" for x in d.get((i, c), [])] or [0]) + np.std([x for c in "ABC" for x in d.get((i, c), [])] or [0]) for i in ids])
xa, xb = mean(LA, "C"), mean(LB, "C"); m = ~np.isnan(xa) & ~np.isnan(xb)
qwk = lambda a, b: cohen_kappa_score(np.round(np.clip(a, 1, 5) * 2).astype(int), np.round(b * 2).astype(int), weights="quadratic", labels=list(range(2, 11)))
rnd = np.random.default_rng(9); res = {k: [] for k in ["mae_a", "mae_b", "mae_ens", "qwk_a", "qwk_b", "qwk_ens"]}
esc = {b: {"cross": [], "selfA": [], "selfB": [], "random": [], "n_large": []} for b in (0.1, 0.2, 0.3)}
sA, sB = spread(LA), spread(LB)
for _ in range(300):
    idx = rnd.permutation(np.where(m)[0]); h = len(idx) // 2
    for cal, tst in ((idx[:h], idx[h:]), (idx[h:], idx[:h])):
        ba, aa = np.polyfit(xa[cal], H[cal], 1); bb, ab = np.polyfit(xb[cal], H[cal], 1)
        pa, pb = aa + ba * xa[tst], ab + bb * xb[tst]; pe = (pa + pb) / 2
        for k, p in (("a", pa), ("b", pb), ("ens", pe)):
            res["mae_" + k].append(np.mean(np.abs(np.clip(np.round(p * 2) / 2, 1, 5) - H[tst]))); res["qwk_" + k].append(qwk(p, H[tst]))
        err = np.abs(pe - H[tst]); large = err >= 0.5; dis = np.abs(pa - pb)
        for b in esc:
            k = max(1, round(b * len(tst)))
            def caught(score): return int(large[np.argsort(-score)[:k]].sum())
            esc[b]["cross"].append(caught(dis)); esc[b]["selfA"].append(caught(sA[tst])); esc[b]["selfB"].append(caught(sB[tst]))
            esc[b]["random"].append(large.sum() * k / len(tst)); esc[b]["n_large"].append(int(large.sum()))
out = {k: [float(np.mean(v)), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in res.items()}
for k, v in out.items(): print(f"{k}: {v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]")
for b, d in esc.items():
    diff = np.array(d["cross"]) - np.array(d["random"])
    out[f"esc_{int(b*100)}"] = {k: float(np.mean(v)) for k, v in d.items()} | {"cross_minus_random_ci": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))], "share_splits_cross_gt_random": float(np.mean(diff > 0))}
    print(f"budget {int(b*100)}% (k≈{round(b*60)} of 60): large errors {np.mean(d['n_large']):.1f}; caught by cross-model {np.mean(d['cross']):.2f}, self A {np.mean(d['selfA']):.2f}, self B {np.mean(d['selfB']):.2f}, random {np.mean(d['random']):.2f}; cross-random CI {np.round(out[f'esc_{int(b*100)}']['cross_minus_random_ci'],2)}, share>0 {out[f'esc_{int(b*100)}']['share_splits_cross_gt_random']:.2f}")
json.dump(out, open("cross_model_results.json", "w"), indent=1)
