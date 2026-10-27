# HELD-OUT business cards for the FROZEN operator (written 27.10.2026 after all design iterations): new visual designs
# (dark theme, two-colour band, Times/Calibri/Georgia, no «Dr», slight rotation, lower resolution), new people,
# organisations and countries, single and compound defects. Fictional data, example.* domains. Output: PNG + truth.json
# usage: python mkcards_holdout.py <out_dir>
import json, random, sys, os
from PIL import Image, ImageDraw, ImageFont
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True); random.seed(2710)
FONTS = ["C:/Windows/Fonts/times.ttf", "C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/georgia.ttf"]
first = ["Akira", "Camille", "Yerlan", "Selin", "Liam", "Dana", "Rustam", "Ines", "Kenji", "Madina", "Pierre", "Aruzhan", "Noah", "Leyla", "Bauyrzhan"]
last = ["Tanaka", "Moreau", "Zhumabekov", "Yilmaz", "Walsh", "Seitkali", "Karimov", "Duarte", "Mori", "Omarova", "Laurent", "Tulegenova", "Brooks", "Aliyeva", "Serikov"]
orgs = [("Kyoto Example University", "Graduate School of Informatics", "Professor", "Japan", "Yoshida-honmachi, Kyoto 606-8501, Japan", "+81 75 555 0101"),
        ("Universite Fictive de Lyon", "Laboratoire d'Informatique", "Maitre de conferences", "France", "12 rue Exemple, 69007 Lyon, France", "+33 4 72 55 01 23"),
        ("Steppe Analytics LLP", "", "Data Engineering Lead", "Kazakhstan", "Dostyk Ave 52, Astana 010000, Kazakhstan", "+7 7172 55 0199"),
        ("Bosphorus Sample University", "Department of Industrial Engineering", "Assistant Professor", "Turkey", "Bebek Cd. 1, 34342 Istanbul, Turkey", "+90 212 555 0123"),
        ("Maple Synthetic Systems Inc.", "", "VP of Product", "Canada", "100 King St W, Toronto, ON M5X 1A9, Canada", "+1 416 555 0175")]
plan = ["clean"] * 6 + ["no_email"] * 3 + ["no_org"] * 3 + ["no_name"] * 3 + ["no_country"] * 3 + ["no_job"] * 3 + ["no_job+no_country"] * 2 + ["no_name+no_email"] * 2
cases = []
for i, spec in enumerate(plan):
    d = set() if spec == "clean" else set(spec.split("+"))
    fn, ln = first[i % 15], last[(i * 4) % 15]; org, dept, job, country, addr, phone = orgs[i % 5]
    email = f"{fn[0].lower()}.{ln.lower()}@example.{['jp','fr','kz','com.tr','ca'][i % 5]}"
    theme = i % 3; font = FONTS[i % 3]; F = lambda s: ImageFont.truetype(font, s)
    bg, fg, acc = [((24, 32, 44), (235, 235, 235), (90, 170, 220)), ((255, 255, 255), (20, 20, 20), (0, 110, 90)), ((245, 238, 225), (60, 40, 30), (150, 60, 30))][theme]
    img = Image.new("RGB", (900, 520), bg); dr = ImageDraw.Draw(img)
    if theme == 1: dr.rectangle([0, 440, 900, 520], fill=acc)
    else: dr.rectangle([860, 0, 900, 520], fill=acc)
    left, right = [], []
    if "no_name" not in d: left.append((f"{fn} {ln.upper()}", 40))
    if "no_job" not in d: left.append((job, 24))
    if dept: left.append((dept, 20))
    if "no_org" not in d: left.append((org, 24))
    a = addr if "no_country" not in d else addr.rsplit(",", 1)[0]
    right += [(a, 18), (phone, 18)]
    if "no_email" not in d: right.append((email, 18))
    y = 50
    for t, s in left: dr.text((50, y), t, fill=fg, font=F(s)); y += s + 22
    y = max(y + 20, 300)
    for t, s in right: dr.text((50, y), t, fill=fg, font=F(s)); y += s + 14
    img = img.rotate(random.choice([-2.5, -1.5, 1.5, 2.5]), expand=True, fillcolor=bg).resize((760, 460))
    name = f"h{i:02d}.png"; img.save(os.path.join(OUT, name))
    cases.append({"file": name, "defects": sorted(d)})
json.dump(cases, open(os.path.join(OUT, "truth.json"), "w"), indent=1); print(len(cases), "cards")
