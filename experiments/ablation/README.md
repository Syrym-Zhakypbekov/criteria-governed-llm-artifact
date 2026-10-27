# Governance ablation (Sections 5.3 and 6.3, Table 8, Figure 5)

Five governance configurations are applied to the **same frozen model output** of each document, so differences
between configurations come from the governance layer only, not from model randomness.

| Config | What it adds |
|---|---|
| C1 | LLM only: every output is accepted |
| C2 | structural check of the raw model JSON |
| C3 | hard veto: 12-digit BIN, at least one item |
| C4 | weighted criteria and escalation (the production gate, τ_S = 0.9) |
| C5 | full operator: applicability from source or model, BIN must occur in the source, graded price evidence (exact value to 0.01), criterion floor, fail-closed handling |

## Files
| File | What |
|---|---|
| `freeze_contracts.ts` | stage 1: one model call per document; stores the raw model JSON, the normalised draft and the source text |
| `apex_jrd_frozen.ts` | the artefact `src/jrd-extract.ts` plus one line that exposes the raw model JSON to stage 1 |
| `freeze_holdout2.ts` | generator of the confirmatory set (43 documents), written and run **after** the final C5 code was frozen |
| `frozen_*.json`, `frozen_h2_*.json` | frozen outputs: development + held-out 1 (79 documents) and held-out 2 (43 documents), two models |
| `ablation.ts` | stage 2 as frozen (SHA-256 in `ablation_freeze.sha256`); no model calls |
| `ablation_replay.ts` | driver-only revision of `ablation.ts` (same decision logic; runs on every set, adds four counterfactual probes) |
| `ablation_*.json`, `ablation_h2_*.json` | per-document routing under C1–C5 |
| `ablation_*_regexv1.json`, `ablation_summary_regexv1.json` | results before the Cyrillic regex correction (identical counts; disclosed in Section 5.3) |
| `ablation_stats.py` | Clopper–Pearson intervals, Cochran's Q, pairwise McNemar mid-p with Holm correction → `ablation_summary.json` |
| `fig_ablation.py` | Figure 5 |
| `ablation_freeze.sha256` | chronology: hashes and UTC times of the frozen operator, the replay driver and the held-out 2 generator |
| `cost_evidence_2710.json` | metered model-call charges and the seven ledger intervals used in Section 6.6 |
| `stubs/`, `tsconfig.json` | offline stubs so the replay runs without the production platform (no model, database or file parsing is called) |

## Reproduce (offline, no API key)
Node.js 20+ and Python 3.11+ with `scipy`.
```
cd experiments/ablation
npx tsx --tsconfig tsconfig.json ablation_replay.ts frozen_gemini-3.8-flash.json      out_dev_38.json
npx tsx --tsconfig tsconfig.json ablation_replay.ts frozen_h2_gemini-3.8-flash.json   out_h2_38.json
# repeat for gemini-3.1-flash-lite; each output is byte-identical to the stored ablation_*.json
python ablation_stats.py ablation_gemini-3.8-flash.json ablation_gemini-3.1-flash-lite.json ablation_h2_gemini-3.8-flash.json ablation_h2_gemini-3.1-flash-lite.json
python fig_ablation.py ablation_summary.json Figure5_ablation.png
```
Re-running stage 1 (`freeze_contracts.ts`) calls the model and needs the production Gemini adapter; its outputs are stored here.
