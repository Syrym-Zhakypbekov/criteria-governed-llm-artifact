import json,sys
r=json.load(open(sys.argv[1],encoding="utf-8"))
print("tau  defects_routed_to_human  clean_routed_to_human  (contracts v2, n_def=28, n_clean=8)")
for tau in [0.5,0.6,0.7,0.8,0.85,0.9,0.95,0.99,1.0]:
  esc=lambda x: x["veto"] or (x["sTotal"] is not None and x["sTotal"]<tau)
  d=[x for x in r if x["defect"]!="clean"]; c=[x for x in r if x["defect"]=="clean"]
  print(f"{tau:4.2f} {sum(map(esc,d)):3d}/{len(d)} = {100*sum(map(esc,d))/len(d):5.1f}%   {sum(map(esc,c))}/{len(c)}")
print("sTotal by defect:", sorted({(x['defect'],x['sTotal']) for x in r}))
