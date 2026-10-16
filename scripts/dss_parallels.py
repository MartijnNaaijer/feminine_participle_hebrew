"""Biblical parallels for the non-biblical DSS fsg participles of non-weak roots, ה and ת alike.

Criterion (applied mechanically to every form, whatever its ending):
a form has a biblical parallel if some MT verse (BHSA) has a participle (any gender, number, stem)
of the same lexeme within 3 words of a word whose lexeme also occurs within 3 words of the DSS form
in the same scroll line. Only content words count (BHSA part of speech noun, verb, adjective, proper noun),
and a few very frequent lexemes are ignored.

Reads data/dss_fsg_participles.csv; writes data/dss_parallels.csv and data/dss_parallels_tables.md.
Run from the project root:  python scripts/dss_parallels.py
"""
import os
from collections import defaultdict

import pandas as pd
from scipy.stats import fisher_exact
from tf.fabric import Fabric

from mdtable import to_md

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DSS = os.path.expanduser("~/text-fabric-data/github/ETCBC/dss/tf/2.0.1")
BHSA = os.path.expanduser("~/text-fabric-data/etcbc/bhsa/tf/2021")
WINDOW = 3
IGNORE = {"KL/", "HJH[", ">LHJM/", "JHWH/", ">MR[", "L>", ">JN/"}
CONTENT = {"subs", "verb", "adjv", "nmpr"}

d = pd.read_csv(os.path.join(ROOT, "data", "dss_fsg_participles.csv"))
d["weak"] = d.root_class.str.extract(r"(III-y|II-w/y|II-gem)")[0].fillna("other")
tgt = d[(d.biblical == 0) & (d.last_letter == "ok") & d.ending.isin(["H", "T"]) & (d.state != "c")
        & (d.weak == "other") & (((d.stem == "qal") & (d.vt == "ptca")) | (d.stem == "nifal"))].copy()

# BHSA: content lexemes and participle positions
TFb = Fabric(locations=BHSA, silent="deep")
B = TFb.load("lex sp vt gn nu g_cons", silent="deep")
content = {B.F.lex.v(w) for w in B.F.otype.s("word") if B.F.sp.v(w) in CONTENT} - IGNORE
ptc_by_lex = defaultdict(list)
for w in B.F.otype.s("word"):
    if B.F.vt.v(w) in ("ptca", "ptcp"):
        ptc_by_lex[B.F.lex.v(w)].append(w)


def bhsa_neighbours(w):
    v = B.L.u(w, "verse")[0]
    ws = B.L.d(v, "word")
    i = ws.index(w)
    return {B.F.lex.v(x) for x in ws[max(0, i - WINDOW):i + WINDOW + 1] if x != w}


# DSS: neighbour lexemes in the same line
TFd = Fabric(locations=DSS, silent="deep")
S = TFd.load("lex_etcbc glyph", silent="deep")
rows = []
for r in tgt.itertuples():
    w = int(r.node)
    line = S.L.u(w, "line")[0]
    ws = [x for x in S.L.d(line, "word") if S.F.glyph.v(x) or x == w]  # skip empty nodes (they repeat a lexeme)
    i = ws.index(w)
    lex0 = S.F.lex_etcbc.v(w)
    neigh = ({S.F.lex_etcbc.v(x) for x in ws[max(0, i - WINDOW):i + WINDOW + 1] if x != w} & content) - {lex0}
    lex = S.F.lex_etcbc.v(w)
    hits, mt_end = [], set()
    for bw in ptc_by_lex.get(lex, []):
        shared = bhsa_neighbours(bw) & neigh
        if shared:
            b, c, v = B.T.sectionFromNode(bw)
            hits.append(f"{b} {c}:{v} [{','.join(sorted(shared))}]")
            if B.F.gn.v(bw) == "f" and B.F.nu.v(bw) == "sg":
                mt_end.add("H" if B.F.g_cons.v(bw).endswith("H") else "T" if B.F.g_cons.v(bw).endswith("T") else "?")
    rows.append({"node": w, "scroll": r.scroll, "fragment": r.fragment, "line": r.line, "glyph": r.glyph,
                 "stem": r.stem, "ending": r.ending, "lex": lex, "neighbours": " ".join(sorted(neigh)),
                 "n_parallels": len(hits), "parallels": "; ".join(hits[:5]),
                 "mt_fsg_endings": "".join(sorted(mt_end)) or "-", "line_text": r.line_text})
