# Manifest of this repository: SHA-256, size and record count of every published file (paths as published).
# Files named *.orig.json are original records; the same name without .orig is the corrected derived record (see README).
# usage: python build_repo_manifest.py  ->  MANIFEST.json
import hashlib, json, os
out = []
for root, _, files in os.walk("."):
    if ".git" in root.split(os.sep): continue
    for f in sorted(files):
        p = os.path.join(root, f)[2:].replace("\\", "/")
        if p in ("MANIFEST.json",): continue
        b = open(p, "rb").read(); n = None
        if p.endswith(".jsonl"): n = sum(1 for l in b.splitlines() if l.strip())
        elif p.endswith(".json"):
            try: j = json.loads(b); n = len(j) if isinstance(j, list) else None
            except Exception: pass
        out.append({"path": p, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b), "records": n, "original": p.endswith(".orig.json")})
json.dump(sorted(out, key=lambda r: r["path"]), open("MANIFEST.json", "w", encoding="utf-8"), indent=1); print(len(out), "files")
