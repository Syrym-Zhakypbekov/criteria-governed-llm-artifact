# Figure 5 (v4, 27.10.2026): governance ablation — share of defective documents routed to a human per configuration C1–C5,
# development vs held-out, two models, Clopper–Pearson 95% intervals; read from ablation_summary.json (ablation_stats.py).
# usage: python fig_ablation.py <ablation_summary.json> <out_png>
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

S = json.load(open(sys.argv[1], encoding="utf-8"))
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
CFG = ["C1", "C2", "C3", "C4", "C5"]
LAB = ["C1\nLLM only", "C2\n+ structure", "C3\n+ hard veto", "C4\n+ weighted,\nescalation", "C5\nfull\noperator"]
COL = {"gemini-3.8-flash": "#A42421", "gemini-3.1-flash-lite": "#2f5d8a"}
PANELS = [("dev", "(a) Development\n28 defective, 8 clean"), ("holdout", "(b) Held-out 1 (exposed)\n33 defective, 10 clean"),
          ("holdout2", "(c) Held-out 2 (confirmatory)\n33 defective, 10 clean")]
fig, axes = plt.subplots(1, 3, figsize=(6.7, 3.4), sharey=True)
for ax, (st, title) in zip(axes, PANELS):
    for j, (m, c) in enumerate(COL.items()):
        rec = next(r for r in S if r["model"] == m and r["set"] == st)
        xs = [i + (j - 0.5) * 0.36 for i in range(len(CFG))]
        ys = [rec["configs"][k]["routed_pct"] for k in CFG]
        lo = [ys[i] - rec["configs"][k]["routed_ci"][0] for i, k in enumerate(CFG)]
        hi = [rec["configs"][k]["routed_ci"][1] - ys[i] for i, k in enumerate(CFG)]
        ax.bar(xs, ys, width=0.34, color=c, label=m.replace("gemini-", ""), yerr=[lo, hi], capsize=2, error_kw={"lw": 0.8})
        fa = sum(rec["configs"][k]["false_alarms"] for k in CFG)
    ax.set_xticks(range(len(CFG))); ax.set_xticklabels(CFG, fontsize=10)
    ax.set_title(title, fontsize=9); ax.set_ylim(0, 108)
axes[0].set_ylabel("Defective documents routed\nto a human (%)")
h, l = axes[0].get_legend_handles_labels(); fig.legend(h, l, ncol=2, fontsize=8.5, frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.07))
fig.text(0.5, -0.13, "False alarms on clean documents: 0 in every configuration, set and model.", ha="center", fontsize=9, color="#595959")
fig.tight_layout(); fig.savefig(sys.argv[2], dpi=600, bbox_inches="tight"); plt.close(fig)
print("ok")
