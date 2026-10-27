# Synthetic business cards (fictional people/companies, example.* domains) with planted defects → PNG + truth.json
import json, random
from PIL import Image, ImageDraw, ImageFont
random.seed(42)
F=lambda s: ImageFont.truetype("C:/Windows/Fonts/arial.ttf", s)
first=["Daniel","Maria","Arman","Aigerim","Lukas","Sofia","Timur","Elena","Omar","Hana","Nikolai","Zhanna"]
last=["Kessler","Rossi","Sadykov","Nurlanova","Weber","Novak","Bekov","Ivanova","Haddad","Sato","Petrov","Abenova"]
orgs=[("University of Northvale","Department of Computer Science","Associate Professor","United Kingdom","+44 161 306 6000"),
      ("Technische Hochschule Westfeld","Faculty of Informatics","Professor","Germany","+49 30 1234 5678"),
      ("Almaty Synthetic Tech LLP","","Chief Technology Officer","Kazakhstan","+7 727 300 1234"),
      ("Universita di Esempio","Dipartimento di Ingegneria","Researcher","Italy","+39 06 4991 0000"),
      ("Example Data Systems Inc.","","Head of Analytics","United States","+1 415 555 0134"),
      ("Instituto Ficticio de Tecnologia","School of Engineering","Assistant Professor","Spain","+34 91 555 0199")]
defects=["clean"]*8+["no_email"]*4+["no_org"]*4+["no_name"]*4+["no_country"]*4+["no_job"]*4
cases=[]
for i,d in enumerate(defects):
    fn,ln=first[i%12],last[(i*5)%12]; org,dept,job,country,phone=orgs[i%6]
    email=f"{fn.lower()}.{ln.lower()}@example.{['ac.uk','de','kz','it','com','es'][i%6]}"
    lines=[]
    if d!="no_name": lines.append((f"Dr {fn} {ln}",38))
    if d!="no_job": lines.append((job,24))
    if dept: lines.append((dept,22))
    if d!="no_org": lines.append((org,26))
    addr={"United Kingdom":"Oxford Road, Manchester M13 9PL, United Kingdom","Germany":"Hauptstrasse 1, 10115 Berlin, Germany","Kazakhstan":"Abay Ave 10, Almaty 050000, Kazakhstan","Italy":"Via Roma 1, 00185 Roma, Italy","United States":"1 Market St, San Francisco, CA 94105, USA","Spain":"Calle Mayor 1, 28013 Madrid, Spain"}[country]
    if d=="no_country": addr=addr.split(",")[0]
    lines.append((addr,20)); lines.append((f"Tel: {phone}",20))
    if d!="no_email": lines.append((f"E-mail: {email}",20))
    img=Image.new("RGB",(1050,600),(250,250,246)); dr=ImageDraw.Draw(img); y=60
    dr.rectangle([0,0,18,600],fill=(164,36,33))
    for t,s in lines: dr.text((70,y),t,fill=(30,30,30),font=F(s)); y+=s+26
    p=f"C:/Users/syrym/AppData/Local/Temp/apex/cards/card{i:02d}.png"; img.save(p)
    cases.append({"file":p,"defect":d,"truth":{"first_name":"" if d=="no_name" else fn,"last_name":"" if d=="no_name" else ln,"email":"" if d=="no_email" else email,
      "organization":"" if d=="no_org" else org,"job_title":"" if d=="no_job" else job,"country":"" if d=="no_country" else country}})
json.dump(cases,open("C:/Users/syrym/AppData/Local/Temp/apex/cards/truth.json","w"),indent=1); print(len(cases))
