# Execution record of the topic annotation and answer grading

| Item | Topic annotation (n = 300) | Answer grading (n = 150) |
|---|---|---|
| Model | Claude Opus 5.5 (Anthropic) | Claude Opus 5.5 (Anthropic) |
| Interface | Claude Code sub-agent in the authors' session | Claude Code sub-agent in the authors' session |
| Date | 28 October 2026 (Asia/Almaty) | 28 October 2026 (Asia/Almaty) |
| Decoding settings | not exposed by Claude Code (temperature, top-p unknown) | not exposed by Claude Code |
| Batching | 4 batches of ~75 questions, each written to a file before the next | instructed batches of ~25 answers, written incrementally |
| Passes | one pass; no relabelling after the production labels were joined | one initial grading pass; one post-review adjudication by the authors on 28 October 2026 changed item 1611 from partly correct to wrong under the original rubric; no other grades changed |
| Malformed output | none occurred; every row has exactly one label from the closed list | none occurred; every row has a grade |
| Source index | — | `queue.law_chunks` as on 28 October 2026 (60 documents, 4926 passages); read-only full-text queries |
| Document versions | — | R-41 «Правила приёма в бакалавриат», ред. 9 (approved); the applicant guide's version is not recorded in the index |
| Cohort snapshot | live table on 28 Oct 2026; seeded order md5(msg_id ‖ 'make2026') | live table on 28 Oct 2026; seeded order md5(id ‖ 'make2026') |

Adjudication note (28 October 2026, after review): the grader's output contained one item graded «partly» with hallucination = yes (a cited-provision answer, id 1611). Under the verbatim instruction below, an invented fact makes an answer «wrong», so this item was regraded to «wrong». No other item was changed. Final totals: correct 79, partly 36, wrong 3, unanswerable 32.

## Instruction given to the topic annotator (verbatim)

> You are an independent annotator for a research study. Task: BLIND topic labelling of 300 applicant questions sent to a university admission contact centre (Kazakhstan, Russian/Kazakh text).
> Input: bitrix_sample300.csv (columns msg_id, question, ai_topic, ai_subtopic, topic_by, label_A, label_B). You MUST NOT look at ai_topic, ai_subtopic or topic_by before you have written your own label for every row — read only msg_id and question. Label each question with exactly one topic from this closed list (copy the string exactly): Прочее / Нецелевые обращения; Гранты, скидки и льготы; Специальности и образовательные программы; Необходимые документы и подача заявления; Вступительные экзамены (ЕНТ/творческий); Стоимость обучения и оплата; Английский язык и IELTS; Поступление после колледжа и перевод; Статус заявки, договор и зачисление; Контакты, локация и график работы; Формат и организация учебного процесса; Общежитие и проживание; Сроки приёма и ключевые даты; Магистратура и докторантура; Военная кафедра; Иностранным гражданам.
> Rules: choose the main intent; greetings, thanks, spam, unclear or empty messages → «Прочее / Нецелевые обращения». Label in batches of ~50 by reading the text yourself (do not call any external API or model). Write results incrementally with columns msg_id, claude_topic, confidence (high/medium/low), note. Only AFTER all 300 are written: join with ai_topic and compute raw agreement, Cohen's kappa, per-topic agreement counts, and a confusion list of disagreements.

## Instruction given to the answer grader (verbatim, paths shortened)

> You are an independent grader for a research study. Task: grade 150 answers produced by a university admission question-answering service (Gemini RAG over legal and institutional documents, or a direct cited provision) for correctness against the source documents.
> Sources: the retrieval index is the table queue.law_chunks (columns id, doc_id, law, kind, num, chapter, breadcrumb, body, cite_label, url, tsv). Query it read-only (SELECT only, small LIMIT; full-text search or the cited provision).
> For each row decide: grade: correct (answer consistent with the sources and answers the question) / partly (incomplete, partly outdated or vague but not misleading) / wrong (contradicts sources, invents a fact, wrong number/date/rule) / unanswerable (question outside the documents; then judge whether the service correctly declined or redirected); citation_valid: yes / no / none; hallucination: yes if the answer states a specific fact (number, date, rule, contact) not supported by any source you found.
> Do not call any external API or model. Work in batches of ~25, writing incrementally (id, answered_by, lang, grade, citation_valid, hallucination, evidence_cite_label, note — short, no personal data). Finally compute counts and percentages by grade overall, by answered_by and by language; citation validity; hallucination rate with Wilson 95% CI.

Instruction hashes: see `sha256sum EXECUTION_RECORD.md` in the repository manifest; the instructions above are the complete text used, apart from local file paths.
