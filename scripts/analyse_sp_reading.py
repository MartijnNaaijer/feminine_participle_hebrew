"""Samaritan reading: the ū pattern in qal fsg participles, and qal 3fs perfects as a control.

1. ū after the first radical (fūqəd) in qal active fsg participles of non-weak roots,
   by article (BHSA: preceding word is the article) and guttural first radical.
   Excluded: the verbal adjective מְלֵאָה; suffixed forms; forms the Samaritan reading
   does not read as active participles (Gen 16:11 perfect, Lev 11:26 passive, Lev 26:25 noun).
2. Control: do Tiberian qal 3fs perfects with a reduced vowel (קָטְלָה) have a reduced vowel
   in the Samaritan reading? Strong roots only (no III-y, II-w/y, II-gem), Genesis–Deuteronomy.

Reads data/sp_fsg_participles.csv, data/mt_fsg_participles.csv, BHSA and the Samaritan link file;
writes data/sp_reading_tables.md. The readings come from the machine-read transcription
(schwa not verified); forms cited in the report were checked on the printed page.
Run from the project root:  python scripts/analyse_sp_reading.py
"""
import os
from collections import defaultdict

import pandas as pd
from tf.fabric import Fabric

from mdtable import to_md

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LINK = os.path.join(ROOT, "data", "bh_sp_link.tsv")
BHSA = os.path.expanduser("~/text-fabric-data/etcbc/bhsa/tf/2021")
out = []


def table(title, df, note=""):
    out.append(f"## {title}\n")
    if note:
        out.append(note + "\n")
    out.append(to_md(df))
    out.append("")


# 1. ū pattern
sp = pd.read_csv(os.path.join(ROOT, "data", "sp_fsg_participles.csv"))
mt = pd.read_csv(os.path.join(ROOT, "data", "mt_fsg_participles.csv"))
q = sp[(sp.stem == "qal") & (sp.vt == "ptca") & sp.sp_reading.notna()].merge(
    mt[["book", "chapter", "verse", "lex", "prev_lex", "suffix"]].drop_duplicates(["book", "chapter", "verse", "lex"]),
    on=["book", "chapter", "verse", "lex"], how="left")
NOT_PTC = {("Genesis", 16, 11), ("Leviticus", 11, 26), ("Leviticus", 26, 25)}
q = q[~q.root_class.str.contains(r"III-y|II-w/y") & (q.lex != "ML>[")
      & (q.suffix.isin(["absent", "n/a"]) | q.suffix.isna())]
q = q[[(b, c, v) not in NOT_PTC for b, c, v in zip(q.book, q.chapter, q.verse)]]
q["article"] = q.prev_lex.eq("H")
q["I_guttural"] = q.root_class.str.contains(r"(?:^|,)I-gutt")
q["u"] = q.sp_reading.str.contains("ū")
t = q.groupby(["article", "I_guttural"]).agg(forms=("u", "size"), with_u=("u", "sum"), lexemes=("lex", "nunique"))
table("ū after the first radical, by article and guttural first radical", t,
      f"{len(q)} qal active fsg participles of non-weak roots with a Samaritan reading (exclusions in the docstring).")
q["ref"] = q.book + " " + q.chapter.astype(str) + ":" + q.verse.astype(str)
table("Articled forms", q[q.article][["ref", "lex", "mt_word", "sp_reading", "u"]].set_index("ref"))

# 2. 3fs perfect control
link = defaultdict(list)
with open(LINK, encoding="utf-8") as fh:
    for line in fh:
        if line.startswith("#"):
            continue
        book, ch, vs, num, tok, nodes, gc, sc, spv = line.rstrip("\n").split("\t")
        a, b = spv.split(":")
        link[(book, a, b)].append((gc.split("+")[-1], tok))
TF = Fabric(locations=BHSA, silent="deep")
api = TF.load("vs vt ps gn nu g_cons g_word g_word_utf8 lex prs", silent="deep")
F, T = api.F, api.T
rows = []
for w in F.otype.s("word"):
    if (F.vs.v(w), F.vt.v(w), F.ps.v(w), F.gn.v(w), F.nu.v(w)) != ("qal", "perf", "p3", "f", "sg"):
        continue
    b, c, v = T.sectionFromNode(w)
    if b not in ("Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy") or F.prs.v(w) not in ("absent", "n/a"):
        continue
    gw = F.g_word.v(w)
    if ":" not in gw:  # keep only Tiberian forms with a reduced vowel (šwa or ḥaṭef) before the ending
        continue
    lex = F.lex.v(w)
    if lex.endswith("H[") or lex[1:2] == lex[2:3]:  # III-y, II-gem
        continue
    cand = [tok for g, tok in link.get((b, str(c), str(v)), []) if g == F.g_cons.v(w)]
    if cand:
        rows.append({"ref": f"{b} {c}:{v}", "word": F.g_word_utf8.v(w), "lex": lex, "sp_reading": cand[0],
                     "reduced_in_SH": "ə" in cand[0]})
p = pd.DataFrame(rows)
table("Control: Tiberian qal 3fs perfects with a reduced vowel, and their Samaritan reading",
      p.groupby("reduced_in_SH").agg(forms=("lex", "size"), lexemes=("lex", "nunique")),
      "A reduced vowel (ə) in the Samaritan reading of the stem would parallel Tiberian קָטְלָה.")
table("Control forms", p.set_index("ref"))

with open(os.path.join(ROOT, "data", "sp_reading_tables.md"), "w", encoding="utf-8") as fh:
    fh.write("# Samaritan reading: ū pattern and 3fs perfect control\n\n" + "\n".join(out))
print("written data/sp_reading_tables.md")
