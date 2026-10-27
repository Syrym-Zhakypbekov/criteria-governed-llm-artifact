import json,collections,sys
r=json.load(open(sys.argv[1],encoding="utf-8"))
expect={"no_email":("veto","email"),"no_org":("veto","organization"),"no_name":("veto","name"),"no_country":("low","country"),"no_job":("low","job_title")}
by=collections.defaultdict(list)
for x in r: by[x["defect"]].append(x)
print("cards",len(r),"errors",sum(1 for x in r if "error" in x))
fields=collections.Counter(); fieldsn=collections.Counter(); halluc=[]
for d,xs in by.items():
  ok=[x for x in xs if "error" not in x]
  if d=="clean": det=sum(1 for x in ok if not x["veto"]); lab="no_veto"
  else:
    kind,code=expect[d]
    det=sum(1 for x in ok if (kind=="veto" and x["veto"] and code in (x["vetoReason"] or "")) or (kind=="low" and code in x["low"]))
    lab="caught"
  esc=sum(1 for x in ok if x["state"]!="provisional")
  print(f"{d:11s} n={len(xs)} {lab}={det}/{len(ok)} escalated_or_vetoed={esc} mean_conf={sum(x['confidence'] for x in ok)/len(ok):.2f}")
  for x in ok:
    for k,v in x["fieldOk"].items():
      fieldsn[k]+=1; fields[k]+=v
      if not v and d!="clean" and d.replace("no_","") in (k,"org" if k=="organization" else "", "name" if k in("first_name","last_name") else "", "job" if k=="job_title" else ""): halluc.append((x["id"],k,x["got"].get(k)))
print("field accuracy:",{k:f"{fields[k]}/{fieldsn[k]}" for k in fieldsn})
print("possible invented values for removed fields:",halluc)
