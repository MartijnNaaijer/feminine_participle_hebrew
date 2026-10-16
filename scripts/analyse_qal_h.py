"""Vowel of the qal fsg participles in ה (qoṭelā vs qoṭlā), tested factor by factor.

Joins the manual coding in data/coding/qal_h_coding.csv (external function,
internal verbal syntax, lexicalization; coded from the unpointed text in
data/coding/qal_h_blind.csv) with the MT data and writes data/qal_h_tables.md.

Main set: the 46 qal forms of non-weak roots (the same set as the ending
analysis). The three forms of שׁוֹבֵב (BHSA: adjective, root II-w/y; Jer 8:5 may
be a polel perfect) are reported only as a sensitivity check.
Run from the project root:  python scripts/analyse_qal_h.py
"""
import os

import pandas as pd
from scipy.stats import binomtest, fisher_exact

from mdtable import to_md

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
d = pd.read_csv(os.path.join(ROOT, "data", "mt_fsg_participles.csv"))
c = pd.read_csv(os.path.join(ROOT, "data", "coding", "qal_h_coding.csv"))
allm = c.merge(d, on="node")
allm["vowel"] = allm.form_subtype.map(lambda x: "qoṭelā" if x == "sere" else "qoṭlā")
allm["complement"] = allm.int_syntax.map(lambda x: "none" if x == "none" else "complement")
allm["II_gem"] = allm.root_class.str.contains("II-gem")
allm["plene"] = allm.word.str.contains("ו", regex=False)  # ו after the first radical (all forms are qoṭel type)
allm["ref"] = allm.book.str.replace("_", " ") + " " + allm.chapter.astype(str) + ":" + allm.verse.astype(str)
m = allm[allm.lex != "CWBB/"]
out = []


def table(title, df, note=""):
    out.append(f"## {title}\n")
    if note:
        out.append(note + "\n")
    out.append(to_md(df))
    out.append("")


def ct(df, rows):
    t = pd.crosstab([df[r] for r in rows], df.vowel)
    for v in ("qoṭelā", "qoṭlā"):
        if v not in t:
            t[v] = 0
    t["lexemes"] = df.groupby(rows).lex.nunique()
    return t


def fisher(df, mask, label):
    tab = pd.crosstab(mask, df.vowel)
    if tab.shape == (2, 2):
        out.append(f"Fisher's exact test, {label}: p = {fisher_exact(tab.values)[1]:.4f} (n = {len(df)}).\n")


table("All forms by pause", ct(m, ["pause"]), f"Main set: {len(m)} forms ({(m.vowel == 'qoṭlā').sum()} qoṭlā, {(m.vowel == 'qoṭelā').sum()} qoṭelā).")
table("Major pause by external function and complement", ct(m[m.pause == "major"], ["ext_function", "complement"]),
      "No form with a complement stands in major pause, so the pause effect cannot be separated from the absence of a complement.")
o = m[m.pause != "major"]
table("Outside major pause: function × complement", ct(o, ["ext_function", "complement"]))
table("Outside major pause: II-gem roots", ct(o, ["II_gem"]))
table("All forms: II-gem roots", ct(m, ["II_gem"]))
table("Outside major pause: accent level and clause end", ct(o, ["pause", "clause_final"]))
table("Outside major pause: lexicalization", ct(o, ["lexicalization"]))
table("Position: clause end × complement, all 46 forms", ct(m, ["clause_final", "complement"]),
      "Hypothesis: pausal forms are placed by position (clause end, main division of a clause), "
      "not by the accent. A participle followed by its complement cannot end the clause, so the cell with a complement "
      "and clause_final = 1 is empty by construction.")

# stress position from the accent placement (Leningrad, as in BHSA)
POSTPOS = {"֙", "֒", "֩", "֮"}   # pashta, segolta, telisha qetana, zinor: written on the last letter
PREPOS = {"֠", "֚", "֭"}              # telisha gedola, yetiv, dehi: written on the first letter


def stress(word, verse_final):
    letters = []
    for ch in word.strip():
        if "א" <= ch <= "ת":
            letters.append([ch, []])
        elif letters:
            letters[-1][1].append(ch)
    n = len(letters)
    accs = [(i, ch) for i, (_, ms) in enumerate(letters) for ch in ms if "֑" <= ch <= "֯"]
    if verse_final:  # silluq has the same code point as meteg: take the last one
        mets = [i for i, (_, ms) in enumerate(letters) if "ֽ" in ms]
        if mets:
            accs.append((mets[-1], "silluq"))
    main = [i for i, ch in accs if ch not in POSTPOS | PREPOS]
    post = [i for i, ch in accs if ch in POSTPOS]
    if main:
        idx = max(main)
    elif len(post) >= 2:   # two postpositives (not used: BHSA writes a doubled pashta as qadma + pashta, and qadma counts as main)
        idx = min(post)
    elif post:             # single pashta: final stress
        return "milraʿ"
    else:
        return "no accent"
    # every form ends in consonant + qameṣ + ה: the final syllable starts at letter n-2
    return "milraʿ" if idx >= n - 2 else "milʿel"


