# Held-out frozen-operator evaluation: routed to a human at tau_S = 0.9 (veto or escalation) and expected-criterion hit.
import json, sys
from scipy.stats import beta
cp = lambda k, n: (0 if k == 0 else beta.ppf(.025, k, n - k + 1), 1 if k == n else beta.ppf(.975, k + 1, n - k))
for f in sys.argv[1:]:
    r = json.load(open(f, encoding="utf-8")); err = [x for x in r if "error" in x]; ok = [x for x in r if "error" not in x]
    clean = [x for x in ok if not x["defects"]]; bad = [x for x in ok if x["defects"]]
    fa = sum(x["routed"] for x in clean); routed = sum(x["routed"] for x in bad); hit = sum(x["criterionHit"] for x in bad)
    print(f, "| docs", len(r), "errors", len(err))
    print(f"  clean routed (false alarm): {fa}/{len(clean)}  CI {[round(v,3) for v in cp(fa,len(clean))]}")
    print(f"  defective routed to human: {routed}/{len(bad)}  CI {[round(v,3) for v in cp(routed,len(bad))]}")
    print(f"  expected criterion fired: {hit}/{len(bad)}")
    for x in bad:
        if not x["routed"] or not x["criterionHit"]: print("   MISS", x["id"], x["state"], x.get("sTotal"), x["low"], x.get("vetoReason"))
