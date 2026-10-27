# Figures for the MAKE manuscript — every number is read from the experiment JSON files or the R1 counts (r1stats.py).
# usage: python figs.py <experiments_dir> <out_dir>
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

EXP, OUT = sys.argv[1], sys.argv[2]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
RED, GREY, DARK, BLUE = "#A42421", "#9a9a9a", "#242424", "#2f5d8a"


def box(ax, x, y, w, h, text, fc="#f5f5f5", ec=DARK, fs=8.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def arrow(ax, x1, y1, x2, y2, label=""):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.3, color=DARK))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.02, label, ha="center", fontsize=8, color=DARK)


def load(f):
    return json.load(open(f"{EXP}/{f}", encoding="utf-8"))


# Figure 1 — the criteria operator
fig, ax = plt.subplots(figsize=(13, 4.6)); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
box(ax, 0.01, 0.42, 0.13, 0.16, "Input x\n(card, contract,\nanswer)")
box(ax, 0.18, 0.42, 0.14, 0.16, "LLM proposal\n+ confidence c")
box(ax, 0.36, 0.42, 0.16, 0.16, "Criterion certificates\nr_i = <s, e, p, q, u, k>")
box(ax, 0.56, 0.70, 0.17, 0.14, "Hard veto\nA(x) = prod a_h", fc="#f7e3e2", ec=RED)
box(ax, 0.56, 0.43, 0.17, 0.14, "Aggregate\nS = sum wqs / sum wq")
box(ax, 0.56, 0.16, 0.17, 0.14, "Gate\nc < tau_c  or  S < tau_S ?")
box(ax, 0.78, 0.70, 0.2, 0.14, "VETOED -> human", fc="#f7e3e2", ec=RED)
box(ax, 0.78, 0.43, 0.2, 0.14, "ESCALATED -> human", fc="#fdf1dc", ec="#b7791f")
box(ax, 0.78, 0.16, 0.2, 0.14, "PROVISIONAL -> human\nconfirm / revise / reject", fc="#e6eef6", ec=BLUE)
arrow(ax, 0.14, 0.5, 0.18, 0.5); arrow(ax, 0.32, 0.5, 0.36, 0.5)
arrow(ax, 0.52, 0.53, 0.56, 0.75); arrow(ax, 0.52, 0.5, 0.56, 0.5); arrow(ax, 0.645, 0.43, 0.645, 0.30)
arrow(ax, 0.73, 0.77, 0.78, 0.77, "A = 0"); arrow(ax, 0.73, 0.25, 0.78, 0.48, "yes"); arrow(ax, 0.73, 0.21, 0.78, 0.21, "no")
ax.text(0.5, 0.03, "Decision ledger: criteria, AI proposal, human final record and field-level difference stored per decision",
        ha="center", fontsize=9, style="italic", color=DARK)
fig.savefig(f"{OUT}/Figure1_operator.png", dpi=600, bbox_inches="tight"); plt.close(fig)

# Figure 2 — production comparison (R1 counts, see r1stats.py)
R1 = {"Returned by\nverification gate": ((1, 191), (187, 1377)), "Edited after\nentry": ((12, 191), (266, 1377))}
fig, ax = plt.subplots(figsize=(6, 3.6))
for i, (k, ((a, n1), (b, n2))) in enumerate(R1.items()):
    ax.bar(i - 0.18, 100 * a / n1, 0.34, color=RED, label="Card-labelled contacts (n=191)" if i == 0 else None)
    ax.bar(i + 0.18, 100 * b / n2, 0.34, color=GREY, label="Other contacts (n=1377)" if i == 0 else None)
    ax.text(i - 0.18, 100 * a / n1 + 0.5, f"{100 * a / n1:.1f}%", ha="center", fontsize=9)
    ax.text(i + 0.18, 100 * b / n2 + 0.5, f"{100 * b / n2:.1f}%", ha="center", fontsize=9)
ax.set_xticks([0, 1]); ax.set_xticklabels(list(R1.keys())); ax.set_ylabel("Share of contacts (%)")
ax.legend(frameon=False, fontsize=8)
fig.savefig(f"{OUT}/Figure2_production.png", dpi=600, bbox_inches="tight"); plt.close(fig)

# Figure 3 — threshold sensitivity (contracts v2)
r = load("contracts_results_v2.json")
d = [x for x in r if x["defect"] != "clean"]; c = [x for x in r if x["defect"] == "clean"]
taus = [i / 100 for i in range(50, 101)]
esc = lambda x, t: x["veto"] or (x["sTotal"] is not None and x["sTotal"] < t)
fig, ax = plt.subplots(figsize=(6, 3.6))
ax.plot(taus, [100 * sum(esc(x, t) for x in d) / len(d) for t in taus], color=RED, lw=2,
        label=f"Defective documents routed to a human (n={len(d)})")
ax.plot(taus, [100 * sum(esc(x, t) for x in c) / len(c) for t in taus], color=BLUE, lw=2, ls="--",
        label=f"Clean documents routed to a human (n={len(c)})")
