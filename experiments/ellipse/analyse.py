# EXP-ELLIPSE analysis. Inputs: jobs.json (gold = published average scores), raw rater CSV (two individual raters),
# results JSONL from ellipse_run.ts. Outputs: printed tables + results_<tag>.json. Every number in the paper comes from here.
# usage: python analyse.py jobs.json raw/ellipsis_raw_rater_scores_anon_all_essay.csv ellipse_<model>.jsonl <tag>
import json, sys, random
import numpy as np, pandas as pd
from sklearn.metrics import cohen_kappa_score
from scipy.stats import wilcoxon, spearmanr

JOBS, RAW, RES, TAG = sys.argv[1:5]
gold = json.load(open(JOBS, encoding="utf-8"))["gold"]
raw = pd.read_csv(RAW).set_index("text_id_kaggle")
res = [json.loads(l) for l in open(RES, encoding="utf-8") if l.strip()]
ok = [r for r in res if "out" in r and isinstance(r["out"].get("overall"), (int, float))]
err = len(res) - len(ok)
ids = sorted(gold)
H = {i: gold[i]["Overall"] for i in ids}                                       # published average of two raters
R1 = {i: float(raw.loc[i, "Overall_1"]) for i in ids if i in raw.index}
R2 = {i: float(raw.loc[i, "Overall_2"]) for i in ids if i in raw.index}

def qwk(a, b):  # quadratic weighted kappa on half-point scale mapped to integers 2..10
    return cohen_kappa_score([int(round(x * 2)) for x in a], [int(round(x * 2)) for x in b], weights="quadratic")
def ci(vals, f, n=2000, seed=7):
    rnd = np.random.default_rng(seed); v = np.array(vals, dtype=object); bs = []
    for _ in range(n):
        s = v[rnd.integers(0, len(v), len(v))]; bs.append(f(s))
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))

out = {"tag": TAG, "calls": len(res), "errors": err, "essays": len(ids)}
scores = {c: {i: [r["out"]["overall"] for r in ok if r["id"] == i and r["cfg"] == c] for i in ids} for c in "ABC"}
both = [i for i in ids if i in R1 and i in R2]
out["human_qwk_r1_r2"] = qwk([R1[i] for i in both], [R2[i] for i in both])
out["human_mae_r1_r2"] = float(np.mean([abs(R1[i] - R2[i]) for i in both]))
print(f"[{TAG}] calls {len(res)} errors {err}; human rater1 vs rater2 on {len(both)} essays: QWK {out['human_qwk_r1_r2']:.3f}, MAE {out['human_mae_r1_r2']:.3f}")
for c in "ABC":
    full = [i for i in ids if len(scores[c][i]) >= 1]
    m = {i: float(np.mean(scores[c][i])) for i in full}
    first = {i: scores[c][i][0] for i in full}
    sd = [float(np.std(scores[c][i])) for i in full if len(scores[c][i]) >= 2]
    rng = [max(scores[c][i]) - min(scores[c][i]) for i in full if len(scores[c][i]) >= 2]
    mae = float(np.mean([abs(m[i] - H[i]) for i in full]))
    lo, hi = ci(full, lambda s: float(np.mean([abs(m[i] - H[i]) for i in s])))
    d = {"n": len(full), "mae_vs_gold": mae, "mae_ci": [lo, hi],
         "qwk_single_run_vs_gold": qwk([first[i] for i in full], [H[i] for i in full]),
         "qwk_single_run_vs_rater1": qwk([first[i] for i in full if i in R1], [R1[i] for i in full if i in R1]),
         "qwk_single_run_vs_rater2": qwk([first[i] for i in full if i in R2], [R2[i] for i in full if i in R2]),
         "spearman_mean_vs_gold": float(spearmanr([m[i] for i in full], [H[i] for i in full])[0]),
         "bias_ai_minus_gold": float(np.mean([m[i] - H[i] for i in full])),
         "repeat_sd_mean": float(np.mean(sd)) if sd else None,
         "share_repeats_identical": float(np.mean([x == 0 for x in rng])) if rng else None}
    out[c] = d
    print(f"  {c}: n={d['n']} MAE {mae:.3f} [{lo:.3f},{hi:.3f}]  QWK(run1 vs gold) {d['qwk_single_run_vs_gold']:.3f}  "
          f"QWK vs r1 {d['qwk_single_run_vs_rater1']:.3f} vs r2 {d['qwk_single_run_vs_rater2']:.3f}  rho {d['spearman_mean_vs_gold']:.3f}  "
          f"bias {d['bias_ai_minus_gold']:+.3f}  repeat SD {d['repeat_sd_mean']:.3f}  identical {d['share_repeats_identical']:.2f}")
# paired comparisons (H1): per-essay absolute error of the 3-run mean
for a, b in [("A", "B"), ("B", "C"), ("A", "C")]:
    common = [i for i in ids if scores[a][i] and scores[b][i]]
    ea = [abs(np.mean(scores[a][i]) - H[i]) for i in common]; eb = [abs(np.mean(scores[b][i]) - H[i]) for i in common]
    diff = float(np.mean(np.array(ea) - np.array(eb)))
    p = float(wilcoxon(ea, eb).pvalue) if any(x != y for x, y in zip(ea, eb)) else 1.0
    out[f"paired_{a}{b}"] = {"mae_diff": diff, "wilcoxon_p": p}
    print(f"  MAE({a}) - MAE({b}) = {diff:+.3f}, Wilcoxon p = {p:.4f}")
# H4 / criteria operator: escalate by disagreement across repeats and configurations vs random review, same budget
allm = {i: [x for c in "ABC" for x in scores[c][i]] for i in ids}
risk = {i: (max(allm[i]) - min(allm[i])) + float(np.std(allm[i])) for i in ids if len(allm[i]) >= 2}
cm = {i: float(np.mean(scores["C"][i])) if scores["C"][i] else float(np.mean(allm[i])) for i in risk}
large = {i for i in risk if abs(cm[i] - H[i]) >= 0.75}
out["large_errors"] = len(large)
for budget in (0.1, 0.2, 0.3):
    k = max(1, round(budget * len(risk)))
    top = sorted(risk, key=lambda i: -risk[i])[:k]
    caught = len(set(top) & large)
    rnd = random.Random(11); sims = [len(set(rnd.sample(list(risk), k)) & large) for _ in range(5000)]
    out[f"escalate_{int(budget*100)}"] = {"k": k, "caught": caught, "random_mean": float(np.mean(sims)),
                                         "p_random_ge": float(np.mean([s >= caught for s in sims]))}
    print(f"  escalate top {int(budget*100)}% (k={k}) by disagreement: caught {caught}/{len(large)} large errors; random {np.mean(sims):.2f} (p={np.mean([s >= caught for s in sims]):.4f})")
json.dump(out, open(f"results_{TAG}.json", "w"), indent=1)
