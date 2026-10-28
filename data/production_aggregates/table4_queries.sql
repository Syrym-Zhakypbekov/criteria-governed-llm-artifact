-- Aggregate queries behind Table 4 and Section 6.1 (run read-only on the production database, schema queue).
-- They return counts only; no personal data is selected or exported. Executed 28 October 2026.

-- Identity documents of enrolled applicants (23-25 Aug 2026): verdicts and agreement
SELECT verdict, read_by, count(*) n,
       count(*) FILTER (WHERE iin_match) iin_agree, count(*) FILTER (WHERE iin_match IS FALSE) iin_disagree,
       count(*) FILTER (WHERE fio_udv_match) name_agree, count(*) FILTER (WHERE fio_udv_match IS FALSE) name_disagree
FROM queue.udv_check GROUP BY 1,2 ORDER BY 3 DESC;
-- File layer (input quality)
SELECT l3_kind, l3_quality, count(*) FROM queue.udv_recon GROUP BY 1,2 ORDER BY 3 DESC;
-- Staff records corrected after a flag, escalation to a stronger model
SELECT count(*) FILTER (WHERE EXISTS (SELECT 1 FROM unnest(flags) f WHERE f LIKE 'изменение в%')) corrected_records,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM unnest(flags) f WHERE f LIKE 'перечитано сильной%')) escalated_reads
FROM queue.udv_check;

-- Applicant questions (contact centre) classification
SELECT topic_by, count(*) n, count(DISTINCT topic) topics FROM queue.bitrix_questions GROUP BY 1;
SELECT topic, count(*) FROM queue.bitrix_questions WHERE topic IS NOT NULL GROUP BY 1 ORDER BY 2 DESC;
SELECT match_by, count(*) FROM queue.bitrix_person_link GROUP BY 1;
SELECT count(*) sent, count(*) FILTER (WHERE ok) delivered FROM queue.bitrix_send_log;

-- Admission question answering
SELECT count(*) chunks, count(DISTINCT law) documents FROM queue.law_chunks;
SELECT answered_by, lang, count(*) FROM queue.faq_search_log WHERE channel <> 'smoke' GROUP BY 1,2 ORDER BY 3 DESC;

-- Supplier-contract ledger
SELECT caller, state, criteria_version, count(*), sum(fields_total), sum(fields_changed)
FROM queue.ai_decision WHERE caller = 'jrd-extract' GROUP BY 1,2,3;

-- Thesis topics, syllabi
SELECT action, count(*) FROM queue.actions WHERE action LIKE 'thesis.%' GROUP BY 1 ORDER BY 2 DESC;
SELECT count(DISTINCT syllabus_id) syllabi, count(DISTINCT saved_by) authors, count(*) saves FROM queue.syllabus_version;
SELECT state, count(*) FROM queue.syllabus_ai_job GROUP BY 1;

-- Admission campaign scale (26 Jun-31 Aug 2026)
SELECT count(*) tickets, count(DISTINCT applicant_id) applicants, count(*) FILTER (WHERE closed_at IS NOT NULL) served,
       count(DISTINCT desk_id) desks FROM queue.tickets WHERE created_at < '2026-09-01';
SELECT status, count(*) FROM queue.salem_agreement WHERE NOT deleted GROUP BY 1;
SELECT count(*) accounts, sum(login_count) logins FROM queue.platonus_applicant_session;

-- ===== Added 28 Oct 2026 (review R24-14): exact cohorts and partitions =====
-- SUPERSEDED by the R26 block at the end (no read_by filter): first-pass acceptance vs acceptance after a change
WITH t AS (SELECT person_id, verdict,
  EXISTS (SELECT 1 FROM unnest(flags) x WHERE x LIKE 'статус изменился%') changed,
  EXISTS (SELECT 1 FROM unnest(flags) x WHERE x LIKE 'изменение в%') corrected,
  EXISTS (SELECT 1 FROM unnest(flags) x WHERE x LIKE 'изменение в деле%') corr_file,
  EXISTS (SELECT 1 FROM unnest(flags) x WHERE x LIKE 'изменение в договоре%') corr_contract
  FROM queue.udv_check)
SELECT count(*) records, count(DISTINCT person_id) persons,
  count(*) FILTER (WHERE verdict IN ('ok','скан') AND NOT changed AND NOT corrected) accepted_first_pass,
  count(*) FILTER (WHERE verdict IN ('ok','скан') AND (changed OR corrected)) accepted_after_change,
  count(*) FILTER (WHERE corrected) correction_flag_any, count(*) FILTER (WHERE corr_file) on_file,
  count(*) FILTER (WHERE corr_contract) on_contract, count(*) FILTER (WHERE corr_file AND corr_contract) on_both
