# Criteria-governed LLM decisions — research artefact

Code, prompts, synthetic test inputs, analysis scripts and aggregate results for the manuscript
«Criteria-Governed Large Language Model Agents in a Production University Platform: A Design-Science Study of Criterion-Traceable Knowledge Extraction and Decision-Making» (submitted to MDPI *Machine Learning and Knowledge Extraction*).

This repository contains **only the parts needed to reproduce the study**. The production platform (Astra,
International Information Technology University, Almaty) is not published. No personal data is included.

## Contents
| Path | What |
|---|---|
| `src/decision-ledger.ts` | implemented operator: criterion codes and scores, hard veto, weighted aggregate (input-quality weight default 1), escalation gate, lifecycle, field-level diff, best-effort ledger writes |
| `src/jrd-extract.ts` | contract extraction prompt, normalisation and criteria (`jrdCriteria`) |
| `src/card-ocr.ts` | business-card extraction prompt, schema, provenance criteria (`cardCriteria`) |
| `experiments/contracts/` | planted-defect generator and runner (36 synthetic supplier documents), threshold and stability analysis, figures |
| `experiments/business_cards/` | development (28) and held-out (25, `holdout_cards/`) synthetic card images, generators, runners and per-call outputs; `*.orig.json` = original records, same name without `.orig` = corrected record (`routed` = state vetoed/escalated, `flagged` = any soft criterion below 1) |
| `experiments/ellipse/` | public ELLIPSE benchmark: essay ids and human scores (`jobs_ids_scores.json`, no essay texts), per-call model outputs (`ellipse_*.jsonl`), analysis scripts and their outputs |
| `results/` | per-document outputs of the contract and card development runs and repeated runs; `astra_evolution_20261026.md` (repository and deploy aggregates) |
| `figures/` | Figures 1–5 and the graphical abstract; generator in `figures/src/figs.py` |
| `context_facts_2710.md` | SQL and results for every contextual number in the paper and an experiment-level reconciliation of metered call counts (2716 calls) |
| `MANIFEST.json` | SHA-256, size and record count of every file in this repository (`build_repo_manifest.py`) |

## Reproduce
**Scope.** The repository supports reanalysis of all stored experimental outputs without access to the production platform. Re-executing the model calls requires the production model adapter and configuration (Gemini via Vertex AI; parameters in Appendix A of the paper), which are not released; the extraction sources in `src/` are the final operator version, and the development versions are described in Section 6.3 of the paper.

Python 3.11+, `pip install numpy pandas scipy scikit-learn matplotlib`. From `experiments/ellipse/`, with `ellipsis_raw_rater_scores_anon_all_essay.csv` downloaded from https://github.com/scrosseye/ELLIPSE-Corpus:
```
python analyse.py jobs_ids_scores.json ellipsis_raw_rater_scores_anon_all_essay.csv ellipse_flashlite.jsonl flashlite   # Table 8 raw columns
python calibrate.py jobs_ids_scores.json ellipse_flashlite.jsonl flashlite     # Table 8 calibrated columns
python human_compare.py jobs_ids_scores.json ellipsis_raw_rater_scores_anon_all_essay.csv ellipse_flashlite.jsonl flashlite
python uncertainty_signals.py jobs_ids_scores.json ellipse_flashlite.jsonl ellipse_flash38.jsonl   # Table 9
python matched_signals.py    jobs_ids_scores.json ellipse_flashlite.jsonl ellipse_flash38.jsonl   # matched before/after calibration
python cross_model.py         jobs_ids_scores.json ellipse_flashlite.jsonl ellipse_flash38.jsonl   # ensemble
```
(repeat the first three with `ellipse_flash38.jsonl flash38`). Contract and card counts are recomputed from the per-call JSON files (`holdout_an.py`, `stability.py`). Results of LLM calls are not exactly reproducible across model versions; every output used in the paper is stored here.

## Data and licences
- Code: MIT licence (see `LICENSE`).
- Synthetic contracts and business cards were generated for this study; any resemblance to real organisations or persons is coincidental.
- ELLIPSE corpus: Crossley, S.A. et al. (2023), *International Journal of Learner Corpus Research* 9(2), 248–269, doi:10.1075/ijlcr.22026.cro — CC BY-NC-SA 4.0. Only model outputs and essay identifiers are redistributed here; essay texts must be obtained from the original repository.
- Production data of the university (business-card contacts, contract drafts, assessments) cannot be shared under the Law of the Republic of Kazakhstan «On Personal Data and Their Protection» No. 94-V; only aggregates reported in the paper are released.

## Cite
Zhakypbekov, S. (2026). Research artefact for «Criteria-Governed Large Language Model Agents in a Production University Platform». Zenodo. doi:[to be assigned]
