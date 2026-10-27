# Commensurable comparison (reviewer request): calibrated AI vs EACH single rater, against rater 1 vs rater 2 on the same
# held-out essays. Calibration is fitted on the calibration fold against the mean of the two raters, applied to held-out
# essays; single-run AI score (run 1) is used so that AI and human are both single ratings. Difference in QWK
# (AI-vs-rater minus rater-vs-rater) with a bootstrap 95% CI over essays inside each split, pooled over 200 splits.
# usage: python human_compare.py jobs.json raw_rater.csv results.jsonl tag
import json, sys, numpy as np, pandas as pd
from sklearn.metrics import cohen_kappa_score
JOBS, RAW, RES, TAG = sys.argv[1:5]
gold = json.load(open(JOBS, encoding="utf-8"))["gold"]; raw = pd.read_csv(RAW).set_index("text_id_kaggle")
res = [json.loads(l) for l in open(RES, encoding="utf-8") if l.strip()]
ids = sorted(i for i in gold if i in raw.index)
R1 = np.array([float(raw.loc[i, "Overall_1"]) for i in ids]); R2 = np.array([float(raw.loc[i, "Overall_2"]) for i in ids])
M = (R1 + R2) / 2
def run1(c):
    d = {(r["id"], r["rep"]): r["out"]["overall"] for r in res if r["cfg"] == c and "out" in r and isinstance(r["out"].get("overall"), (int, float))}
    return np.array([d.get((i, 1), d.get((i, 2), d.get((i, 3), np.nan))) for i in ids])
qwk = lambda a, b: cohen_kappa_score(np.round(np.clip(a, 1, 5)).astype(int), np.round(b).astype(int), weights="quadratic")  # integer 1-5 scale = scale of individual raters
mae = lambda a, b: float(np.mean(np.abs(np.clip(np.round(a), 1, 5) - b)))
rnd = np.random.default_rng(5); out = {"tag": TAG, "n": len(ids), "human_qwk_int": qwk(R1, R2), "human_mae_int": mae(R1, R2)}
print(f"[{TAG}] rater1 vs rater2 (integer scale): QWK {out['human_qwk_int']:.3f} MAE {out['human_mae_int']:.3f}")
for c in "ABC":
    x = run1(c); m = ~np.isnan(x); dq, dm, aq = [], [], []
    for _ in range(200):
        idx = rnd.permutation(np.where(m)[0]); h = len(idx) // 2
        for cal, tst in ((idx[:h], idx[h:]), (idx[h:], idx[:h])):
            b, a = np.polyfit(x[cal], M[cal], 1); p = a + b * x[tst]
            ai_q = (qwk(p, R1[tst]) + qwk(p, R2[tst])) / 2; hu_q = qwk(R1[tst], R2[tst])
            ai_m = (mae(p, R1[tst]) + mae(p, R2[tst])) / 2; hu_m = mae(R1[tst], R2[tst])
            dq.append(ai_q - hu_q); dm.append(ai_m - hu_m); aq.append(ai_q)
    out[c] = {"ai_vs_single_rater_qwk": float(np.mean(aq)), "qwk_diff": float(np.mean(dq)), "qwk_diff_ci": [float(np.percentile(dq, 2.5)), float(np.percentile(dq, 97.5))],
              "mae_diff": float(np.mean(dm)), "mae_diff_ci": [float(np.percentile(dm, 2.5)), float(np.percentile(dm, 97.5))]}
    print(f"  {c}: calibrated single-run AI vs single rater QWK {out[c]['ai_vs_single_rater_qwk']:.3f}; diff vs human {out[c]['qwk_diff']:+.3f} {np.round(out[c]['qwk_diff_ci'],3)}; MAE diff {out[c]['mae_diff']:+.3f} {np.round(out[c]['mae_diff_ci'],3)}")
json.dump(out, open(f"human_compare_{TAG}.json", "w"), indent=1)
