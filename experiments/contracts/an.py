import json,collections,sys
r=json.load(open(sys.argv[1],encoding="utf-8"))
by=collections.defaultdict(list)
for x in r: by[x["defect"]].append(x)
print("cases",len(r),"errors",sum(1 for x in r if "error" in x))
for d,xs in by.items():
  ok=[x for x in xs if "error" not in x]
  if d=="clean": det=sum(1 for x in ok if not x["veto"] and not x["low"]); lab="clean_pass"
  else: det=sum(1 for x in ok if (x["expectVeto"] and x["veto"] and x["vetoReason"]==x["expectVeto"]) or (x["expectLow"] and x["expectLow"] in x["low"])); lab="caught"
  esc=sum(1 for x in ok if x["state"]!="provisional")
  ext=sum(1 for x in ok if x["binOk"] and x["itemsOk"] and x["totalOk"])
  print(f"{d:16s} n={len(xs)} {lab}={det}/{len(ok)} escalated_or_vetoed={esc} extraction_exact={ext}/{len(ok)} mean_ms={sum(x.get('ms',0) for x in xs)//len(xs)}")
