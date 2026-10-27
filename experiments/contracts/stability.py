# E1: run-to-run stability of the criteria-governed routing decision (contracts, 36 synthetic docs, tau_S = 0.9).
import json, itertools
def load(f): return {x["id"]: x for x in json.load(open(f, encoding="utf-8"))}
runs = {"gemini-3.1-flash-lite": ["results_gemini-3.1-flash-lite.json", "rep_gemini-3.1-flash-lite_r2.json", "rep_gemini-3.1-flash-lite_r3.json"],
        "gemini-3.8-flash": ["contracts_results_v2.json", "rep_gemini-3.8-flash_r2.json", "rep_gemini-3.8-flash_r3.json"]}
route = lambda x: "error" if "error" in x else ("human" if x["veto"] or (x["sTotal"] is not None and x["sTotal"] < 0.9) else "provisional")
def caught(x):
    if "error" in x or x["defect"] == "clean": return None
    return bool(x["veto"]) if x.get("expectVeto") else (x.get("expectLow") in x["low"])
out = {}
for m, fs in runs.items():
    R = [load(f) for f in fs]; ids = sorted(R[0])
    same = sum(len({route(r[i]) for r in R}) == 1 for i in ids)
    sameFull = sum(len({(route(r[i]), tuple(sorted(r[i].get("low", []))), r[i].get("vetoReason")) for r in R}) == 1 for i in ids)
    per = [sum(1 for i in ids if caught(r[i])) for r in R]
    fa = [sum(1 for i in ids if r[i]["defect"] == "clean" and route(r[i]) == "human") for r in R]
    errs = [sum(1 for i in ids if "error" in r[i]) for r in R]
    out[m] = {"docs": len(ids), "routing_identical_all_3": same, "criteria_identical_all_3": sameFull, "caught_per_run": per, "false_alarms_per_run": fa, "errors_per_run": errs}
    print(m, out[m])
json.dump(out, open("stability_results.json", "w"), indent=1)