m["stress"] = [stress(q if isinstance(q, str) and q else w, vf == 1) for q, w, vf in zip(m.qere, m.word, m.verse_final)]
table("Stress (from the accents, Leningrad)", ct(m, ["stress", "pause"]),
      "Penultimate stress in qoṭlā (two syllables) is nesiga. In Ps 48:7 the Aleppo-based edition (MAM) has silluq on the "
      "last syllable, Leningrad on the penultimate.")
table("Forms with penultimate stress", m[m.stress == "milʿel"][["ref", "word", "accents", "pause", "complement", "vowel"]].set_index("ref"))

pos = pd.read_csv(os.path.join(ROOT, "data", "coding", "position_coding.csv"))
mp = m.merge(pos, on="node")
POS_NOTE = ("Hand-coded position (data/coding/position_coding.csv): R_end = end of the clause "
            "(relative and appositive phrases belong to their head); cf_initial / cf_preterminal / cf_other = end of a "
            "constituent inside the clause (after the first constituent / before the last / before two or more); list_item = "
            "end of a list item; not_cf = not at the end of a constituent. All but not_cf are possible pausal positions.")
table("Position (hand-coded) × complement", ct(mp, ["R_pos", "complement"]), POS_NOTE)
mp["pausal_position"] = mp.main_div.map({1: "pausal position", 0: "other"})
PP_NOTE = ("pausal position = end of the clause, or the main division of the clause, "
           "judged from syntax and the accent hierarchy. Note that this reintroduces the accents.")
table("Pausal position × complement", ct(mp, ["pausal_position", "complement"]), PP_NOTE)
fit_pos = ((mp.pausal_position == "pausal position") == (mp.vowel == "qoṭelā")).sum()
fit_com = ((mp.complement == "none") == (mp.vowel == "qoṭelā")).sum()
out.append("## Position and complement as predictors (all 46 forms)\n")
out.append(f"- pausal position → qoṭelā, other → qoṭlā: {fit_pos} of {len(mp)} fit.")
out.append(f"- no complement → qoṭelā, complement → qoṭlā: {fit_com} of {len(mp)} fit.")
out.append(f"- the two predictors agree on {((mp.pausal_position == 'pausal position') == (mp.complement == 'none')).sum()} of {len(mp)} forms.\n")
fisher(mp, mp.pausal_position == "pausal position", "pausal position × vowel")
fisher(mp, mp.complement == "none", "no complement × vowel")
table("Sensitivity: without the forms coded as ambiguous", ct(mp[mp.ambiguous == 0], ["pausal_position", "complement"]))
cols = ["ref", "word", "accents", "R_pos", "pausal_position", "int_syntax", "vowel", "note_y"]
table("Forms that do not fit pausal position",
      mp[(mp.pausal_position == "pausal position") != (mp.vowel == "qoṭelā")][cols].fillna("").set_index("ref"))

fit_c = ((o.complement == "complement") == (o.vowel == "qoṭlā")).sum()
fit_f = ((o.ext_function != "substantival") == (o.vowel == "qoṭlā")).sum()
out.append("## Two predictors compared (outside major pause)\n")
out.append(f"- complement → qoṭlā, none → qoṭelā: {fit_c} of {len(o)} fit.")
out.append(f"- substantival → qoṭelā, other → qoṭlā: {fit_f} of {len(o)} fit.")
out.append("- The two are nested: every substantival form lacks a complement. They cannot be ranked with these data.\n")
fisher(o, o.complement == "complement", "complement × vowel outside major pause")
fisher(o, o.ext_function == "substantival", "substantival vs other × vowel outside major pause")
ns = o[o.ext_function != "substantival"]
fisher(ns, ns.complement == "complement", "complement × vowel, non-substantival forms only")

table("Spelling visible on the coding sheet (leak check)", ct(m, ["plene"]),
      "The unpointed sheet still shows ו after the first radical; it correlates with the vowel.")

misfit = o[(o.complement == "complement") != (o.vowel == "qoṭlā")]
cols = ["ref", "word", "accents", "ext_function", "int_syntax", "II_gem", "vowel", "note"]
table("Forms that do not fit the complement tendency (outside major pause)", misfit[cols].fillna("").set_index("ref"))

