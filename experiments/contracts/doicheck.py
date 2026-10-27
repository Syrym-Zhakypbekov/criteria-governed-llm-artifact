import re, sys, json, urllib.request, concurrent.futures as cf
txt = open(sys.argv[1], encoding="utf-8").read().split("## References")[1].split("## Appendix")[0]
refs = re.findall(r"^(\d+)\. (.*)$", txt, re.M)
def chk(r):
    n, line = r; m = re.search(r"doi:(\S+)", line)
    if not m: return n, "NO-DOI", line[:90]
    doi = m.group(1).rstrip(".")
    try:
        req = urllib.request.Request("https://api.crossref.org/works/" + doi, headers={"User-Agent": "doicheck/1.0 (mailto:research@example.org)"})
        d = json.load(urllib.request.urlopen(req, timeout=25))["message"]
        t = (d.get("title") or [""])[0]; a = (d.get("author") or [{}])[0].get("family", "")
        y = (d.get("issued", {}).get("date-parts") or [[None]])[0][0]
        return n, "OK", f"{doi} | {a} {y} | {t[:100]}"
    except Exception as e:
        try:
            urllib.request.urlopen(urllib.request.Request("https://doi.org/" + doi, method="HEAD"), timeout=25); return n, "DOI.ORG-OK", doi
        except Exception as e2:
            return n, "FAIL", f"{doi} {e2}"
with cf.ThreadPoolExecutor(8) as ex:
    for n, s, info in sorted(ex.map(chk, refs), key=lambda x: int(x[0])): print(n, s, info)
