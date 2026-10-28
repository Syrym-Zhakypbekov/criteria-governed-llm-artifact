# External baselines for the frozen governance ablation

This experiment adds off-the-shelf strict validation (B1) and an LLM-free,
guardrail-style extension (B2) to the existing C2/C4 comparison. The 244 frozen
model-document records comprise the same 36 development, 43 held-out-1 and 43
held-out-2 documents for each of two models. No model calls, source extraction,
normalisation, output repair, or production services are used.

These baselines were implemented after all three sets were available. They are
retrospective comparators, not a newly preregistered confirmatory evaluation.
The same rules are applied unchanged to every model and set.

## Run

From the repository root, with Python 3.11 or later:

```powershell
python -m pip install -r experiments/baseline/requirements.txt
python -B experiments/baseline/baseline_schema.py
python -B experiments/baseline/test_baseline.py
```

On the owner's machine the actual interpreter used is
`C:/Users/syrym/miniforge3/envs/admission/python.exe`. Both dependencies were already
installed; no environment changes were needed. Versions used: pydantic **2.14.1**, pydantic-core **2.50.1**, jsonschema **4.26.0**, python **3.15.1**.
For an exact library rerun, install `pydantic==2.14.1 jsonschema==4.26.0`.
The implementation needs only Pydantic and jsonschema plus the Python standard
library. The test optionally checks numerical parity against the original
SciPy-based statistics functions if SciPy is installed; SciPy is not a runtime
dependency of the baselines.

All generated outputs go beside the script, regardless of the working directory.
Existing experiment files are read only. The original statistics script is never
executed as a command (it would overwrite a summary). No commits are made.

## B1: strict schema

`baseline_schema.py` defines nested Pydantic v2 models with `strict=True` and
`extra="forbid"`; `baseline_json_schema.json` is their equivalent Draft 2020-12
schema. Both libraries validate every raw output independently; a disagreement
aborts the run. Any validation error routes the document to a human.
No normalised draft, source text, ground truth, or planted label enters either
baseline validator. Labels are used only after validation to score tracing.

Required fields follow the raw extraction prompt in `apex_jrd_frozen.ts`:

| Object | Required fields |
|---|---|
| Root | `supplier`, `contract`, `items`, `third_party` |
| Supplier | `name`, `bin`, `address`, `phone`, `email`, `iban`, `bank`, `bik`, `director` |
| Contract | `number`, `date`, `basis`, `vat_rate`, `with_vat`, `kind`, `from`, `until`, `addendum` |
| Item | `name`, `description`, `qty`, `unit`, `unit_price_with_vat`, `ktru_hints` |
| Non-null third party | `fio`, `iin`, `email`, `phone`, `role` |
| Non-null addendum | `base_number`, `base_date` |

- Supplier BIN is a string matching exactly the requested `^\d{12}$` pattern.
  It is not converted to a string, padded, stripped, or checked against a source.
- `items` must contain at least one object. Unit prices are JSON numbers >= 0.
  Numeric strings, booleans and null are rejected. Integer and floating-point
  JSON numbers are both accepted. Quantity and VAT rate are strict numbers;
  `with_vat` is a strict boolean. Zero prices pass B1.
- There is **no VAT enum declaration** in either the frozen extraction module or
  `src/jrd-extract.ts`. Prompt examples of 0, 12 and 16 do not constitute an enum.
  B1 therefore does not invent an exhaustive VAT enum from observed outputs.
  `kind` does have an explicit enum: `goods`, `services`, `works`.
- Supplier and emitted third-party e-mails use jsonschema's standard
  `FormatChecker("email")`, also invoked by Pydantic to keep acceptance equivalent.
  Empty e-mails fail this format. This is the library's deliberately minimal
  syntax check, not a deliverability/DNS check or a full RFC mailbox parser.
  No `email-validator` extra dependency is required.