# Hos 7:4 בֹּעֵרָה: feminine participle after masculine תַּנּוּר, probably a corrupt text (second critique, 2026-10-11)
HOS = "Hosea 7:4"
out.append("## Sensitivity: without Hos 7:4 (text doubtful)\n")
for label, df in [("all forms", mp), ("outside major pause", o)]:
    d = df[df.ref != HOS]
    fit = ((d.complement == "none") == (d.vowel == "qoṭelā")).sum()
    out.append(f"- no complement → qoṭelā, complement → qoṭlā, {label}: {fit} of {len(d)} fit.")
out.append("")

# Stich position: in poetry, pausal forms mark stich ends and are not used within stichs.
# Poetic forms: two coders (stich_coding_A = Claude, vowel known; stich_coding_B = separate agent, consonantal sheet only),
# consensus in stich_coding.csv. Prose forms keep the position coding (clause end or main division).
sc = pd.read_csv(os.path.join(ROOT, "data", "coding", "stich_coding.csv"))
ms = mp.merge(sc[["node", "code_A", "code_B", "final", "ambiguous_final", "alternative_final"]], on="node", how="left")
ms["stich_pos"] = ms.final.map({"stich_end": "pausal position", "subunit_end": "other", "internal": "other"})
ms.loc[ms.final.isna(), "stich_pos"] = ms.pausal_position  # prose
out.append("## Stich position for the poetic forms\n")
both = ms.dropna(subset=["code_A", "code_B"])
agree = ((both.code_A == "stich_end") == (both.code_B == "stich_end")).sum()
out.append(f"- poetic forms: {len(both)}; the two coders agree on stich end vs not in {agree} of {len(both)}.")
table("Stich position (poetry) or clause position (prose) × complement", ct(ms, ["stich_pos", "complement"]),
      "Poetry: pausal position = end of a stich (consensus coding). Prose (7 forms): end or main division of the clause.")
for label, d in [("all 46 forms", ms), ("outside major pause", ms[ms.pause != "major"]),
                 ("without Hos 7:4", ms[ms.ref != HOS]), ("without the forms coded ambiguous", ms[ms.ambiguous_final != 1])]:
    fs = ((d.stich_pos == "pausal position") == (d.vowel == "qoṭelā")).sum()
    fc = ((d.complement == "none") == (d.vowel == "qoṭelā")).sum()
    ag = ((d.stich_pos == "pausal position") == (d.complement == "none")).sum()
    out.append(f"- {label}: stich/clause position fits {fs} of {len(d)}; complement fits {fc} of {len(d)}; they agree on {ag}.")
alt = ms.copy()
flip = alt.alternative_final.notna() & (alt.ambiguous_final == 1)
alt.loc[flip, "stich_pos"] = alt.loc[flip, "alternative_final"].map(
    {"stich_end": "pausal position", "subunit_end": "other", "internal": "other"})
fs = ((alt.stich_pos == "pausal position") == (alt.vowel == "qoṭelā")).sum()
out.append(f"- every ambiguous form recoded to its alternative: stich/clause position fits {fs} of {len(alt)}.\n")
fisher(ms, ms.stich_pos == "pausal position", "stich position × vowel")
ok_s = (ms.stich_pos == "pausal position") == (ms.vowel == "qoṭelā")
ok_c = (ms.complement == "none") == (ms.vowel == "qoṭelā")
only_c, only_s = int((ok_c & ~ok_s).sum()), int((ok_s & ~ok_c).sum())
out.append(f"- paired comparison: both fit {int((ok_s & ok_c).sum())}, neither {int((~ok_s & ~ok_c).sum())}; only the complement "
           f"fits {only_c} ({', '.join(ms[ok_c & ~ok_s].ref)}); only stich position fits {only_s} ({', '.join(ms[ok_s & ~ok_c].ref)}).")
out.append(f"- exact McNemar (binomial) test on the {only_c + only_s} discordant forms: "
           f"p = {binomtest(only_c, only_c + only_s).pvalue:.3f}. Forms are not fully independent (repeated formulae).")
nj = ms.lex != "JLD["
c1, s1 = int((ok_c & ~ok_s & nj).sum()), int((ok_s & ~ok_c & nj).sum())
out.append(f"- without יוֹלֵדָה ({int((~nj).sum())} forms): only the complement fits {c1}, only stich position {s1}; "
           f"p = {binomtest(c1, c1 + s1).pvalue:.3f}; fits {int((ok_s & nj).sum())} vs {int((ok_c & nj).sum())} of {int(nj.sum())}.")
rg = ms.repeat_group.fillna(ms.node.astype(str))
first = ~rg.duplicated()
c2, s2 = int((ok_c & ~ok_s & first).sum()), int((ok_s & ~ok_c & first).sum())
out.append(f"- one form per repeat_group (phrase groups, not lines; the כיולדה formula is not grouped; {int(first.sum())} forms): "
           f"only the complement fits {c2}, only stich position {s2}; p = {binomtest(c2, c2 + s2).pvalue:.3f}.")
