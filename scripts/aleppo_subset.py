"""Leningrad vs Aleppo/MAM for the forms the vowel argument rests on.

Subset (defined 2026-10-11, replacing an earlier hand-made count of 141/105 that could not be reproduced):
qal active participles of the qoṭel pattern (no III-y, II-w/y roots) that end in ה, plus all such forms in major pause
(including the pausal segolates qoṭālet). Reads data/aleppo_comparison.csv (from check_aleppo.py) and
data/mt_fsg_participles.csv; Lev 7:9 is dropped, as everywhere else.
Run from the project root:  python scripts/aleppo_subset.py
"""
import os

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
a = pd.read_csv(os.path.join(ROOT, "data", "aleppo_comparison.csv"))
m = pd.read_csv(os.path.join(ROOT, "data", "mt_fsg_participles.csv"))
a = a[~((a.book == "Leviticus") & (a.chapter == 7) & (a.verse == 9))].reset_index(drop=True)
assert len(a) == len(m) and (a.lex.values == m.lex.values).all(), "comparison file and MT data are not aligned"
d = pd.concat([m, a[["aleppo_extant", "vowels_equal", "L_pause", "A_pause"]]], axis=1)
weak = d.root_class.str.contains(r"III-y|II-w/y", na=False)
qoTel = (d.stem == "qal") & (d.vt == "ptca") & (d.pattern_first_vowel == "holam") & ~weak
sub = d[qoTel & ((d.ending == "H") | (d.pause == "major"))]


def row(x, label):
    return {"set": label, "forms": len(x), "in surviving Aleppo": int(x.aleppo_extant.sum()),
            "same vowels": int(x.vowels_equal.sum()), "same pause class": int((x.L_pause == x.A_pause).sum())}


res = pd.DataFrame([row(d, "all fsg participles"), row(sub, "qal qoṭel forms in ה or in major pause")])
print(res.to_string(index=False))