FROM t;
-- SUPERSEDED by the R26 block at the end (old rule C = accepting OR changed): classification of the 175-record set
WITH t AS (SELECT verdict, udv_nature, array_to_string(flags,' | ') f,
  EXISTS (SELECT 1 FROM unnest(flags) x WHERE x LIKE 'статус изменился%') changed,
  EXISTS (SELECT 1 FROM unnest(flags) x WHERE x LIKE 'изменение в%') corrected FROM queue.udv_check)
SELECT CASE WHEN corrected THEN 'A correction flag on file/contract'
            WHEN f LIKE '%НЕ удостоверение%' THEN 'B not an identity document'
            WHEN verdict IN ('ok','скан') OR changed THEN 'C resolved on re-check'
            WHEN verdict='каз_рус_буквы' THEN 'D Kazakh-Russian letter variant, open'
            WHEN verdict='фио_договор_расхождение' THEN 'E record vs contract, open'
            WHEN udv_nature='eGov' THEN 'F mismatch on electronic document, open'
            ELSE 'G mismatch on photo or scan, open' END cls, count(*)
FROM t WHERE verdict IN ('не_сходится','каз_рус_буквы','фио_договор_расхождение') OR changed OR corrected
GROUP BY 1 ORDER BY 1;
-- Flags: rotation, stronger-model re-read
SELECT count(*) FILTER (WHERE EXISTS (SELECT 1 FROM unnest(flags) x WHERE x LIKE 'повёрнут%')) rotation_flag,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM unnest(flags) x WHERE x LIKE 'перечитано сильной%')) stronger_model_reread
FROM queue.udv_check;
-- File layer covers 2316 records (separate table)
SELECT count(*) FROM queue.udv_recon;

-- Contract ledger: changed vs filled fields among revised decisions
SELECT sum(jsonb_array_length(coalesce(diff->'changed','[]'::jsonb))) changed_values,
       sum((SELECT count(*) FROM jsonb_object_keys(CASE WHEN jsonb_typeof(diff->'filled')='object' THEN diff->'filled' ELSE '{}'::jsonb END))) filled_object_keys,
       sum(CASE WHEN jsonb_typeof(diff->'filled')='array' THEN jsonb_array_length(diff->'filled') ELSE 0 END) filled_array_items
FROM queue.ai_decision WHERE caller='jrd-extract' AND state='revised';

-- Contact centre: median first-reply minutes on first-pass classified rows
SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY reply_minutes) FROM queue.bitrix_questions WHERE topic_by='gemini';

-- Thesis translations corrected without a change of the Russian title
SELECT count(DISTINCT topic_id) FROM (SELECT topic_id,
  coalesce(before_value->>'title_kz','')<>'' AND before_value->>'title_kz'<>coalesce(after_value->>'title_kz','') kz_ch,
  coalesce(before_value->>'title_en','')<>'' AND before_value->>'title_en'<>coalesce(after_value->>'title_en','') en_ch,
  coalesce(before_value->>'title_ru','')<>coalesce(after_value->>'title_ru','') ru_ch FROM queue.thesis_topic_history) t
WHERE (kz_ch OR en_ch) AND NOT ru_ch;
SELECT count(*) topics, count(*) FILTER (WHERE coalesce(title_kz,'')<>'' AND coalesce(title_en,'')<>'') translated FROM queue.thesis_topic;
-- Discount eligibility statuses come from the evidence-folder snapshot (no database table); reported as eligibility-check statuses only.

-- SUPERSEDED by the R26 block at the end (old open-set predicate): open discrepancies vs the mirror
WITH t AS (SELECT u.person_id, u.verdict, u.udv_fio, u.fio_platonus, array_to_string(u.flags,' | ') f,
  EXISTS (SELECT 1 FROM unnest(u.flags) x WHERE x LIKE 'статус изменился%') changed,
  EXISTS (SELECT 1 FROM unnest(u.flags) x WHERE x LIKE 'изменение в%') corrected FROM queue.udv_check u),
o AS (SELECT * FROM t WHERE NOT corrected AND f NOT LIKE '%НЕ удостоверение%' AND NOT (verdict IN ('ok','скан') OR changed)
      AND verdict IN ('не_сходится','каз_рус_буквы','фио_договор_расхождение')),
n AS (SELECT o.*, upper(regexp_replace(coalesce(p.full_name,''),'\s+',' ','g')) nn, upper(regexp_replace(coalesce(o.udv_fio,''),'\s+',' ','g')) un
      FROM o LEFT JOIN queue.platonus_student p ON p.person_id=o.person_id)
