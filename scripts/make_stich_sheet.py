"""Coding sheet for stich position of the poetic qal fsg participles in ה.

Writes data/coding/stich_blind.csv: one row per poetic form of the 46-form set, with the consonantal text
(no vowels, no accents) of the preceding, current and following verse, the target word marked [[ ]].
The ending is visible (all forms end in ה); the vowel is not, except through plene spelling (ו).
Run from the project root:  python scripts/make_stich_sheet.py
"""
import os

import pandas as pd
from tf.fabric import Fabric

import analyse_ending as ae

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BHSA = os.path.expanduser("~/text-fabric-data/etcbc/bhsa/tf/2021")

m = pd.read_csv(os.path.join(ROOT, "data", "mt_fsg_participles.csv"))
c = pd.read_csv(os.path.join(ROOT, "data", "coding", "qal_h_coding.csv"))
d = c.merge(m, on="node")
d = d[d.lex != "CWBB/"].copy()
d["genre"] = [ae.genre(r) for r in d.itertuples()]
d = d[d.genre != "prose"]

TF = Fabric(locations=BHSA, silent="deep")
A = TF.load("g_cons_utf8 trailer_utf8", silent="deep")


def cons(words, target=None):
    out = []
    for w in words:
        s = A.F.g_cons_utf8.v(w)
        if w == target:
            s = f"[[{s}]]"
        tr = A.F.trailer_utf8.v(w)
        out.append(s + ("־" if "־" in tr else " " if tr else ""))  # prefixes have no trailer
    return "".join(out).strip()


rows = []
for r in d.sort_values("node").itertuples():
    w = int(r.node)
    v = A.L.u(w, "verse")[0]
    prev_v, next_v = A.L.p(v, "verse"), A.L.n(v, "verse")
    b, ch, vs = A.T.sectionFromNode(v)
    rows.append({
        "node": w, "ref": f"{b.replace('_', ' ')} {ch}:{vs}",
        "prev_verse": cons(A.L.d(prev_v[0], "word")) if prev_v else "",
        "verse": cons(A.L.d(v, "word"), w),
        "next_verse": cons(A.L.d(next_v[0], "word")) if next_v else "",
    })
pd.DataFrame(rows).to_csv(os.path.join(ROOT, "data", "coding", "stich_blind.csv"), index=False, encoding="utf-8-sig")
print(len(rows), "rows written to data/coding/stich_blind.csv")
