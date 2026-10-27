from scipy.stats import fisher_exact
import math
def ci(k,n,method=None,z=1.959964):
  p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return c-h,c+h
rows={"academic_returned":((0,57),(72,665)),"employer_returned":((1,134),(115,712)),"pooled_returned":((1,191),(187,1377)),"pooled_edited":((12,191),(266,1377))}
for k,((a,n1),(b,n2)) in rows.items():
  p=fisher_exact([[a,n1-a],[b,n2-b]])[1]; rr=((a+.5)/(n1+1))/((b+.5)/(n2+1))
  l1,u1=ci(a,n1,method="wilson"); l2,u2=ci(b,n2,method="wilson")
  print(f"{k}: AI {a}/{n1}={100*a/n1:.1f}% [{100*l1:.1f}-{100*u1:.1f}]  manual {b}/{n2}={100*b/n2:.1f}% [{100*l2:.1f}-{100*u2:.1f}]  p={p:.2e}  RR(cc)={rr:.3f}")