SELECT CASE WHEN nn=un THEN 'record now equals model reading'
            WHEN un='' THEN 'model read no name'
            WHEN translate(nn,'ӘҒҚҢӨҰҮҺІЁ','АГКНОУУХИЕ')=translate(un,'ӘҒҚҢӨҰҮҺІЁ','АГКНОУУХИЕ') THEN 'Kazakh/Russian letters only'
            WHEN position(translate(nn,'ӘҒҚҢӨҰҮҺІЁ','АГКНОУУХИЕ') in translate(un,'ӘҒҚҢӨҰҮҺІЁ','АГКНОУУХИЕ'))=1
              OR position(translate(un,'ӘҒҚҢӨҰҮҺІЁ','АГКНОУУХИЕ') in translate(nn,'ӘҒҚҢӨҰҮҺІЁ','АГКНОУУХИЕ'))=1 THEN 'one name is a prefix (missing part)'
            ELSE 'other (classified individually)' END cls, count(*)
FROM n GROUP BY 1 ORDER BY 2 DESC;

-- ===== Added 28 Oct 2026 (review R25) =====
-- Seeded samples (deterministic: order by md5(id || 'make2026'))
-- Applicant questions, 300:
SELECT msg_id FROM queue.bitrix_questions WHERE topic IS NOT NULL ORDER BY md5(msg_id::text||'make2026') LIMIT 300;
-- Question answering, 150 (AI or law answers, smoke tests excluded):
SELECT id FROM queue.faq_search_log WHERE answered_by IN ('ai','law') AND channel<>'smoke' ORDER BY md5(id::text||'make2026') LIMIT 150;

-- Contract ledger, per-field comparison of the 7 revised decisions (12 fields)
WITH r AS (SELECT ai_output a, human_output h, diff FROM queue.ai_decision WHERE caller='jrd-extract' AND state='revised'),
f AS (SELECT unnest(ARRAY['bin','supplier','email','director','number','basis','vat','kind','from','until','items','total']) k)
SELECT f.k,
  count(*) FILTER (WHERE EXISTS (SELECT 1 FROM jsonb_array_elements(r.diff->'changed') e WHERE e->>'field'=f.k)) changed,
  count(*) FILTER (WHERE coalesce(r.a->>f.k,'')='' AND coalesce(r.h->>f.k,'')<>'') filled,
  count(*) FILTER (WHERE coalesce(r.a->>f.k,'')<>'' AND coalesce(r.a->>f.k,'')=coalesce(r.h->>f.k,'')) identical,
  count(*) FILTER (WHERE coalesce(r.a->>f.k,'')='' AND coalesce(r.h->>f.k,'')='') both_empty
FROM f CROSS JOIN r GROUP BY f.k ORDER BY f.k;

-- Syllabus translations and later edits
WITH t AS (SELECT syllabus_id, section, min(at) at FROM queue.syllabus_section_log
           WHERE note ILIKE '%Gemini%' OR note ILIKE '%аударма%' GROUP BY 1,2)
SELECT count(*) translated_sections,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM queue.syllabus_section_log l
         WHERE l.syllabus_id=t.syllabus_id AND l.section=t.section AND l.at>t.at AND l.note='автосохранение')) edited_later
FROM t;

