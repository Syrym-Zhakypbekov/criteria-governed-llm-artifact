# EXP-ELLIPSE: public replication of the EXP001 writing-assessment protocol (26.10.2026) on the ELLIPSE corpus (CC BY-NC-SA 4.0,
# Crossley et al. 2023, doi:10.1075/ijlcr.22026.cro). Builds jobs.json: N essays stratified by human Overall,
# configurations A (holistic) / B (basic analytic rubric) / C (detailed analytic rubric with official descriptors), R repeats.
# usage: python build_jobs.py train.csv jobs.json [N=120] [R=3]
import csv, json, random, sys
SRC, OUT = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 120
R = int(sys.argv[4]) if len(sys.argv) > 4 else 3
csv.field_size_limit(10**8)
rows = list(csv.DictReader(open(SRC, encoding="utf-8", newline="")))
CRIT = ["Cohesion", "Syntax", "Vocabulary", "Phraseology", "Grammar", "Conventions"]

# stratified sample by human Overall (rounded to integer band)
rnd = random.Random(42)
bands = {}
for r in rows:
    bands.setdefault(round(float(r["Overall"])), []).append(r)
per = {b: max(1, round(N * len(v) / len(rows))) for b, v in bands.items()}
while sum(per.values()) > N: per[max(per, key=per.get)] -= 1
while sum(per.values()) < N: per[max(per, key=lambda b: len(bands[b]))] += 1
sample = []
for b in sorted(bands):
    sample += rnd.sample(bands[b], per[b])

HOLISTIC = {
 5: "Native-like facility in the use of language with syntactic variety, appropriate word choice and phrases; well-controlled text organization; precise use of grammar and conventions; rare language inaccuracies that do not impede communication.",
 4: "Facility in the use of language with syntactic variety and range of words and phrases; controlled organization; accuracy in grammar and conventions; occasional language inaccuracies that rarely impede communication.",
 3: "Facility limited to the use of common structures and generic vocabulary; organization generally controlled although connection sometimes absent or unsuccessful; errors in grammar and syntax and usage. Communication is impeded by language inaccuracies in some cases.",
 2: "Inconsistent facility in sentence formation, word choice, and mechanics; organization partially developed but may be missing or unsuccessful. Communication impeded in many instances by language inaccuracies.",
 1: "A limited range of familiar words or phrases loosely strung together; frequent errors in grammar (including syntax) and usage. Communication impeded in most cases by language inaccuracies.",
}
BASIC = {
 "Cohesion": "organisation and use of cohesive devices to connect ideas",
 "Syntax": "range and accuracy of sentence structures",
 "Vocabulary": "range and precision of vocabulary",
 "Phraseology": "range and accuracy of multi-word units (idioms, collocations, lexical bundles)",
 "Grammar": "accuracy of grammar and usage",
 "Conventions": "spelling, capitalization and punctuation",
}
DETAILED = {
 "Cohesion": {5: "Text organization consistently well controlled using a variety of effective linguistic features such as reference and transitional words and phrases to connect ideas across sentences and paragraphs; appropriate overlap of ideas.",
   4: "Organization generally well controlled; a range of cohesive devices used appropriately such as reference and transitional words and phrases to connect ideas; generally appropriate overlap of ideas.",
   3: "Organization generally controlled; cohesive devices used but limited in type; some repetitive, mechanical, or faulty use of cohesion within and/or between sentences and paragraphs.",
   2: "Organization only partially developed with a lack of logical sequencing of ideas; some basic cohesive devices used but with inaccuracy or repetition.",
   1: "No clear control of organization; cohesive devices not present or unsuccessfully used; presentation of ideas unclear."},
 "Syntax": {5: "Flexible and effective use of a full range of syntactic structures including simple, compound, and complex sentences; there may be rare minor and negligible errors in sentence formation.",
   4: "Appropriate use of a variety of syntactic structures, such as simple, compound, and complex sentences; occasional errors or inappropriateness in sentence formation.",
   3: "Simple, compound, and complex syntactic structures present although the range may be limited; some apparent errors in sentence formation, especially in more complex sentences.",
   2: "Some sentence variation used; many sentence structure problems.",
   1: "Pervasive and basic errors in sentence structure and word order that cause confusion; basic sentence errors common."},
 "Vocabulary": {5: "Wide range of vocabulary flexibly and effectively used to convey precise meanings; skillful use of topic-related terms and less common words; rare negligible inaccuracies in word use.",
   4: "Sufficient range of vocabulary to allow flexibility and precision; appropriate use of topic-related terms and less common lexical items.",
   3: "Minimally adequate range of vocabulary for the topic; no precise use of subtle word meanings; topic related terms only used occasionally; attempts to use less common vocabulary but with some inaccuracy.",
   2: "Narrow range of vocabulary to convey basic and elementary meaning; topic related terms used inappropriately; errors in word formation and word choice that may distort meanings.",
   1: "Limited vocabulary often inappropriately used; limited control of word choice and word forms; little attempt to use topic-related terms."},
 "Phraseology": {5: "Flexible and effective use of a variety of phrases, such as idioms, collocations, and lexical bundles, to convey precise and subtle meanings; rare minor inaccuracies that are negligible.",
   4: "Appropriate use of a variety of phrases, such as idioms, collocations, and lexical bundles; occasional inaccuracies and colloquialisms.",
   3: "Evident use of phrases such as idioms, collocations, and lexical bundles but without much variety; some noticeable repetitions and misuses.",
   2: "Narrow range of phrases, such as collocations and lexical bundles, used to convey basic and elementary meaning; many repetitions and/or misuses of phrases.",
   1: "Memorized chunks of language, or simple phrasal patterns predominate; many repetitions and misuses of phrases."},
 "Grammar": {5: "Command of grammar and usage with few or no errors.", 4: "Minimal errors in grammar and usage.", 3: "Some errors in grammar and usage.",
   2: "Many errors in grammar and usage.", 1: "Errors in grammar and usage throughout."},
 "Conventions": {5: "Consistent use of appropriate conventions to convey meaning; spelling, capitalization, and punctuation errors nonexistent or negligible.",
   4: "Generally consistent use of appropriate conventions to convey meaning; spelling, capitalization, and punctuation errors few and not distracting.",
   3: "Developing use of conventions to convey meaning; errors in spelling, capitalization, and punctuation that are sometimes distracting.",
   2: "Variable use of conventions; spelling, capitalization, and punctuation errors frequent and distracting.",
   1: "Minimal use of conventions; spelling, capitalization, and punctuation errors throughout."},
}
HEAD = ("You are an experienced rater of English writing by English language learners in grades 8-12. "
        "Score the essay below. Scores range from 1.0 to 5.0 in steps of 0.5. Return ONLY JSON.\n\n")