- Dates are strings: `""` means no date was extracted, otherwise a real ISO
  `YYYY-MM-DD` calendar date is required using `FormatChecker("date")`.
  This includes `contract.date/from/until` and an emitted addendum's `base_date`.
  The old prompt requests DD.MM.YYYY in places; B1 follows the requested ISO
  baseline instead. No non-empty dates occur in this frozen corpus, so this
  choice does not alter the reported counts.
- Plain string fields may be empty in B1; this respects the extraction prompt's
  missing-value convention. Nullable third-party and addendum objects may be
  null, but their keys must be present. No object is inferred from source text.
  Unknown fields are rejected. `ktru_hints` is a list of strings, possibly empty.
- Optional numeric, nonnegative `total` and `contract.total` fields are supported
  as an explicitly documented extension for the arithmetic guardrail. They may
  be absent or null. All other required fields are defined above.

Pydantic runs on the original decoded JSON, without a preliminary coercion or
the repository's `normalizeDraft`. The run records both libraries' error details.
Tracing uses JSON Schema's canonical raw field locations, avoiding Pydantic's
union-branch names in error locations.

Library references: [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/)
and [jsonschema validation and explicit format checking](https://python-jsonschema.readthedocs.io/en/stable/validate/).

## B2: schema plus generic guardrails

B2 is the union of B1 errors and the following deterministic validators, in the
style of reusable guardrail libraries. It does not claim to run Guardrails AI.
Each additional failure immediately routes the document; there is no weighted
score, applicability inference, criterion floor, or hard-veto hierarchy.

1. **Valid range:** quantity > 0, unit price > 0, VAT rate in [0, 100]. Positive
   transaction values are a declared practitioner choice: B2 flags zero-price
   lines, including possible genuine free items in another corpus. B1 permits 0.
   Zero VAT is valid regardless of `with_vat`; there is no domain-specific rule
   requiring an explicit positive VAT rate or interpreting warning strings.
2. **Non-empty strings (after a whitespace-only check, with no data mutation):**
   supplier `name/email`; item `name/unit`; emitted third-party `fio/email`;
   emitted addendum `base_number/base_date`. Optional descriptive/contact fields
   such as address, phone, bank, and free-text basis may remain empty. A missing
   key is handled by B1. A null addendum/third party is not made applicable by B2.
3. **Reusable e-mail regex:** supplier/third-party e-mail must match
   `[^\s@]+@[^\s@]+\.[^\s@]+` as a full string, requiring a dotted domain and no
   whitespace. BIN regex and list non-emptiness are inherited from B1.
4. **Totals:** when a root `total` or `contract.total` is independently supplied
   in raw JSON, check `abs(sum(qty * unit_price_with_vat) - total) <= 1 KZT`.
   Arithmetic uses Decimal from the JSON numbers' string representations, and
   the 1 KZT boundary is inclusive. Both totals are checked if both are supplied.
   Missing/null total -> `not_applicable`; malformed operands -> `not_evaluable`
   (their schema failures already route the output).

**None of the 244 frozen raw outputs supplies a total.** The totals check is
implemented and boundary-tested, but not applicable to every corpus row.
`truth.total` is never accessed by the baseline. The total produced by `jrdFlat`
is itself the sum of extracted items, so reusing it would be a tautological test.
The validators' API accepts only `raw`, preventing source/ground-truth leakage.

There are no numeric-string prices in the frozen corpus. Tests nevertheless
verify that strings such as `"2450"` fail both strict validators without coercion.

## Routing and tracing

As in `ablation_replay.ts`, routed means state `escalated` or `vetoed` (B1/B2 use
`escalated`). A defective document is traced only if it is routed **and every
planted defect** has a matching failure code. Non-routed and clean rows carry
`traced=null`, exactly as in the replay. An unrelated error can route a document
without tracing its planted defect.

The script parses the replay's actual `EXPECT` mapping, rather than maintaining
a different set of labels. Baseline error fields translate to its criterion codes:

| Actual failing raw field | Replay code |
|---|---|
| `supplier.bin` | `bin` (covers short/missing/long BIN) |
| `items` | `items` |
| `items[i].unit_price_with_vat` | `prices` |
| `contract.vat_rate` | `vat_explicit` |
| `third_party.email` | `third_party_email` |
| `contract.addendum.base_number` or `.base_date` | `addendum_base` |

Other failures can route but do not earn planted-defect credit. A missing parent
object is not expanded to failures of hypothetical children. No baseline emits
`bin_evidence` or `price_evidence`. Missing model output is a root-schema failure;
this routes but cannot trace a specific planted defect. The frozen files have no
extraction errors, so differing error-state policies do not affect this experiment.

## Paired statistics and reference verification

The primary McNemar endpoint is **routing on defective documents**, exactly as in
`ablation_stats.py`. The pairs are B1 vs C2, B1 vs C4, B2 vs C4. Two-sided mid-p is
`min(1, 2*BinomCDF(k,n,0.5) - BinomPMF(k,n,0.5))`, with k the smaller discordant
count; no discordance gives p=1. Holm uses these three comparisons as its family,
separately for each model-set. The JSON also includes supplementary tracing and
clean-document false-alarm tests, each with a separate three-comparison Holm
family; they are not pooled with the primary tests.

Clopper-Pearson 95% intervals use standard-library binomial-tail inversion;
they reproduce the original SciPy beta-quantile intervals at the original
one-decimal percentage precision. Exact integer binomial coefficients compute
mid-p without adding SciPy to the baseline requirements.

For every record, an independent Python translation of C2/C4 is evaluated using
the frozen raw JSON and frozen normalised draft. It must equal the archived
per-document state, ordered failure codes, routed flag and traced flag. These
reference validators are separate from the raw-only B1/B2 functions. Pairing
uses `(model, set, id)`, verifies unique/exhaustive keys and identical defect
labels, and never relies on row order.

The displayed C2/C4 figures are taken from `ablation_summary.json` only after
recomputed counts, percentages and intervals match. All overlapping C2/C4
entries in `ablation_summary_main.json`, `ablation_summary_h2.json` and the
historical `ablation_summary_regexv1.json` must match too. Set sizes must be
28 defective + 8 clean (development), and 33 + 10 (each held-out set).

## Files and validation

- `baseline_schema.py`: models, validators, independent reference replay,
  statistics, provenance and output generation.
- `requirements.txt`: the two external runtime dependencies.
- `baseline_json_schema.json`: exported Draft 2020-12 contract.
- `baseline_results.json`: counts, intervals, paired discordances/p-values,
  per-document field errors and traces, versions, and input hashes.
- `baseline_table.md`: Table 8 columns, plus primary paired-test tables.
- `test_baseline.py`: strict-type/format/range/compound-trace/totals boundary
  tests, schema equivalence, optional numerical reference comparison, and
  verification that pre-existing repository files have not changed.
- `README.template.md`: source for this generated README.
- `preexisting_files.sha256.json`: hashes recorded before implementation of all
  164 pre-existing non-git repository files, for the no-existing-file-edit check.

The baseline is fixed across sets, but its strength depends on the stated schema
and guardrail choices. It cannot verify a syntactically valid fabricated BIN or
price against the source. Do not interpret a routing improvement as evidence
that such errors have been traced, or as an independent model-quality gain.

## SHA-256 of inputs

Paths are relative to the repository root. The manifest includes frozen outputs,
per-document reference results, every summary read, the source files inspected
for the experiment definitions, and baseline source/requirements/README template.
Input bytes are rechecked before outputs are written. Repository-wide hashes for
the unchanged-file audit are in `preexisting_files.sha256.json`.

| Input file | SHA-256 |
|---|---|
| `experiments/ablation/README.md` | `9820d5defbc7007dff6ffb7cf27a4f7fdc3e2799bcdb128c9aa405687937ac9f` |
| `experiments/ablation/ablation.ts` | `883d602ac00836c37400700d0dcc450e0797c9550b7c54f3482a5574db75e93e` |
| `experiments/ablation/ablation_gemini-3.1-flash-lite.json` | `62a2b36e8e1fa6c6687b5e559e8657258daf54cdc163d6a315949dd18de8e991` |
| `experiments/ablation/ablation_gemini-3.8-flash.json` | `75534905d6cfebdd0602c35ccaf3d583caa3fcb090b176be1d2fd70577fef7af` |
| `experiments/ablation/ablation_h2_gemini-3.1-flash-lite.json` | `ed6283dd96ac3e761debdffa75c79e2a7cc29adf89d1015ef60faaacf80de657` |
| `experiments/ablation/ablation_h2_gemini-3.8-flash.json` | `c2c33fd40f0f6a3587e6220b1400fc343d31c5870295e62eafdcf9a003678f0a` |
| `experiments/ablation/ablation_replay.ts` | `4b4e0add3aac01900451297d40f9bff8775d4003350c8a16fb4ba15e6de19cc3` |
| `experiments/ablation/ablation_stats.py` | `5b8f02a2a1f16b308673decdeaea8494af168b4d6f560effc9b7c96660882075` |
| `experiments/ablation/ablation_summary.json` | `a64bb7fb6a243056ac2a319a34cdd0c8ba2414c1f9db110c645c1a5274e29e9d` |
| `experiments/ablation/ablation_summary_h2.json` | `b7e9294fbacee0106cd89872c10a0ac6195a4a42c2fd3e92fb3600c53fd4f005` |
| `experiments/ablation/ablation_summary_main.json` | `5349224af11fa1db21820d257637b340e49de3732a1540f323cfe49de4d9c672` |
| `experiments/ablation/ablation_summary_regexv1.json` | `5349224af11fa1db21820d257637b340e49de3732a1540f323cfe49de4d9c672` |
| `experiments/ablation/apex_jrd_frozen.ts` | `d6153c72ddd4327666822e1540d96281f8cc6069905efb64b804e6ce526018f1` |
| `experiments/ablation/freeze_contracts.ts` | `7f191fa51e8c747feb1a05abb9c590ea9f9bc9afec85cfbd99cfa7bd1563d36c` |
| `experiments/ablation/freeze_holdout2.ts` | `0aa5afc9e4badaa8f02d6c1e05c208405ce087600f684c8e52584abc1b855c45` |
| `experiments/ablation/frozen_gemini-3.1-flash-lite.json` | `34de645682d7abeea4a828a348b4f851306ba4acb1746e0a994060dd2081e6c6` |
| `experiments/ablation/frozen_gemini-3.8-flash.json` | `dd756c6ce9103d6e74a57e88b41fc2972e15145c1113ed1d64a3cd6ec5dc4168` |
| `experiments/ablation/frozen_h2_gemini-3.1-flash-lite.json` | `81e2ed9d41dd7befd3bf62af0b0ac2d66c1b2262a1acd3dbcb86b3571bd10df0` |
| `experiments/ablation/frozen_h2_gemini-3.8-flash.json` | `fa66ddf6ecfdd15b08feb19c980d8e57405fd613aaed00c6ee58cbfaecb68430` |
| `experiments/ablation/tsconfig.json` | `42bceb93142311b14d5c912091c755b76e9cc3667a36e0e0d3685060ac1bee74` |
| `experiments/baseline/README.template.md` | `1d0c8c1552eee5787eec30a85305d05c6bb1d7549aa89dae3afd01b135ba73fd` |
| `experiments/baseline/baseline_schema.py` | `2e63110b6fcaf843c6152fabd459df41506e19bcf8b55b8b263c31887d984127` |
| `experiments/baseline/requirements.txt` | `92594728fc623441efbd00a87d0e1dbc7329672be2a872f1bddef1652e6107c0` |
| `experiments/baseline/test_baseline.py` | `a809fae3db3f57dc1fb5f1ce115534ff0ad2e8b692535f843f13c68b9378f3eb` |
| `src/jrd-extract.ts` | `4fb1a43f022b7f0df6f1a33453e09ce9f9ed43308ab65240afbafdb571455781` |
