# Context facts for the MAKE manuscript — queries and results (27.10.2026, warp_iitu, read-only)

Every contextual number in Sections 1, 4, 6.1, 6.3, 6.6 comes from one of the queries below (run 27.10.2026 10:55–11:05 Almaty).

| Fact in manuscript | Query | Result |
|---|---|---|
| User accounts | `SELECT count(*) FROM queue.users` | 7487 |
| Visits and people, 26.09–26.10.2026 (Almaty) | `SELECT count(*), count(DISTINCT user_id) FROM queue.presence_log WHERE started_at >= '2026-09-26 00:00+05' AND started_at < '2026-10-26 00:00+05'` | 54072 visits, 429 people |
| Active menu sections | `SELECT count(*) FILTER (WHERE coalesce(archived,false)=false) FROM queue.nav_items` | 79 (171 incl. archived) |
| Top-level sections visited in the same window | `SELECT count(DISTINCT split_part(page,'/',2)) FILTER (WHERE split_part(page,'/',2) <> '') FROM queue.presence_log WHERE <same window> AND page IS NOT NULL` | 50 |
| LLM calls and cost before the study | `SELECT count(*), sum(est_usd) FROM queue.llm_call WHERE ts < '2026-10-26 18:00+00'` | 2029 calls, USD 3.77 |
| Reviewer comments on first return of QS contacts (returns 1–23.10) | first `qs_audit` row per contact with `action='state'` and `detail->>'state'='needs_fix'`, `at` in [01.10, 24.10 00:00+05), comment text matched per field | industry 102, country 22, subject 14, job title 11, e-mail 10, department 1 |
| Card-call failures, gemini-3.8-flash | `queue.llm_call` caller `research.synthetic`, model `gemini-3.8-flash`, 27.10 10:20–10:26 | 4 calls with thought_tokens 979–981 and out_tokens 29–31 (total 1009–1010 of the 1024-token limit); all other calls ≤ 655 |

Note: the earlier figures «427 people / 53,908 visits» were a rolling now()−30 days window run at ~23:50 on 26.10 (re-run with that window: 53,924 / 427) and are replaced by the fixed calendar window above.

## Call reconciliation (queue.llm_call, 26.10 23:00 – 27.10 10:30 Almaty)

| Experiment | Model | New calls | Note |
|---|---|---:|---|
| ELLIPSE essays | gemini-3.1-flash-lite | 1080 | |
| ELLIPSE essays | gemini-3.8-flash | 1080 | |
| Contracts v1 (development) | gemini-3.8-flash | 36 | 26.10 23:30 |
| Contracts v2 (development) | gemini-3.8-flash | 36 | 26.10 23:35; also run 1 of the stability test |
| Contracts v2, model comparison | gemini-3.1-flash-lite | 36 | 26.10 23:55; also run 1 of the stability test |
| Contracts v2, model comparison | gemini-3.1-pro (unavailable id) | 36 | all failed (HTTP error), rerun as preview |
| Contracts v2, model comparison | gemini-3.1-pro-preview | 36 | |
| Contract stability, runs 2–3 | gemini-3.1-flash-lite | 72 | 27.10 09:15 |
| Contract stability, runs 2–3 | gemini-3.8-flash | 72 | 27.10 09:15–09:20 |
| Contract held-out | gemini-3.1-flash-lite | 43 | 27.10 09:50 |
| Contract held-out | gemini-3.8-flash | 43 | 27.10 09:45–09:50 |
| Business cards v1–v3 | gemini-3.5-flash-lite | 84 | 26.10 23:30–23:50 |
| Business-card held-out | gemini-3.5-flash-lite | 25 | 27.10 10:20 |
| Business-card held-out | gemini-3.8-flash | 25 | 27.10 10:20–10:25 |
| Interrupted/debugging calls, outputs not used | gemini-3.8-flash (contracts) | 5 | |
| Interrupted/debugging calls, outputs not used | gemini-3.5-flash-lite (cards) | 5 | |
| Smoke tests | qs.card / jrd-extract | 2 | |
| **Total** | | **2716** | USD 5.234 |

Evaluation calls with used outputs: 2668 (+36 failed, +10 unused, +2 smoke tests = 2716).

## Speaking/text model allocation in the expert calibration study (work_v1)
`SELECT i.stratum, s.model_version, s.provider, count(*) FROM work_v1.calibration_study_item i LEFT JOIN work_v1.answer_scores s ON s.id = i.ai_score_id GROUP BY 1,2,3`
AUDIO: gemini-2.5-flash 5 (recording) · gemini-2.5-flash-lite 1 (recording) + 7 (transcript) = 13. CHAT: gemini-2.5-flash 10 · gemini-2.5-flash-lite 11 · deepseek-chat 1 = 22.

## Expert calibration sample (work_v1.calibration_study notes, items → turns → exam_sessions)
Stratified random sample, seeded, fraction 0.25 of eligible answers (completed sessions, ≥5 words): recordings 6/25, transcript-only spoken 7/26, text 22/88; 35 items from 35 distinct students (max one per student per stratum). AI 0–100 → rubric 1–5 as 1 + 4·x/100 (reproduces MAE 0.631, bias −0.607; ρ 0.751, p 0.0031 on the original scale). ρ CI: 10,000 item-level bootstrap resamples, numpy default_rng seed 2710 → 0.34–0.91 (pilot_2710/pilot_speaking_rho.py).