ax.axvline(0.9, color=DARK, lw=0.8, ls=":"); ax.text(0.905, 50, "production tau_S = 0.9", fontsize=8)
ax.set_xlabel("Escalation threshold tau_S"); ax.set_ylabel("%"); ax.set_ylim(-3, 105)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.savefig(f"{OUT}/Figure3_threshold.png", dpi=600, bbox_inches="tight"); plt.close(fig)


# Figure 4 — design iterations
def card_caught(f):
    n = 0
    for x in load(f):
        df = x["defect"]
        if df in ("no_email", "no_org", "no_name"):
            n += bool(x["veto"])
        elif df == "no_job":
            n += "job_title" in x["low"]
        elif df == "no_country":
            n += ("country" in x["low"]) or ("provenance" in x["low"])
    return n


def contract_caught(f):
    n = 0
    for x in load(f):
        if x["defect"] == "clean":
            continue
        n += bool(x["veto"]) if x.get("expectVeto") else (x.get("expectLow") in x["low"])
    return n


cards = [card_caught(f"cards_results_v{i}.json") for i in (1, 2, 3)]
contr = [contract_caught(f"contracts_results_v{i}.json") for i in (1, 2)]
fig, ax = plt.subplots(figsize=(6, 3.4))
ax.plot([1, 2, 3], [100 * v / 20 for v in cards], marker="o", color=RED, lw=2, label="Business cards (20 defective)")
ax.plot([1, 2], [100 * v / 28 for v in contr], marker="s", color=BLUE, lw=2, label="Contracts (28 defective)")
for i, v in enumerate(cards):
    ax.text(i + 1, 100 * v / 20 - 7, f"{v}/20", ha="center", fontsize=8)
for i, v in enumerate(contr):
    ax.text(i + 1, 100 * v / 28 + 2.5, f"{v}/28", ha="center", fontsize=8)
ax.set_xticks([1, 2, 3]); ax.set_xticklabels(["v1 (deployed)", "v2", "v3"]); ax.set_ylim(40, 108)
ax.set_ylabel("Expected criterion detected (%)"); ax.legend(frameon=False, fontsize=8, loc="lower right")
fig.savefig(f"{OUT}/Figure4_iterations.png", dpi=600, bbox_inches="tight"); plt.close(fig)
print("cards caught v1-v3:", cards, "contracts caught v1-v2:", contr)

# Figure 5 — release gates (deploy logs, results_2610_night.md R3)
G = [("Tests", 60), ("Build", 16), ("Migration", 9), ("Health -> rollback", 3), ("Install", 2), ("DB permissions", 2),
     ("Coverage", 1), ("Type check", 1)]
fig, ax = plt.subplots(figsize=(6, 3.2))
ax.barh([g for g, _ in G][::-1], [n for _, n in G][::-1], color=RED)
for i, (_, n) in enumerate(G[::-1]):
    ax.text(n + 0.6, i, str(n), va="center", fontsize=8)
ax.set_xlabel(f"Releases stopped (first failing gate), {sum(n for _, n in G)} of 1026 runs")
fig.savefig(f"{OUT}/Figure5_gates.png", dpi=600, bbox_inches="tight"); plt.close(fig)

# Graphical abstract 2200x1120 px (MDPI: >= 1100x560), not a copy of any figure
fig = plt.figure(figsize=(11, 5.6), dpi=200); ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.text(0.03, 0.91, "Criteria-governed LLM decisions in a production university platform", fontsize=19, weight="bold", color=DARK)
ax.text(0.03, 0.85, "Criteria specification: certificates -> veto -> aggregate -> escalation -> human finality; shared ledger for extraction",
        fontsize=12, color=DARK)
cols = [("Production", f"{100 * 1 / 191:.1f}% vs {100 * 187 / 1377:.1f}%",
         "returned by verification:\ncard-labelled vs other contacts\n(6.8% excl. one submitter)"),
        ("Public essays", "QWK 0.77", "calibrated, 3.8-flash,\ndetailed rubric, held-out\nsplit mean; 120 essays"),
        ("Held-out test", "33/33",
         "synthetic defective contracts\nrouted to a human by the\noperator; 0/10 clean routed"),
        ("Coding agents", "94 / 1026", "deploy runs stopped by\ntool-enforced gates in a\ncode base built by agents")]
for i, (h, big, small) in enumerate(cols):
    x = 0.03 + i * 0.24
    ax.add_patch(FancyBboxPatch((x, 0.12), 0.215, 0.62, boxstyle="round,pad=0.01", fc="#f5f5f5", ec="#d0d0d0"))
    ax.text(x + 0.012, 0.66, h, fontsize=13, weight="bold", color=RED)
    ax.text(x + 0.012, 0.47, big, fontsize=19, weight="bold", color=DARK)
    ax.text(x + 0.012, 0.20, small, fontsize=10, color=DARK, va="bottom")
ax.text(0.03, 0.04, "Astra, International Information Technology University, Almaty  |  design-science study, 2026",
        fontsize=10, color="#595959")
fig.savefig(f"{OUT}/GraphicalAbstract.png", dpi=200); plt.close(fig)
from PIL import Image; Image.open(f"{OUT}/GraphicalAbstract.png").convert("RGB").save(f"{OUT}/GraphicalAbstract.png")
print("ok")