out.append(f"- lexemes among the forms only the complement fits: {ms[ok_c & ~ok_s].lex.nunique()}.\n")


def compare(d, label):
    s_ok = (d.stich_pos == "pausal position") == (d.vowel == "qoṭelā")
    c_ok = (d.complement == "none") == (d.vowel == "qoṭelā")
    a, b = int((c_ok & ~s_ok).sum()), int((s_ok & ~c_ok).sum())
    p = binomtest(a, a + b).pvalue if a + b else float("nan")
    out.append(f"- {label}: stich/clause position fits {int(s_ok.sum())} of {len(d)}, complement {int(c_ok.sum())}; "
               f"discordant {a} (complement only) vs {b} (position only), p = {p:.2f}.")


out.append("## Stich position: subsets and coding models (review 2026-10-11)\n")
out.append(f"- substantival forms: {int((ms.ext_function == 'substantival').sum())}, all qoṭelā: "
           f"{bool((ms[ms.ext_function == 'substantival'].vowel == 'qoṭelā').all())}; lexemes "
           f"{ms[ms.ext_function == 'substantival'].lex.nunique()}. A substantival form has no complement by definition.")
compare(ms[ms.ext_function != "substantival"], "non-substantival forms")
compare(ms[ms.final.notna()], "poetry only")
compare(ms[(ms.final.notna()) & (ms.ext_function != "substantival")], "poetry, non-substantival")
compare(ms[~ms.II_gem], "without II-gem forms")
compare(ms[(~ms.II_gem) & (ms.lex != "JLD[")], "without II-gem forms and יוֹלֵדָה")
P = "pausal position"
# Three-Books model: a colon boundary inside a half-verse is a sub-unit end; affects the
# qoṭelā forms on minor disjunctives coded stich_end in the Prophets
TB = ["Isaiah 33:14", "Jeremiah 30:6", "Micah 4:6", "Zephaniah 3:19"]
tb = ms.copy()
tb.loc[tb.ref.isin(TB), "stich_pos"] = "other"
compare(tb, "Three-Books model (Isa 33:14; Jer 30:6; Mic 4:6; Zeph 3:19 as sub-unit ends)")
rv = ms.copy()
rv.loc[rv.ref == "Jeremiah 12:12", "stich_pos"] = "other"   # Ps 79:3 pattern: clause + adverbial = one stich
rv.loc[rv.ref == "Lamentations 1:13", "stich_pos"] = P       # qinah caesura as stich end
compare(rv, "Jer 12:12 as sub-unit end and Lam 1:13 as stich end (reviewer's coding)")
best = rv.copy()
best.loc[best.ref.isin(["Hosea 4:16", "Hosea 7:4"]), "stich_pos"] = P
compare(best, "best case for position (also Hos 4:16; 7:4 as stich ends)")
worst = ms.copy()
worst.loc[worst.ref.isin(["Isaiah 30:30", "Micah 4:6", "Zephaniah 3:19"]), "stich_pos"] = "other"
compare(worst, "worst case for position (Isa 30:30; Mic 4:6; Zeph 3:19 as sub-unit ends)")
out.append(f"- ṣere forms outside pausal position (consensus coding): {', '.join(ms[(ms.stich_pos != P) & (ms.vowel == 'qoṭelā')].ref)}.\n")
cols = ["ref", "word", "accents", "final", "code_A", "code_B", "int_syntax", "ext_function", "vowel"]
table("Forms that do not fit stich position", ms[(ms.stich_pos == "pausal position") != (ms.vowel == "qoṭelā")][cols]
      .fillna("").set_index("ref"))
table("Poetic forms inside a stich with ṣere", ms[(ms.final.isin(["internal", "subunit_end"])) & (ms.vowel == "qoṭelā")]
      [cols].fillna("").set_index("ref"))

s = allm[allm.pause != "major"]
table("Sensitivity: with the three forms of שׁוֹבֵב (all 49 forms)", ct(allm, ["pause"]))
table("Sensitivity: with שׁוֹבֵב, outside major pause, function × complement", ct(s, ["ext_function", "complement"]))

cols = ["ref", "word", "accents", "pause", "clause_final", "ext_function", "int_syntax", "lexicalization", "II_gem", "vowel", "note"]
table("All forms (including שׁוֹבֵב)", allm.sort_values(["vowel", "pause", "ext_function"])[cols].fillna("").set_index("ref"))

with open(os.path.join(ROOT, "data", "qal_h_tables.md"), "w", encoding="utf-8") as fh:
    fh.write("# Qal fsg participles in ה: vowel by pause, function and syntax\n\n" + "\n".join(out))
print("written data/qal_h_tables.md")
