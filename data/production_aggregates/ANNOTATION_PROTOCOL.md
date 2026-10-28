# Annotation and grading protocol (28 October 2026)

Both evaluations used Claude Opus 5.5 (Anthropic), a different model family from the production models (Gemini),
run through the authors' Claude Code session. No external API other than the annotating model was called, and
no messages were sent to applicants. Question and answer texts are not published; this folder contains only
identifiers and labels.

## Applicant questions: blind topic labelling (n = 300)
- Sample: `table4_queries.sql`, «Seeded samples», 300 classified questions ordered by md5(msg_id || 'make2026').
- Blinding: the annotator loaded only `msg_id` and `question`; the production labels (`ai_topic`, `ai_subtopic`,
  `topic_by`) were not loaded before all 300 labels were written.
- Instruction: label each question with exactly one topic from the closed list of 16 production topics; choose the
  main intent; greetings, thanks, spam, unclear or empty messages → «Прочее / Нецелевые обращения»; record a
  confidence (high / medium / low).
- Output: `topic_labels_300.csv` (msg_id, ai_topic, topic_by, claude_topic, confidence).
- Statistics: raw agreement, Cohen's κ (chance agreement from both annotators' marginal distributions),
  Wilson 95% interval.

## Question answering: grading against the indexed sources (n = 150)
- Sample: `table4_queries.sql`, «Seeded samples», 150 answers with answered_by ai or law, smoke tests excluded,
  ordered by md5(id || 'make2026').
- Sources: the retrieval index `queue.law_chunks` (60 documents, 4926 passages), queried read-only by full-text
  search or by the cited provision.
- Grades: correct (consistent with the sources and answers the question) · partly (incomplete, partly outdated or
  vague but not misleading) · wrong (contradicts the sources, invents a fact, wrong number/date/rule) ·
  unanswerable (question outside the indexed documents). Citation: valid / invalid / none. Hallucination: a specific
  fact (number, date, rule, contact) not supported by any source found.
- Adjudication (28 Oct 2026): one item graded «partly» with an unsupported fact was regraded to «wrong» under the rule above; see EXECUTION_RECORD.md.
- Conflict rule: where the admission rules R-41 and an applicant guide disagreed (minimum score for paid admission),
  answers were graded against R-41.
- Output: `qa_grades_150.csv` (id, answered_by, lang, grade, citation_valid, hallucination).

## Identity-document discrepancies (n = 175)
- Classification by mutually exclusive SQL rules (`table4_queries.sql`), then comparison of open cases with the
  student-information-system mirror synchronised on 6 September 2026. The 14 remaining cases were classified by
  comparing both spellings with the document type (electronic eGov document, scan, photograph). Individual name
  records are not published.
