"""Ending (ה vs ת) of the qal fsg participle of non-weak roots: book group, prose/poetry, lexeme.

Writes data/ending_tables.md. Run from the project root:  python scripts/analyse_ending.py

The prose/poetry classification is our own judgement, following the layout of BHS
(poems set as verse). It is a coarse two-way split; "uncertain" marks passages whose
layout or genre is disputed.
"""
import os

import pandas as pd

from mdtable import to_md

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
d = pd.read_csv(os.path.join(ROOT, "data", "mt_fsg_participles.csv"))
absol = d[(d.state == "a") & d.ending.isin(["H", "T"])]
weak = absol.root_class.str.contains(r"III-y|II-w/y$|II-w/y,|II-w/y \(")
q = absol[(absol.stem == "qal") & (absol.vt == "ptca") & (absol.pattern_first_vowel == "holam") & ~weak].copy()

POETRY_BOOKS = {"Psalms", "Proverbs", "Job", "Song_of_songs", "Lamentations", "Isaiah", "Jeremiah", "Hosea",
                "Joel", "Amos", "Obadiah", "Micah", "Nahum", "Habakkuk", "Zephaniah"}
# poems inside prose books (book, chapter, first verse, last verse)
POEMS = [("Genesis", 49, 2, 27), ("Exodus", 15, 1, 18), ("Numbers", 21, 17, 18), ("Numbers", 21, 27, 30),
         ("Numbers", 23, 7, 10), ("Numbers", 23, 18, 24), ("Numbers", 24, 3, 9), ("Numbers", 24, 15, 24),
         ("Deuteronomy", 32, 1, 43), ("Deuteronomy", 33, 2, 29), ("Judges", 5, 1, 31), ("1_Samuel", 2, 1, 10),
         ("2_Samuel", 1, 19, 27), ("2_Samuel", 22, 1, 51), ("2_Samuel", 23, 1, 7)]
# prose passages inside "poetic" prophetic books, as far as they contain our forms
PROSE = [("Isaiah", 7, 1, 25), ("Isaiah", 36, 1, 22), ("Isaiah", 37, 1, 38), ("Isaiah", 38, 1, 8),
         ("Isaiah", 39, 1, 8), ("Jeremiah", 3, 6, 18)]
UNCERTAIN = [("Ezekiel", 17, 1, 10), ("Ezekiel", 21, 13, 22)]


def inside(r, spans):
    return any(r.book == b and r.chapter == c and v1 <= r.verse <= v2 for b, c, v1, v2 in spans)


def genre(r):
    if inside(r, UNCERTAIN):
        return "uncertain"
    if inside(r, PROSE):
        return "prose"
    if inside(r, POEMS) or r.book in POETRY_BOOKS:
        return "poetry"
    return "prose"


q["genre"] = [genre(r) for r in q.itertuples()]
q["prophetic"] = q.book_group.isin(["Major Prophets", "Minor Prophets"]).map({True: "Latter Prophets", False: "other books"})
out = []


def ct(df, rows):
    g = df.groupby(rows + ["ending"]).agg(tokens=("lex", "size"), types=("lex", "nunique")).unstack(fill_value=0)
    g.columns = [f"{e} {k}" for k, e in g.columns]
    return g[[c for c in ("H tokens", "H types", "T tokens", "T types") if c in g]]


def table(title, df, note=""):
    out.append(f"## {title}\n")
    if note:
        out.append(note + "\n")
    out.append(to_md(df))
    out.append("")


table("By book group", ct(q, ["book_group"]), f"{len(q)} qal active fsg participles of non-weak roots (absolute state).")
table("By prose/poetry and book group", ct(q, ["prophetic", "genre"]))
noj = q[q.lex != "JLD["]
table("Without יָלַד", ct(noj, ["prophetic", "genre"]), f"Removes {len(q) - len(noj)} forms of יָלַד ({(q[q.lex == 'JLD['].ending == 'H').sum()} in ה).")
nojq = noj[noj.lex != "QHLT/"]
table("Without יָלַד and קֹהֶלֶת (a title)", ct(nojq, ["prophetic", "genre"]))
table("Most frequent lexemes in ה", q[q.ending == "H"].groupby("lex").size().sort_values(ascending=False).head(8).to_frame("tokens"))

q["predicate_phrase"] = q.phrase_function.isin(["PreC", "PtcO", "PreO", "PreS", "PrAd"]).map({True: "predicate phrase", False: "other phrase"})
table("Ending by genre and phrase function (preliminary)", ct(q, ["genre", "predicate_phrase"]),
      "BHSA `function` is a phrase-level feature: a participle inside a predicate noun phrase (אֵשׁ אֹכְלָה "
      "in 'he is a consuming fire') counts as 'predicate phrase'. Word-level coding of the ת forms is still to be done.")