-- Figure 2 periods (Almaty time, min/max of each workflow's records)
SELECT 'queue' w, min(created_at AT TIME ZONE 'Asia/Almaty')::date, max(created_at AT TIME ZONE 'Asia/Almaty')::date FROM queue.tickets WHERE created_at < '2026-09-01'
UNION ALL SELECT 'qa', min(created_at AT TIME ZONE 'Asia/Almaty')::date, max(created_at AT TIME ZONE 'Asia/Almaty')::date FROM queue.faq_search_log
UNION ALL SELECT 'sis_access', min(logged_in_at AT TIME ZONE 'Asia/Almaty')::date, max(logged_in_at AT TIME ZONE 'Asia/Almaty')::date FROM queue.platonus_applicant_session
UNION ALL SELECT 'e_contracts', min(created_at AT TIME ZONE 'Asia/Almaty')::date, max(created_at AT TIME ZONE 'Asia/Almaty')::date FROM queue.salem_agreement WHERE NOT deleted AND status='SIGNED'
UNION ALL SELECT 'classification', min(classified_at AT TIME ZONE 'Asia/Almaty')::date, max(classified_at AT TIME ZONE 'Asia/Almaty')::date FROM queue.bitrix_questions
UNION ALL SELECT 'id_check', min(finished_at AT TIME ZONE 'Asia/Almaty')::date, max(finished_at AT TIME ZONE 'Asia/Almaty')::date FROM queue.udv_check
UNION ALL SELECT 'syllabi', min(saved_at AT TIME ZONE 'Asia/Almaty')::date, max(saved_at AT TIME ZONE 'Asia/Almaty')::date FROM queue.syllabus_version
UNION ALL SELECT 'thesis', min(ts AT TIME ZONE 'Asia/Almaty')::date, max(ts AT TIME ZONE 'Asia/Almaty')::date FROM queue.actions WHERE action LIKE 'thesis.%'
UNION ALL SELECT 'card_reads', min(ts AT TIME ZONE 'Asia/Almaty')::date, max(ts AT TIME ZONE 'Asia/Almaty')::date FROM queue.llm_call WHERE caller='qs.card'
UNION ALL SELECT 'supplier_extraction', min(ts AT TIME ZONE 'Asia/Almaty')::date, max(ts AT TIME ZONE 'Asia/Almaty')::date FROM queue.llm_call WHERE caller='jrd-extract'
UNION ALL SELECT 'ledger', min(created_at AT TIME ZONE 'Asia/Almaty')::date, max(created_at AT TIME ZONE 'Asia/Almaty')::date FROM queue.ai_decision WHERE caller='jrd-extract';
-- Discount evidence period: evidence-folder audit log (8-20 Oct 2026), not a database table.

-- ===== R26 (28 Oct 2026): queries that reproduce the numbers in the manuscript =====
-- Expected: records 2416, persons 2415; model-read accepting 2294; without status-change/correction flag 2203; with a flag 91.
WITH t AS (SELECT person_id, read_by, verdict,
  EXISTS (SELECT 1 FROM unnest(flags) x WHERE x LIKE 'статус изменился%') changed,
  EXISTS (SELECT 1 FROM unnest(flags) x WHERE x LIKE 'изменение в%') corrected FROM queue.udv_check)
SELECT count(*) records, count(DISTINCT person_id) persons,
  count(*) FILTER (WHERE read_by='gemini' AND verdict IN ('ok','скан')) model_read_accepting,
  count(*) FILTER (WHERE read_by='gemini' AND verdict IN ('ok','скан') AND NOT changed AND NOT corrected) without_flag,
  count(*) FILTER (WHERE read_by='gemini' AND verdict IN ('ok','скан') AND (changed OR corrected)) with_flag
FROM t;
-- Expected partition of the 175-record discrepancy set: A 54 · B 3 · C 36 · open 82,
-- and open follow-up: now equals model 26 · KZ/RU letters only 28 · missing part 9 · model read no name 5 · other 14.
WITH t AS (SELECT u.person_id, u.verdict, u.udv_fio, array_to_string(u.flags,' | ') f,
  EXISTS (SELECT 1 FROM unnest(u.flags) x WHERE x LIKE 'статус изменился%') changed,
  EXISTS (SELECT 1 FROM unnest(u.flags) x WHERE x LIKE 'изменение в%') corrected FROM queue.udv_check u),
d AS (SELECT * FROM t WHERE verdict IN ('не_сходится','каз_рус_буквы','фио_договор_расхождение') OR changed OR corrected),
c AS (SELECT d.*, CASE WHEN corrected THEN 'A correction flag on file/contract'
                       WHEN f LIKE '%НЕ удостоверение%' THEN 'B not an identity document'
                       WHEN verdict IN ('ok','скан') THEN 'C accepting final verdict'
                       ELSE 'open' END cls FROM d),
n AS (SELECT c.*, upper(regexp_replace(coalesce(p.full_name,''),'\s+',' ','g')) nn,
             upper(regexp_replace(coalesce(c.udv_fio,''),'\s+',' ','g')) un
      FROM c LEFT JOIN queue.platonus_student p ON p.person_id=c.person_id)
SELECT cls,
  CASE WHEN cls<>'open' THEN ''
       WHEN nn=un AND un<>'' THEN 'record now equals model reading'
       WHEN un='' THEN 'model read no name'
       WHEN translate(nn,'ӘҒҚҢӨҰҮҺІЁ','АГКНОУУХИЕ')=translate(un,'ӘҒҚҢӨҰҮҺІЁ','АГКНОУУХИЕ') THEN 'Kazakh/Russian letters only'
       WHEN position(translate(nn,'ӘҒҚҢӨҰҮҺІЁ','АГКНОУУХИЕ') in translate(un,'ӘҒҚҢӨҰҮҺІЁ','АГКНОУУХИЕ'))=1
         OR position(translate(un,'ӘҒҚҢӨҰҮҺІЁ','АГКНОУУХИЕ') in translate(nn,'ӘҒҚҢӨҰҮҺІЁ','АГКНОУУХИЕ'))=1 THEN 'one name is a prefix'
       ELSE 'other (classified individually: 6 staff typos, 6 patronymic form, 2 model misreads)' END sub,
  count(*)
FROM n GROUP BY 1,2 ORDER BY 1,2;
-- Snapshot note: these tables are live; the reported values are from the run of 28 October 2026 and the
-- student-information-system mirror synchronised on 6 September 2026 (queue.platonus_student.synced_at).
