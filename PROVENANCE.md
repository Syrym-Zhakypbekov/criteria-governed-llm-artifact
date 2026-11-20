# Provenance of the archived source files and prompts

This note answers two questions raised in review of the MAKE article (November 2026): how the archived source files
correspond to the platform version used in the experiments (commit `1114a138`), and how prompt fingerprints are
computed, stored and linked to results. Run `python verify_deidentification.py` to check the first part yourself.

## 1. Archived files versus platform commit 1114a138

Appendix A of the article gives SHA-256 prefixes of three platform files at commit `1114a138`:

| Archive file | Platform path at 1114a138 | SHA-256 at 1114a138 (Appendix A) | SHA-256 of the archived file |
|---|---|---|---|
| `src/jrd-extract.ts` | `apps/legal/lib/jrd-extract.ts` | `1c07b6322ce2…` | `4fb1a43f022b…` |
| `src/card-ocr.ts` | `apps/kafedra/lib/qs/card-ocr.ts` | `05fe1acd0734…` | `cc25f3f36150…` (v1.0–v1.2); `238a4013513b…` (v1.3) |
| `src/decision-ledger.ts` | `lib/decision-ledger.ts` | `5f9b2d699dd7…` | `5f9b2d699dd7…` (identical) |

**Why two hashes differ.** Before publication, the archived copies of `jrd-extract.ts` and `card-ocr.ts` were
de-identified: names of university staff that appeared in code comments (who reported an issue, on which date) were
replaced by their roles, for example «юрист» (lawyer) or «заведующий кафедрой» (head of department). Ten lines changed in
total (nine in `jrd-extract.ts`, one in `card-ocr.ts`); every one of them is a comment line. No executable line, no
prompt text and no line count changed. `decision-ledger.ts` contained no names and was archived unchanged, so its hash
matches Appendix A. Earlier archive versions (v1.0–v1.2-make) did not state this de-identification; this note corrects
that omission. In v1.3-make one further staff name left in the first comment line of `card-ocr.ts` was replaced by a
role; this is again a comment-only change, so the comment-stripped hash below is unchanged.

**How to check it.** `verify_deidentification.py` removes every line whose first non-blank characters are `//`, `*` or
`/*` (comment-only lines; Windows line endings normalised to LF) and hashes the rest. The same rule applied to the
platform originals at `1114a138` gives the recorded values:

| File | SHA-256 without comment lines (archive = platform 1114a138) |
|---|---|
| `jrd-extract.ts` | `7b5d748973374d2ad39d23065380a6700c638e7383cb68252cc76db2f7965ede` |
| `card-ocr.ts` | `c94339cc796abc665607cb0778836f9705755ffe0d63904ede3bac8a6758fa76` |
| `decision-ledger.ts` | `86349227c533d0652d3db24a38e1044e21b7d93546265ce3700328e9f2b337e0` |

The platform repository is private (it contains personal data of applicants and staff), so the original files with
names are not published; the recorded hashes of both the full originals and their comment-stripped forms let a reader
with platform access, or an editor on request, confirm the correspondence.

## 2. Prompt fingerprints: what is stored, and what is not

- **Contract extraction (`jrd-extract.ts`) and business-card reading (`card-ocr.ts`).** The prompts are string constants
  inside these source files. The prompt used in an experiment is therefore identified by the source file at commit
  `1114a138` (Section 1). These two workflows do **not** store a per-call prompt hash, and the per-call result files in
  `experiments/contracts/` and `experiments/business_cards/` record inputs, criterion results, states and timings, not a
  prompt hash. The statement in the submitted manuscript that «each production LLM call also stores its own prompt
  hash» was too general and is corrected in the revision.
- **AI grading of written work and spoken answers.** These workflows compute
  `sha256(systemPrefix + " " + userBody)` (`hashPrompt` in `lib/ai-grade/prompt.ts` at `1114a138`) for every call and
  store it with the score (`ai_grade.prompt_hash`), so each stored score can be linked to the exact prompt text.
- **Offline replays (ablation, frozen C5).** They make no model calls; they replay stored model outputs. Their code is
  frozen by the hashes in `experiments/ablation/ablation_freeze.sha256`.

## 3. Revision v1.3-make (November 2026, response to the MAKE reviews)

- Added: this note and `verify_deidentification.py` (section 1); `experiments/verification/` with three checks written
  separately from the original analysis scripts — `planted_truth_check.py` (planted defect labels of all 122 synthetic
  contracts re-derived from the source text: 122/122), `recount_headlines.py` (37 assertions on headline counts, exact
  intervals and stored summaries: all pass) and `rounding_check.ts` (production four-decimal rounding of the aggregate
  changes 0 of 244 routing decisions).
- Removed: the LLM topic re-annotation and answer-grading material (`ANNOTATION_PROTOCOL.md`, `EXECUTION_RECORD.md`,
  `topic_labels_300.csv`, `qa_grades_150.csv`) and their sampling queries. These analyses supplied individual question and
  answer texts to an external model and were removed from the revised article. Earlier archive versions are unchanged.
- The submitted version v1.2-make (doi:10.5281/zenodo.23719854) remains available unchanged.