def prompt(cfg, text):
    if cfg == "A":
        rub = "\n".join(f"{k}: {v}" for k, v in sorted(HOLISTIC.items(), reverse=True))
        return HEAD + f"HOLISTIC RUBRIC (overall English proficiency):\n{rub}\n\nReturn: {{\"overall\": <1.0-5.0>}}\n\nESSAY:\n{text}"
    if cfg == "B":
        rub = "\n".join(f"- {c}: {d}" for c, d in BASIC.items())
        return HEAD + (f"Score each criterion from 1.0 (very weak) to 5.0 (native-like), then an overall proficiency score.\nCRITERIA:\n{rub}\n\n"
                       "Return: {\"cohesion\":x,\"syntax\":x,\"vocabulary\":x,\"phraseology\":x,\"grammar\":x,\"conventions\":x,\"overall\":x}\n\nESSAY:\n" + text)
    rub = "\n\n".join(c + ":\n" + "\n".join(f"  {k}: {v}" for k, v in sorted(DETAILED[c].items(), reverse=True)) for c in CRIT)
    hol = "\n".join(f"  {k}: {v}" for k, v in sorted(HOLISTIC.items(), reverse=True))
    return HEAD + (f"ANALYTIC RUBRIC (level descriptors 1-5; use .5 between levels):\n{rub}\n\nOVERALL:\n{hol}\n\n"
                   "Return: {\"cohesion\":x,\"syntax\":x,\"vocabulary\":x,\"phraseology\":x,\"grammar\":x,\"conventions\":x,\"overall\":x}\n\nESSAY:\n" + text)

jobs = []
for r in sample:
    for cfg in "ABC":
        for rep in range(1, R + 1):
            jobs.append({"id": r["text_id_kaggle"], "cfg": cfg, "rep": rep, "prompt": prompt(cfg, r["full_text"])})
order = list(range(len(jobs))); rnd.shuffle(order)  # randomised call order (EXP001 §4)
gold = {r["text_id_kaggle"]: {k: float(r[k]) for k in ["Overall"] + CRIT} | {"words": int(r["num_words"])} for r in sample}
json.dump({"jobs": [jobs[i] for i in order], "gold": gold}, open(OUT, "w", encoding="utf-8"))
print("essays", len(sample), "jobs", len(jobs), "per band", dict(sorted(per.items())))
