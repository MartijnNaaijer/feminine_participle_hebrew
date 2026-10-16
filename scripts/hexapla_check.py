"""Secunda (Origen's Hexapla, second column) readings for the MT fsg participles.

Source: Göttinger Septuaginta, Hexapla Database v3 (https://septuaginta.uni-goettingen.de/hexapla/; CC BY-NC-SA 4.0),
public verse API /api/hexapla/v3/?versekey=10BBCCCVVV (BB = 10 for 2 Samuel, 25 for Psalms, LXX numbering; on
2026-10-11 no other book code from 01 to 59 answered). Responses are cached in data/hexapla_cache/. Each MT form is
located by its consonants in the database's own MT column; the Secunda cell at the same position is reported.
Writes data/hexapla_fsg.csv.  Run from the project root:  python scripts/hexapla_check.py
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CACHE = os.path.join(ROOT, "data", "hexapla_cache")
API = "https://septuaginta.uni-goettingen.de/api/hexapla/v3/?versekey={}"


def get(vk):
    p = os.path.join(CACHE, f"{vk}.json")
    if not os.path.exists(p):
        req = urllib.request.Request(API.format(vk), headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        os.makedirs(CACHE, exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(data)
        time.sleep(0.5)
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def cols(d, slugs=("mt", "secunda", "lxx-edition")):
    res = {s: [] for s in slugs}
    for seg in d.get("segments", []):
        for pos in seg["positions"]:
            for c in pos["cells"]:
                if c["tradition"] in slugs:
                    t = " / ".join(" ".join(tok["text"] for tok in rd["tokens"]) for rd in c["readings"])
                    res[c["tradition"]].append((seg["stichos"], pos["position"], t))
    return res


def lxx(ch, v):
    """MT Psalm chapter/verse -> candidate LXX chapter/verse (the MT column of the hit is checked afterwards)."""
    if ch <= 9 or ch >= 148:
        return [(ch, v)]
    if ch == 10:
        return [(9, v + 21), (9, v + 20), (9, v + 22)]
    if 11 <= ch <= 113 or 117 <= ch <= 146:
        return [(ch - 1, v)]
    if ch in (114, 115):
        return [(113, v), (113, v + 8), (113, v + 9)]
    if ch == 116:
        return [(114, v)] if v <= 9 else [(115, v - 9)]
    if ch == 147:
        return [(146, v)] if v <= 11 else [(147, v - 11)]


def strip(s):
    return re.sub(r"[֑-ׇ־ /|׃]", "", s)


m = pd.read_csv(os.path.join(ROOT, "data", "mt_fsg_participles.csv"))
m = m[m.book.isin(["Psalms", "2_Samuel"])]
rows = []
for r in m.itertuples():
    word, found = strip(str(r.word)), None
    bk = 25 if r.book == "Psalms" else 10
    cands = lxx(r.chapter, r.verse) if r.book == "Psalms" else [(r.chapter, r.verse)]
    for ch, v in cands:
        for vv in (v, v - 1, v + 1):
            vk = f"10{bk:02d}{ch:03d}{vv:03d}"
            try:
                d = get(vk)
            except urllib.error.HTTPError:
                continue
            c = cols(d)
            hit = [x for x in c["mt"] if word in strip(x[2])]
            if hit:
                found = (vk, d["passage"]["display"], c, hit)
                break
        if found:
            break
    base = dict(ref=f"{r.book.replace('_', ' ')} {r.chapter}:{r.verse}", word=r.word, stem=r.stem, ending=r.ending)
    if not found:
        rows.append({**base, "hexapla": "not located"})
        continue
    vk, disp, c, hit = found
    st, pos = hit[0][0], hit[0][1]
    rows.append({**base, "hexapla": disp, "versekey": vk,
                 "secunda_at_position": " / ".join(x[2] for x in c["secunda"] if (x[0], x[1]) == (st, pos)),
                 "secunda_verse": " | ".join(x[2] for x in c["secunda"])})
out = pd.DataFrame(rows)
out.to_csv(os.path.join(ROOT, "data", "hexapla_fsg.csv"), index=False, encoding="utf-8-sig")
print(f"{len(out)} forms; located {int((out.hexapla != 'not located').sum())}; "
      f"with a Secunda reading at the position: {int((out.secunda_at_position.fillna('') != '').sum())}")
print(out[out.secunda_at_position.fillna("") != ""][["ref", "word", "stem", "hexapla", "secunda_at_position"]].to_string())
