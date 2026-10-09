# -*- coding: utf-8 -*-
import fitz, re, json, sys, os
sys.stdout.reconfigure(encoding='utf-8')
# 使い方: python parse2.py <用語集PDFのパス>（省略時は同じフォルダの Medical-Information-Basic-Glossary-2nd.pdf）
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "Medical-Information-Basic-Glossary-2nd.pdf")
doc = fitz.open(SRC)
BOLDF = {"MS-Gothic","Arial-BoldMT","ArialMT","SymbolMT","Century-Bold"}
entries=[]; minors={}; cur_major=None; cur_minor=None; cur=None; pending_wrap=False

def join(paras):
    out=[]
    for p in paras:
        s=""
        for ln in p:
            if s and re.search(r"[0-9A-Za-z\-]$", s) and re.match(r"[0-9A-Za-z]", ln):
                s+=" "
            s+=ln
        out.append(s)
    return out

def flush():
    global cur
    if cur:
        cur["paras"]=join(cur["paras"])
        # split 【発展】
        adv=[]; main=[]
        hit=False
        for p in cur["paras"]:
            if p.startswith("【発展】"): hit=True
            (adv if hit else main).append(p)
        cur["def"]=main; cur["adv"]=[re.sub(r"^【発展】","",a) for a in adv]
        del cur["paras"]
        entries.append(cur); cur=None

for pno,page in enumerate(doc):
    if pno<7: continue
    lines=[]
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines",[]):
            spans=[s for s in l["spans"] if s["text"].strip()]
            if not spans: continue
            txt="".join(s["text"] for s in l["spans"]).rstrip()
            lines.append((l["bbox"][1], min(s["bbox"][0] for s in spans),
                          max(s["bbox"][2] for s in spans), txt, spans))
    lines.sort(key=lambda t:(round(t[0],1), t[1]))
    for y,x0,x1,txt,spans in lines:
        t=txt.strip()
        if not t or t.startswith("日本医療情報学会医療情報技師育成部会"): continue
        if re.fullmatch(r"[ivxlc0-9]+", t): continue
        sz=max(s["size"] for s in spans); allbold=all(s["font"] in BOLDF for s in spans)
        m=re.match(r"^([１２３４５６７]) ?[．.](.+)$", t)
        if m and sz>11:
            flush(); cur_major=t.replace("．",". "); pending_wrap=False; continue
        m=re.match(r"^(\d{3})\s*(\S.*)$", t)
        if m and allbold and x0<60 and len(t)<40:
            flush(); cur_minor=m.group(1)
            minors[cur_minor]={"title":m.group(2).strip(),"major":cur_major,"points":[]}
            pending_wrap=False; continue
        if t=="主要な学習ポイント": pending_wrap=False; continue
        if t.startswith("♦"):
            if cur_minor: minors[cur_minor]["points"].append(t.lstrip("♦ ").strip())
            continue
        if allbold and x0<60:
            if pending_wrap and cur and not cur["paras"]:
                cur["term"]+=t
            else:
                flush(); cur={"major":cur_major,"minor":cur_minor,"term":t,"paras":[],"page":pno+1}
            pending_wrap = x1>500
            continue
        pending_wrap=False
        if cur is None: continue
        if x0>62 or not cur["paras"]: cur["paras"].append([t])
        else: cur["paras"][-1].append(t)
flush()

# normalize terms: split aliases in parentheses
for e in entries:
    e["term"]=e["term"].strip()
    e["alias"] = bool(e["def"]) and e["def"][0].startswith("→")
json.dump({"entries":entries,"minors":minors}, open("glossary.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("entries",len(entries),"alias",sum(e["alias"] for e in entries))
with open("glossary_clean.txt","w",encoding="utf-8") as f:
    lastmin=None
    for e in entries:
        if e["minor"]!=lastmin:
            lastmin=e["minor"]
            f.write(f"\n\n========== {e['major']} / {lastmin} {minors[lastmin]['title']} ==========\n")
            for p in minors[lastmin]["points"]: f.write(f"  [POINT] {p}\n")
        f.write(f"\n■{e['term']}\n")
        for p in e["def"]: f.write(f"  {p}\n")
        for p in e["adv"]: f.write(f"  【発展】{p}\n")
print("ok")

# --- post: merge broken paragraphs ---
import json,re
d=json.load(open("glossary.json",encoding="utf-8"))
def fix(ps):
    out=[]
    for p in ps:
        if out and not re.search(r"[。」）\)】]$", out[-1]) and not p.startswith("→"):
            out[-1]+=p
        else: out.append(p)
    return out
for e in d["entries"]:
    e["def"]=fix(e["def"]); e["adv"]=fix(e["adv"])
json.dump(d, open("glossary.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
with open("glossary_clean.txt","w",encoding="utf-8") as f:
    lastmin=None
    for e in d["entries"]:
        if e["minor"]!=lastmin:
            lastmin=e["minor"]; m=d["minors"][lastmin]
            f.write(f"\n========== {m['major']} / {lastmin} {m['title']} ==========\n")
            for p in m["points"]: f.write(f"[POINT] {p}\n")
        f.write(f"■{e['term']}\n")
        for p in e["def"]: f.write(f"  {p}\n")
        for p in e["adv"]: f.write(f"  【発展】{p}\n")
print("fixed")
