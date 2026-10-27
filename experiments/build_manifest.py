# Reproducibility manifest for the MAKE paper (27.10.2026): every experiment -> script, inputs, outputs (sha256, size, mtime),
# model, records; plus metered calls per caller/model from queue.llm_call (pasted from the server query of 27.10 10:40).
# usage: python build_manifest.py <data_aggregates_dir> <out.json>
import hashlib, json, os, sys, datetime
ROOT, OUT = sys.argv[1:3]
def f(p):
    full = os.path.join(ROOT, p); b = open(full, "rb").read()
    n = None
    try:
        j = json.loads(b); n = len(j) if isinstance(j, list) else None
    except Exception:
        if p.endswith(".jsonl"): n = sum(1 for l in b.splitlines() if l.strip())
    return {"path": p, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b), "records": n,
            "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(full)).isoformat(timespec="seconds")}
E = "experiments_2610/"; L = "ellipse_2710/"
X = [
 ("contracts_dev", "Contract planted defects, development v1/v2", [E+"run.ts", E+"an.py", E+"an2.py", E+"tau.py"], [], [E+"contracts_results_v1.json", E+"contracts_results_v2.json"]),
 ("contracts_models", "Contract v2 model comparison", [E+"run.ts"], [], [E+"results_gemini-3.1-flash-lite.json", E+"results_gemini-3.1-pro-preview.json"]),
 ("contracts_stability", "Three repeats of v2, two models", [E+"stability.py"], [], [E+"stability_results.json"]),
 ("contracts_holdout", "Frozen held-out contracts (inputs generated deterministically by run_holdout.ts; production commit 1114a138, tau_S=0.9)", [E+"run_holdout.ts", E+"holdout_an.py"], [], [E+"holdout_gemini-3.1-flash-lite.json", E+"holdout_gemini-3.8-flash.json"]),
 ("cards_dev", "Business-card planted defects v1-v3", [E+"mkcards.py", E+"cards.ts"], [], [E+"cards_results_v1.json", E+"cards_results_v2.json", E+"cards_results_v3.json"]),
 ("cards_holdout", "Frozen held-out business cards (25 new-design PNG + truth.json)", [E+"mkcards_holdout.py", E+"cards_holdout.ts"], [E+"cards_holdout/truth.json"] + [E+"cards_holdout/"+n for n in sorted(os.listdir(os.path.join(ROOT, E+"cards_holdout"))) if n.endswith(".png")], [E+"cards_holdout_gemini-3.5-flash-lite.json", E+"cards_holdout_gemini-3.8-flash.json"]),
 ("ellipse", "ELLIPSE 120 essays x 3 configs x 3 runs x 2 models; calibration, human comparison, uncertainty signals", [L+"build_jobs.py", L+"ellipse_run.ts", L+"analyse.py", L+"calibrate.py", L+"human_compare.py", L+"cross_model.py", L+"uncertainty_signals.py"], [L+"jobs.json"], [L+"ellipse_flashlite.jsonl", L+"ellipse_flash38.jsonl", L+"results_flashlite.json", L+"results_flash38.json", L+"calibration_flashlite.json", L+"calibration_flash38.json", L+"human_compare_flashlite.json", L+"human_compare_flash38.json", L+"cross_model_results.json", L+"uncertainty_signals_results.json"]),
]
man = {"generated": datetime.datetime.now().isoformat(timespec="seconds"), "experiments": []}
for key, desc, scripts, inputs, outputs in X:
    man["experiments"].append({"id": key, "description": desc, "scripts": [f(p) for p in scripts if os.path.exists(os.path.join(ROOT, p))],
                               "inputs": [f(p) for p in inputs], "outputs": [f(p) for p in outputs]})
man["metered_calls_queue_llm_call_26_10_23h_to_27_10_10h25"] = [
 {"caller": "jrd-extract", "model": "gemini-3.1-flash-lite", "n": 151, "failed": 0, "usd": 0.202},
 {"caller": "jrd-extract", "model": "gemini-3.1-pro", "n": 36, "failed": 36, "usd": 0.0, "note": "model id unavailable; rerun as gemini-3.1-pro-preview"},
 {"caller": "jrd-extract", "model": "gemini-3.1-pro-preview", "n": 36, "failed": 0, "usd": 0.755},
 {"caller": "jrd-extract", "model": "gemini-3.5-flash-lite", "n": 1, "failed": 0, "usd": 0.006, "note": "smoke test"},
 {"caller": "jrd-extract", "model": "gemini-3.8-flash", "n": 192, "failed": 0, "usd": 0.594},
 {"caller": "qs.card", "model": "gemini-3.5-flash-lite", "n": 1, "failed": 0, "usd": 0.001, "note": "smoke test"},
 {"caller": "research.ellipse", "model": "gemini-3.1-flash-lite", "n": 1080, "failed": 0, "usd": 0.370},
 {"caller": "research.ellipse", "model": "gemini-3.8-flash", "n": 1080, "failed": 0, "usd": 3.149},
 {"caller": "research.synthetic", "model": "gemini-3.5-flash-lite", "n": 114, "failed": 0, "usd": 0.085},
 {"caller": "research.synthetic", "model": "gemini-3.8-flash", "n": 25, "failed": 0, "usd": 0.072, "note": "4 truncated JSON (HTTP 200) counted as errors in cards_holdout"}]
t = man["metered_calls_queue_llm_call_26_10_23h_to_27_10_10h25"]
man["totals"] = {"calls": sum(r["n"] for r in t), "failed_http": sum(r["failed"] for r in t), "usd": round(sum(r["usd"] for r in t), 3)}
json.dump(man, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False); print(man["totals"]); print([ (e["id"], len(e["outputs"]), [o["records"] for o in e["outputs"]]) for e in man["experiments"]])
