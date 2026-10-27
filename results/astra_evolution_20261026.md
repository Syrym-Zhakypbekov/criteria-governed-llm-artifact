# Astra evolution and evidence — aggregates for the MAKE paper (P3)

Generated 26.10.2026 22:25 Almaty by `0000_system/tools/astra_evolution_metrics.py` — do not edit by hand, re-run the script. Aggregates only, no personal data.

## 1. Build history (git, origin/main)
Source: `git log` / `git ls-tree` in `C:\dev\iitu-queue`.

- First commit 2026-06-24 `ab4367f3` «feat: scaffold iitu-queue (Next.js+pg+vitest) + DB layer (schema queue, migratio»; last 2026-10-26 `44d3f6fe`.
- **2,905 commits in 125 days** (102 active days): mean 28.5 per active day, median 17, max 157 (2026-07-05).
- Per month: 2026-06 313 · 2026-07 1,145 · 2026-08 541 · 2026-09 388 · 2026-10 518.
- Human authors: Syrym Zhakypbekov 2,904, server-wip 1.
- **Commits with an AI co-author trailer: 2,103 (72%)** — Claude Fable 5 893 · Claude Opus 4.8 472 · Claude Opus 5.5 369 · Claude Fable 5.1 238 · Claude Opus 4.6 54 · Claude Opus 5 49 · Claude Sonnet 5.5 24 · Claude Sonnet 5 4.
- Commits between 00:00 and 06:00: 341.

| Snapshot | commit | pages | API routes | DB migrations | test files | TS/TSX files |
|---|---|---|---|---|---|---|
| 2026-06-30 | `6be179dd` | 30 | 84 | 45 | 15 | 186 |
| 2026-07-15 | `b5c69ed6` | 80 | 244 | 187 | 36 | 523 |
| 2026-07-31 | `761c207b` | 100 | 290 | 224 | 50 | 652 |
| 2026-08-15 | `d27ba634` | 100 | 310 | 256 | 53 | 692 |
| 2026-08-31 | `c941e220` | 107 | 342 | 297 | 60 | 797 |
| 2026-09-15 | `d4cdfab7` | 153 | 438 | 379 | 104 | 1127 |
| 2026-09-30 | `fd7a5579` | 164 | 457 | 404 | 120 | 1199 |
| 2026-10-15 | `b71047b7` | 219 | 593 | 469 | 321 | 1928 |
| 2026-10-26 | `44d3f6fe` | 244 | 645 | 496 | 910 | 2788 |

Milestones (first commit whose subject mentions it):
- 2026-06-24 — RBAC guard (22 commits; first `d52a8339`)
- 2026-06-25 — Platonus integration (386 commits; first `15f63d75`)
- 2026-06-25 — Gemini (LLM) calls (50 commits; first `4c4ca8b5`)
- 2026-07-03 — edoc integration (25 commits; first `eb5f2abf`)
- 2026-07-05 — OCR of documents (49 commits; first `1e12a122`)
- 2026-08-06 — Salem Office integration (133 commits; first `b2327b6a`)
- 2026-08-21 — Bitrix24 integration (70 commits; first `56ae04ef`)
- 2026-09-03 — Syllabus module (R-57) (74 commits; first `50f7d1b3`)
- 2026-09-10 — AI check of written work (15 commits; first `bd4eec05`)
- 2026-09-25 — QS contacts module (39 commits; first `2bcd8823`)
- 2026-10-10 — Move to astra.iitu.edu.kz (3 commits; first `3c4ee392`)
- 2026-10-24 — Multi-zone modular monolith (18 commits; first `a1811316`)
- 2026-10-26 — Placement Test zone (16 commits; first `b9d9d713`)

## 2. Architecture (deploy/zones.json, origin/main)
- 10 services behind one Caddy (Next.js multi-zones):
  - `/shell` :3402 — Оболочка (корень): вход, меню, профиль, админка
  - `placement` :3410 — Express Placement Test: английский A1–C1, ИИ-оценка Speaking, две камеры
  - `legal` :3420 — Юридический отдел
  - `kafedra` :3430 — Кафедра
  - `student` :3440 — Студент
  - `admission` :3450 — Приёмная комиссия
  - `management` :3460 — Руководство
  - `lab` :3470 — Лаборатория (эксперименты, только владелец)
  - `salem` :3480 — Salem HR: всё о Salem в Astra (карта, задачи, документы, эксперименты)
  - `legacy` :3490 — Архив и игры
- Files per zone app: admission 631 · kafedra 514 · management 211 · student 188 · lab 138 · placement 108 · legacy 99 · legal 74 · salem 58.

## 3. Delivery with automatic gates (server ~/deploy-logs, via `ssh iitu`)
| Month | deploys | completed | stopped by a gate | rollback messages | zone-only fast lane | timed | median s | p10 s |
|---|---|---|---|---|---|---|---|---|
| 202608 | 343 | 326 | 11 | 1 | 0 | 0 | NA | NA |
| 202609 | 293 | 264 | 21 | 1 | 0 | 0 | NA | NA |
| 202610 | 389 | 301 | 63 | 4 | 32 | 32 | 17 | 12 |

Total: 1,025 deploys, 891 completed, **95 stopped before production**, 32 zone-only deploys. A log counts as 'stopped' when it has no «DEPLOY DONE» but a test/health failure marker.

## 4. Operations and AI calls (warp_iitu, aggregates only)
- Row counts: presence_log 122,357 · actions 65,624 · platonus_applicant 17,711 · tickets 14,727 · rector_report 8,595 · users 7,487 · salem_agreement 2,002 · thesis_member 437 · thesis_topic 230 · nav_items 171 · feedback 82 · syllabus 63 · helpdesk_ticket 53 · travel_job 28 · ipp_plan 26 · written_submission 5 · pt_session 3.
- **AI calls (queue.llm_call): 2,029 calls, 55 callers, 6 models, $3.77 total ($0.00186 per call), 102 failed; 2026-09-04 → 2026-10-26.**
- Largest callers: lab.vision 759 ($0.48) · qs.card 432 ($0.31) · thesis.translate 109 ($0.03) · jrd-extract 75 ($0.84) · (no caller) 69 ($0.13) · placement.vision 69 ($0.05) · written.experiment 40 ($0.12) · superapp.ai 36 ($0.13) · syllabus.translate.control 29 ($0.01) · syllabus.translate.info 29 ($0.01) · syllabus.translate.goals 25 ($0.02) · syllabus.translate.descr 23 ($0.01).
- Failure causes (top): «IP address restriction» 99 · «status 503» 3.
