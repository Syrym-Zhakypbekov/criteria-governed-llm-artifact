# Pilot speaking calibration (MAKE §5.2/§6.2): Spearman rho between the AI total (0-100) and the mean expert score
# for the 13 spoken items (work_v1 calibration study, 49 ratings of 4 active non-excluded raters), item-level percentile
# bootstrap with 10,000 resamples (numpy default_rng, seed 2710; resamples with a constant vector are skipped), and
# MAE/bias after the linear mapping 1 + 4*x/100. Inputs are aggregates only (no student or rater identifiers).
# usage: python pilot_speaking_rho.py
import json, numpy as np
from scipy.stats import spearmanr
ai = np.array([21, 23, 23, 33, 33, 33, 37.2, 38, 54, 60, 64, 64, 85.0])
expert = np.array([2.85, 2.7333, 3.3, 2.35, 2.6667, 3.1, 3.8, 2.8667, 3.65, 4.15, 3.4, 4.05, 4.7])
rho = spearmanr(ai, expert)
rng = np.random.default_rng(2710); boot = []; skipped = 0
for _ in range(10000):
    i = rng.integers(0, 13, 13)
    if len(set(ai[i])) < 2 or len(set(expert[i])) < 2: skipped += 1; continue
    boot.append(spearmanr(ai[i], expert[i]).statistic)
m = 1 + 4 * ai / 100
out = {"n_items": 13, "rho": round(float(rho.statistic), 3), "p": round(float(rho.pvalue), 4),
       "ci95": [round(float(np.percentile(boot, 2.5)), 2), round(float(np.percentile(boot, 97.5)), 2)],
       "resamples": 10000, "skipped_constant": skipped, "seed": 2710,
       "mae_1to5": round(float(np.mean(np.abs(m - expert))), 3), "bias_1to5": round(float(np.mean(m - expert)), 3)}
json.dump(out, open("pilot_speaking_rho_results.json", "w"), indent=1); print(out)
