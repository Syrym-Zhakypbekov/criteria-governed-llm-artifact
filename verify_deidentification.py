"""Check that the archived source files differ from the platform commit only in code comments.

Why this exists (MAKE revision, November 2026). Appendix A of the article gives SHA-256 prefixes of three source files at
platform commit 1114a138. Before publication, two of them (src/jrd-extract.ts, src/card-ocr.ts) were de-identified:
colleagues' names inside code comments were replaced by their roles. No executable line and no prompt text was changed.
The full-file hashes therefore differ from Appendix A, while src/decision-ledger.ts (not edited) matches it.

This script recomputes, for each file:
  full     = SHA-256 of the file (CR characters removed, i.e. LF line endings);
  stripped = SHA-256 of the same text after removing every line whose first non-blank characters are //, * or /*
             (comment-only lines; the same rule is applied to the platform originals, see DEIDENTIFICATION.md).
and compares them with the values recorded from commit 1114a138. Expected result: every «stripped» value matches,
the «full» value matches only for src/decision-ledger.ts.

Usage: python verify_deidentification.py        (exit 0 = all checks as expected, 1 = a difference)
"""
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMENT_LINE = re.compile(r"^\s*(//|\*|/\*)")

# Values computed from `git show 1114a138:<platform path>` of the private platform repository.
RECORDED = {
    "src/jrd-extract.ts": {
        "platform_path": "apps/legal/lib/jrd-extract.ts",
        "full": "1c07b6322ce288e89fc6043305642a2d125a98f2fa81b4b2d1a0068db22aaac5",
        "stripped": "7b5d748973374d2ad39d23065380a6700c638e7383cb68252cc76db2f7965ede",
        "edited": True,
    },
    "src/card-ocr.ts": {
        "platform_path": "apps/kafedra/lib/qs/card-ocr.ts",
        "full": "05fe1acd07345f5879728efee4150ed855b613e9ab052b11d9af57c1f53dbdb1",
        "stripped": "c94339cc796abc665607cb0778836f9705755ffe0d63904ede3bac8a6758fa76",
        "edited": True,
    },
    "src/decision-ledger.ts": {
        "platform_path": "lib/decision-ledger.ts",
        "full": "5f9b2d699dd77cf6a51be9dbd5a6f93d94ca8afd9228b4af16838b6f9dca57b8",
        "stripped": "86349227c533d0652d3db24a38e1044e21b7d93546265ce3700328e9f2b337e0",
        "edited": False,
    },
}


def digests(text: str) -> tuple[str, str]:
    text = text.replace("\r", "")
    stripped = "".join(line for line in text.splitlines(keepends=True) if not COMMENT_LINE.match(line))
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), hashlib.sha256(stripped.encode("utf-8")).hexdigest()


def main() -> int:
    ok = True
    for rel, rec in RECORDED.items():
        full, stripped = digests((ROOT / rel).read_text(encoding="utf-8"))
        full_match = full == rec["full"]
        stripped_match = stripped == rec["stripped"]
        expected_full_match = not rec["edited"]
        good = stripped_match and full_match == expected_full_match
        ok &= good
        print(f"{'OK ' if good else 'BAD'} {rel}  (platform {rec['platform_path']} @1114a138)")
        print(f"     full     {full[:12]}  recorded {rec['full'][:12]}  {'same' if full_match else 'differs (comments de-identified)' if rec['edited'] else 'DIFFERS'}")
        print(f"     stripped {stripped[:12]}  recorded {rec['stripped'][:12]}  {'same' if stripped_match else 'DIFFERS'}")
    print("ALL AS EXPECTED: code identical to commit 1114a138; only comment lines differ" if ok else "DIFFERENCE FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