p = pd.DataFrame(rows)
p["parallel"] = p.n_parallels > 0
# copies of one composition: count a passage once (same composition, same lexeme, a shared neighbour lexeme)
COMPOSITION = {"1QHa": "Hodayot", "4Q427": "Hodayot", "4Q428": "Hodayot", "4Q429": "Hodayot", "4Q430": "Hodayot",
               "4Q431": "Hodayot", "4Q432": "Hodayot", "CD": "Damascus", "4Q266": "Damascus", "4Q267": "Damascus",
               "4Q268": "Damascus", "4Q269": "Damascus", "4Q270": "Damascus", "4Q271": "Damascus", "4Q272": "Damascus",
               "4Q273": "Damascus", "1QS": "Serekh", "4Q255": "Serekh", "4Q256": "Serekh", "4Q257": "Serekh",
               "4Q258": "Serekh", "4Q259": "Serekh", "4Q260": "Serekh", "4Q261": "Serekh", "4Q262": "Serekh",
               "4Q263": "Serekh", "4Q264": "Serekh", "1QM": "War", "4Q491": "War", "4Q492": "War", "4Q493": "War",
               "4Q494": "War", "4Q495": "War", "4Q496": "War"}
p["composition"] = p.scroll.map(COMPOSITION).fillna(p.scroll)
keep, seen = [], []
for r in p.itertuples():
    nb = set(r.neighbours.split())
    # same line (dittography), or another manuscript of the same composition with largely the same neighbours
    dup = any(c == r.composition and l == r.lex and ((sc, f, ln) == (r.scroll, r.fragment, r.line)
              or (sc != r.scroll and nb and len(nb & n) / len(nb | n) >= 0.5)) for c, l, n, sc, f, ln in seen)
    keep.append(not dup)
    seen.append((r.composition, r.lex, nb, r.scroll, r.fragment, r.line))
p["first_copy"] = keep
MANUAL_COPIES = {1714334}  # 4Q269 f7:8 = 4Q266 f6i:12 (context restored in 4Q269, so the overlap rule misses it)
p.loc[p.node.isin(MANUAL_COPIES), "first_copy"] = False
chk = pd.read_csv(os.path.join(ROOT, "data", "coding", "dss_parallel_check.csv"))
p = p.merge(chk, on="node", how="left")
p["check"] = p.check.fillna("no match")
missing = p[p.parallel & p.first_copy & (p.check == "no match")]
assert missing.empty, f"mechanical matches without a manual check: {list(missing.node)}"
p.to_csv(os.path.join(ROOT, "data", "dss_parallels.csv"), index=False, encoding="utf-8-sig")

out = []
for stem, label in [("qal", "qal, all manuscript tokens"), ("qal", "qal, copies counted once"),
                    ("nifal", "niphal, all manuscript tokens"), ("nifal", "niphal, copies counted once")]:
    s = p[(p.stem == stem) & (p.first_copy | label.endswith("tokens"))]
    t = pd.crosstab(s.ending, s.parallel).reindex(columns=[True, False], fill_value=0)
    out.append(f"## {label}: forms with a biblical parallel (criterion in the script docstring)\n")
    out.append(to_md(t.rename(columns={True: "parallel", False: "no parallel"})))
    if t.shape == (2, 2):
        out.append(f"\nFisher's exact test: p = {fisher_exact(t.values)[1]:.4f} (n = {len(s)}).\n")
    out.append("")
cols = ["scroll", "fragment", "line", "glyph", "stem", "ending", "first_copy", "mt_fsg_endings", "parallels", "line_text"]
out.append("## Manual check of the mechanical matches (copies once; data/coding/dss_parallel_check.csv)\n")
ORDER = ["biblical phrase", "citation", "generic phrase", "uncertain", "chance", "no match"]
out.append(to_md(pd.crosstab([p[p.first_copy].stem, p[p.first_copy].ending], p[p.first_copy].check).reindex(columns=ORDER, fill_value=0)))
out.append("")
for stem in ("qal", "nifal"):
    s = p[(p.stem == stem) & p.parallel & p.first_copy]
    out.append(f"## {stem}, with a parallel (copies once): DSS ending × endings of the matching MT fsg forms\n")
    out.append("MT endings: H = only ה, T = only ת, HT = both, - = no matching MT form is a fsg.\n")
    out.append(to_md(pd.crosstab(s.ending, s.mt_fsg_endings)))
    out.append("")
    out.append(to_md(s[["scroll", "fragment", "line", "glyph", "ending", "mt_fsg_endings", "parallels"]].set_index("scroll")))
    out.append("")
out.append("## All forms\n")
out.append(to_md(p.sort_values(["stem", "ending", "scroll"])[cols].set_index("scroll")))
with open(os.path.join(ROOT, "data", "dss_parallels_tables.md"), "w", encoding="utf-8") as fh:
    fh.write("# Biblical parallels of non-biblical DSS fsg participles (non-weak roots)\n\n" + "\n".join(out) + "\n")
print(p.groupby(["stem", "ending"]).parallel.agg(["sum", "size"]))
print(p[p.first_copy].groupby(["stem", "ending"]).parallel.agg(["sum", "size"]))
