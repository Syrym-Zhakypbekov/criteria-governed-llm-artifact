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
# v4 (27.10, Bykov: «too small, dense, text covered by arrows»): vertical pipeline at journal width (17 cm), text ≥ 10 pt,
# arrows run only between box edges, labels on white background; solid border = in production, dashed = added in this study.
def box2(ax, x, y, w, h, text, fc="#f5f5f5", ec=DARK, fs=10.5, dashed=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008", fc=fc, ec=ec, lw=1.4, ls=(0, (4, 2.5)) if dashed else "-"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def arr(ax, x1, y1, x2, y2, label="", lx=None, ly=None):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", lw=1.4, color=DARK, mutation_scale=14))
    if label:
        ax.text(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else (y1 + y2) / 2, label, ha="center", va="center", fontsize=9.5,
                color=DARK, bbox=dict(fc="white", ec="none", pad=1.5))


fig, ax = plt.subplots(figsize=(6.7, 8.2)); ax.set_xlim(0, 1); ax.set_ylim(-0.18, 1.0); ax.axis("off")
L, W, H = 0.02, 0.56, 0.088          # left pipeline column
R, RW = 0.665, 0.325                  # right outcome column
Y = [0.89, 0.765, 0.64, 0.515, 0.39, 0.255, 0.115]
box2(ax, L, Y[0], W, H, "Input $x$\n(business card, contract, answer)")
box2(ax, L, Y[1], W, H, "LLM proposal (extracted fields)\n+ model confidence $c$")
box2(ax, L, Y[2], W, H, "Criterion certificates\n$r_i=\\langle s_i, e_i, p_i, q_i, u_i, k_i\\rangle$")
box2(ax, L, Y[3], W, H, "Applicability and evidence:\ndoes the criterion apply?\nis the value found in the source?", dashed=True)
box2(ax, L, Y[4], W, H, "Hard veto  $A(x)=\\prod_{h\\in H} a_h(x)$", fc="#f7e3e2", ec=RED)
box2(ax, L, Y[5], W, H + 0.012, "Weighted aggregate\n$S(x)=\\sum_{i\\in G} w_i q_i s_i \\;/\\; \\sum_{i\\in G} w_i q_i$")
box2(ax, L, Y[6], W, H, "Gate:  $c<\\tau_c$  or  $S<\\tau_S$ ?")
box2(ax, R, Y[1], RW, H, "FAIL-CLOSED → human\n(no or invalid\nLLM output)", fc="#f7e3e2", ec=RED, dashed=True)
box2(ax, R, Y[4], RW, H, "VETOED → human", fc="#f7e3e2", ec=RED)
box2(ax, R, Y[6], RW, H, "ESCALATED → human", fc="#fdf1dc", ec="#b7791f")
box2(ax, R, Y[6] - 0.13, RW, H, "PROVISIONAL → human\nconfirm / revise / reject", fc="#e6eef6", ec=BLUE)
cx = L + W / 2
for a, b in zip(Y[:-1], Y[1:]):
    arr(ax, cx, a, cx, b + H + (0.012 if b == Y[5] else 0))
arr(ax, L + W, Y[1] + H / 2, R, Y[1] + H / 2, "error", ly=Y[1] + H / 2 + 0.025)
arr(ax, L + W, Y[4] + H / 2, R, Y[4] + H / 2, "$A=0$", ly=Y[4] + H / 2 + 0.025)
arr(ax, L + W, Y[6] + H / 2, R, Y[6] + H / 2, "yes", ly=Y[6] + H / 2 + 0.025)
arr(ax, cx, Y[6], R, Y[6] - 0.13 + H / 2, "no", lx=cx + 0.10, ly=Y[6] - 0.035)
box2(ax, L, -0.16, 0.97, 0.08, "Decision ledger: criteria, AI proposal,\nhuman final record, field-level difference", fc="#ffffff", fs=10)
ax.text(R + RW / 2, Y[3] + H / 2, "solid: in production\ndashed: added in this study", ha="center", va="center", fontsize=9, color="#595959")
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
ax.axvline(0.9, color=DARK, lw=0.8, ls=":"); ax.text(0.905, 50, "Production $\\tau_S=0.9$", fontsize=8)
ax.set_xlabel("Escalation threshold $\\tau_S$"); ax.set_ylabel("%"); ax.set_ylim(-3, 105)
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
fig.savefig(f"{OUT}/Figure6_gates.png", dpi=600, bbox_inches="tight"); plt.close(fig)

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
ax.text(0.03, 0.04, "QWK: quadratic weighted kappa  |  Astra, International Information Technology University, Almaty  |  design-science study, 2026",
        fontsize=10, color="#595959")
fig.savefig(f"{OUT}/GraphicalAbstract.png", dpi=200); plt.close(fig)
from PIL import Image; Image.open(f"{OUT}/GraphicalAbstract.png").convert("RGB").save(f"{OUT}/GraphicalAbstract.png")
print("ok")
