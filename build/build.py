# -*- coding: utf-8 -*-
"""医療情報基礎知識検定 学習アプリ ビルドスクリプト

  glossary.json（用語集PDFから抽出）＋ q1〜q7.json（厳選問題）を
  template.html に埋め込んで、単一ファイルの index.html を生成する。

  使い方:  python build.py
"""
import json, os, sys, io, re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.abspath(os.path.join(HERE, "..", "index.html"))

def main():
    g = json.load(open(os.path.join(HERE, "glossary.json"), encoding="utf-8"))

    entries = []
    for e in g["entries"]:
        entries.append({
            "minor": e["minor"],
            "term":  e["term"],
            "def":   e["def"],
            "adv":   e["adv"],
            "alias": bool(e.get("alias")),
        })

    minors = {}
    for k, v in g["minors"].items():
        minors[k] = {"title": v["title"], "points": v["points"]}

    questions, seen = [], set()
    for i in range(1, 8):
        p = os.path.join(HERE, "q%d.json" % i)
        if not os.path.exists(p):
            continue
        for q in json.load(open(p, encoding="utf-8")):
            assert isinstance(q["c"], list) and len(q["c"]) == 4, "選択肢は4つ: " + q["q"][:30]
            assert 0 <= q["a"] <= 3, "正答番号が不正: " + q["q"][:30]
            assert q["cat"] in minors, "未知の中分類: " + q["cat"]
            assert q["q"] not in seen, "問題文の重複: " + q["q"][:30]
            seen.add(q["q"])
            questions.append(q)

    data = {"minors": minors, "entries": entries, "questions": questions}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    assert "__DATA__" in tpl
    html = tpl.replace("__DATA__", payload)

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    per = {}
    for q in questions:
        per[q["cat"][0]] = per.get(q["cat"][0], 0) + 1
    print("用語 %d 語 / 中分類 %d / 問題 %d 問" % (len(entries), len(minors), len(questions)))
    print("大分類別の問題数:", dict(sorted(per.items())))
    print("出力:", OUT, "(%.0f KB)" % (os.path.getsize(OUT) / 1024))

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
