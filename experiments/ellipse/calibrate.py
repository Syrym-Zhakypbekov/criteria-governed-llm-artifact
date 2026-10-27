# Human-anchored calibration criterion: fit score' = a + b*score on a calibration fold of human-scored essays,
# evaluate on the held-out fold (2-fold, 200 random repeats). Then escalate by |calibrated - raw| disagreement between
# configurations and by distance to band boundaries. usage: python calibrate.py jobs.json results.jsonl tag
import json, sys, numpy as np
from sklearn.metrics import cohen_kappa_score
JOBS, RES, TAG = sys.argv[1:4]
gold = json.load(open(JOBS, encoding="utf-8"))["gold"]
res = [json.loads(l) for l in open(RES, encoding="utf-8") if l.strip()]
ok = [r for r in res if "out" in r and isinstance(r["out"].get("overall"), (int, float))]
ids = sorted(gold); H = np.array([gold[i]["Overall"] for i in ids])
S = {c: np.array([np.mean([r["out"]["overall"] for r in ok if r["id"] == i and r["cfg"] == c] or [np.nan]) for i in ids]) for c in "ABC"}
q = lambda a, b: cohen_kappa_score(np.round(np.clip(a, 1, 5) * 2).astype(int), np.round(b * 2).astype(int), weights="quadratic")
rnd = np.random.default_rng(3); out = {"tag": TAG}
for c in "ABC":
    x = S[c]; m = ~np.isnan(x); maes, qwks = [], []
    for _ in range(200):
        idx = rnd.permutation(np.where(m)[0]); half = len(idx) // 2
        for cal, tst in ((idx[:half], idx[half:]), (idx[half:], idx[:half])):
            b, a = np.polyfit(x[cal], H[cal], 1); pred = np.clip(np.round((a + b * x[tst]) * 2) / 2, 1, 5)
            maes.append(np.mean(np.abs(pred - H[tst]))); qwks.append(q(pred, H[tst]))
    raw_mae = float(np.mean(np.abs(x[m] - H[m])))
    out[c] = {"raw_mae": raw_mae, "cal_mae": float(np.mean(maes)), "cal_mae_ci": [float(np.percentile(maes, 2.5)), float(np.percentile(maes, 97.5))],
              "raw_qwk": float(q(x[m], H[m])), "cal_qwk": float(np.mean(qwks)), "cal_qwk_ci": [float(np.percentile(qwks, 2.5)), float(np.percentile(qwks, 97.5))]}
    print(f"[{TAG}] {c}: raw MAE {raw_mae:.3f} -> calibrated {out[c]['cal_mae']:.3f} {out[c]['cal_mae_ci']}; QWK {out[c]['raw_qwk']:.3f} -> {out[c]['cal_qwk']:.3f} {out[c]['cal_qwk_ci']}")
json.dump(out, open(f"calibration_{TAG}.json", "w"), indent=1)
