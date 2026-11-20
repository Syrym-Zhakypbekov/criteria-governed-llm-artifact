"""Independent check of the planted truth of the synthetic contract sets (MAKE revision, R2.7, November 2026).

The recount (recount_headlines.py) trusts the defect labels stored with each document. This script checks those labels
themselves: it re-derives every document's defect set from the SOURCE TEXT alone, with simple rules written for the
revision and independent of the generator code and of any model output, and compares the result with the stored labels.

Rules (applied to the source text of each document):
  bin_*        the digits after «БИН» / «BIN»: none → bin_missing, 11 → bin_short, 13 → bin_long, 12 → fine
  no_items     no item row (a row with a line number and a name)
  no_price     an item row whose price cell is empty or a dash
  vat_no_rate  VAT is mentioned but no percentage rate is given
  third_party  the contract is declared three-party but no e-mail of the third party is given
  addendum_nobase  an additional agreement whose base-contract number and date are not given
Development note (kept for transparency): the held-out-2 set matched on the first run; the development and held-out-1
sets first failed only because the table parser did not read their layouts (semicolon and tab tables, and a longer
«БИН/ИИН поставщика» label). Only the parsing was widened; no rule about a defect was changed after seeing a mismatch.
Usage: python experiments/verification/planted_truth_check.py   (exit 0 = every derived set equals the stored labels)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETS = {"development + held-out 1": "experiments/ablation/frozen_gemini-3.8-flash.json",
        "held-out 2 (confirmatory)": "experiments/ablation/frozen_h2_gemini-3.8-flash.json"}

DASH = {"", "-", "—", "–", "нет", "n/a"}


def derive(text: str) -> set[str]:
    found = set()
    m = re.search(r"(?:БИН|BIN)[^\d\n]{0,30}([\d \xa0]{5,20})", text)
    digits = re.sub(r"\D", "", m.group(1)) if m else ""
    if not digits:
        found.add("bin_missing")
    elif len(digits) == 11:
        found.add("bin_short")
    elif len(digits) == 13:
        found.add("bin_long")
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in re.split(r"[|\t;]", line)]  # the three sets use «;», tab and «|» tables
        if len(cells) < 4 or re.search(r"наименование", line, re.I):
            continue  # not a table row, or the header row
        name = cells[1] if re.fullmatch(r"\d{1,3}", cells[0]) else cells[0]  # optional leading line number
        if re.search(r"[A-Za-zА-Яа-яЁё]", name):
            rows.append(cells)
    if not rows:
        found.add("no_items")
    elif any(c[-1].lower() in DASH or not re.search(r"\d", c[-1]) for c in rows):
        found.add("no_price")
    low = text.lower()
    if re.search(r"ндс|налог[а-я]* на добавленную|vat", low) and not re.search(r"(ндс|vat)[^\n%]{0,40}\d+\s*%|\d+\s*%[^\n]{0,40}(ндс|налог)", low):
        found.add("vat_no_rate")
    if re.search(r"тр[её]хсторонн|третья сторона|сторона 3|third party", low):
        tp = re.search(r"(тр[её]хсторонн|третья сторона|сторона 3|third party)[^\n]*", low).group(0)
        if "@" not in tp:
            found.add("third_party")
    if re.search(r"дополнительн[а-я]* соглашени|addendum", low):
        ad = re.search(r"(дополнительн[а-я]* соглашени|addendum)[^\n]*", low).group(0)
        if not re.search(r"№\s*\S+\s+от\s+\d", ad):
            found.add("addendum_nobase")
    return found


def main():
    bad = 0
    for name, rel in SETS.items():
        recs = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        ok = 0
        for r in recs:
            got, want = derive(r["text"]), set(r["defects"])
            if got == want:
                ok += 1
            else:
                bad += 1
                print(f"MISMATCH {name} {r['id']}: derived {sorted(got)} vs stored {sorted(want)}")
        print(f"{name}: {ok}/{len(recs)} documents — derived defect set equals the stored label")
    print("ALL PLANTED LABELS CONFIRMED FROM SOURCE TEXT" if not bad else f"{bad} MISMATCH(ES)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