qj = q[q.lex != "JLD["]
table("The same, without יָלַד", ct(qj, ["genre", "predicate_phrase"]))

both = q.groupby("lex").ending.nunique()
lex2 = q[q.lex.isin(both[both > 1].index)].sort_values("node")
lex2 = lex2.assign(ref=lex2.book.str.replace("_", " ") + " " + lex2.chapter.astype(str) + ":" + lex2.verse.astype(str))
table("Lexemes with both endings", lex2[["lex", "ref", "word", "ending", "genre", "pause", "role"]].set_index("ref"))

with open(os.path.join(ROOT, "data", "ending_tables.md"), "w", encoding="utf-8") as fh:
    fh.write("# Qal fsg participle of non-weak roots: ה vs ת\n\n" + "\n".join(out))
print("written data/ending_tables.md")


# Ending × hand-coded syntax within poetry (ה forms: data/coding/qal_h_coding.csv; ת forms: data/coding/poetry_T_coding.csv)
from scipy.stats import fisher_exact  # noqa: E402
from scipy.stats.contingency import odds_ratio  # noqa: E402

codes = pd.concat([pd.read_csv(os.path.join(ROOT, "data", "coding", f)) for f in ("qal_h_coding.csv", "poetry_T_coding.csv")])
pq = q[q.genre == "poetry"].merge(codes, on="node", how="left")
assert pq.ext_function.notna().all(), "uncoded poetry form"
pq["complement"] = pq.int_syntax.map(lambda x: "none" if x == "none" else "complement")
pq["repeat_group"] = pq.repeat_group.fillna("")
noj = pq[pq.lex != "JLD["]
once = pd.concat([noj[noj.repeat_group == ""], noj[noj.repeat_group != ""].drop_duplicates("repeat_group")])
out2 = []


def ct2(df, rows):
    g = df.groupby(rows + ["ending"]).agg(tokens=("lex", "size"), types=("lex", "nunique")).unstack(fill_value=0)
    g.columns = [f"{e} {k}" for k, e in g.columns]
    return g[[c for c in ("H tokens", "H types", "T tokens", "T types") if c in g]]


for title, df in [("Poetry: ending × external function", ct2(pq, ["ext_function"])),
                  ("Poetry: ending × complement", ct2(pq, ["complement"])),
                  ("Poetry: ending × function × complement", ct2(pq, ["ext_function", "complement"])),
                  ("Poetry without יָלַד, repeated lines counted once: ending × function × complement",
                   ct2(once, ["ext_function", "complement"])),
                  ("Poetry, Latter Prophets only: ending × function × complement",
                   ct2(pq[pq.prophetic == "Latter Prophets"], ["ext_function", "complement"]))]:
    out2.append(f"## {title}" + chr(10))
    out2.append(to_md(df))
    out2.append("")
out2.append("## Tests (complement = object, prepositional complement or adverbial of the participle itself)" + chr(10))
out2.append("| subset | n | ה with complement | ת with complement | Fisher p | odds ratio (95% CI) | predicative ה / ת | Fisher p |")
out2.append("|---|---|---|---|---|---|---|---|")
for label, sub in [("all poetry", pq), ("without יָלַד", noj), ("without יָלַד, repeated lines once", once),
                   ("without יָלַד and without phrases coded fixed", noj[noj.lexicalization != "fixed"])]:
    tab = pd.crosstab(sub.ending, sub.complement == "complement").reindex(index=["H", "T"], columns=[True, False], fill_value=0)
    res = odds_ratio(tab.values)
    ci = res.confidence_interval()
    p_c = fisher_exact(tab.values)[1]
    tabp = pd.crosstab(sub.ending, sub.ext_function == "predicative").reindex(index=["H", "T"], columns=[True, False], fill_value=0)
    p_p = fisher_exact(tabp.values)[1]
    h, t_ = tab.loc["H"], tab.loc["T"]
    out2.append(f"| {label} | {len(sub)} | {h[True]}/{h.sum()} | {t_[True]}/{t_.sum()} | {p_c:.3f} | "
                f"{res.statistic:.2f} ({ci.low:.2f}–{ci.high:.2f}) | {tabp.loc['H', True]}/{h.sum()} / {tabp.loc['T', True]}/{t_.sum()} | {p_p:.3f} |")
with open(os.path.join(ROOT, "data", "ending_tables.md"), "a", encoding="utf-8") as fh:
    fh.write(chr(10) + "# Hand-coded syntax within poetry" + chr(10)*2 + "One coder; the ending was visible while coding the ת forms. "
             "Repeated lines (same phrase in parallel or refrain passages) are listed in the column repeat_group of the coding files." + chr(10)*2
             + chr(10).join(out2) + chr(10))
print("appended hand-coded poetry tables")
