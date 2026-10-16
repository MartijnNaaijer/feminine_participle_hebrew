"""Extract all Hebrew feminine singular participles (all stems) from the Dead Sea Scrolls (ETCBC/dss).

Output: data/dss_fsg_participles.csv, one row per occurrence.
Biblical manuscripts are aligned with the MT (BHSA, loaded directly) on book/chapter/verse
and ETCBC lexeme.

Requires Text-Fabric and ETCBC/dss version 2.0.1 in ~/text-fabric-data/github/ETCBC/dss/tf/2.0.1.
Run from the project root:  python scripts/extract_dss.py
"""
import csv
import os
import sys

from tf.fabric import Fabric

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_mt import BHSA, accents, form_type, pause_level, root_class  # noqa: E402

DSS = os.path.expanduser("~/text-fabric-data/github/ETCBC/dss/tf/2.0.1")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "data", "dss_fsg_participles.csv")

FEATURES = ("glyph full lex lex_etcbc vs vt gn nu st morpho scroll biblical book_etcbc chapter verse "
            "fragment line lang rec unc cor rem g_prs_etcbc")

FINALS = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}


def letters(glyph):
    """Consonants of a DSS glyph string (drops diacritics, brackets and other marks)."""
    return [FINALS.get(c, c) for c in glyph if "א" <= c <= "ת"]


def load_mt():
    """All MT words keyed by (book, chapter, verse, lex), with their analysis.

    Every word of the lexeme in the verse is used, not only words tagged as fsg participle,
    because BHSA sometimes analyses the parallel form differently (e.g. as a perfect)."""
    TF = Fabric(locations=BHSA, silent="deep")
    api = TF.load("g_word g_word_utf8 lex vs vt gn nu st prs", silent="deep")
    F, L, T = api.F, api.L, api.T
    mt = {}
    for w in F.otype.s("word"):
        book, ch, vs_ = T.sectionFromNode(w)
        vwords = L.d(L.u(w, "verse")[0], "word")
        ending, sub = form_type(F.g_word.v(w), F.prs.v(w))
        acc = accents(F.g_word_utf8.v(w))
        mt.setdefault((book, str(ch), str(vs_), F.lex.v(w)), []).append({
            "word": F.g_word_utf8.v(w),
            "parse": f"{F.vs.v(w)} {F.vt.v(w)} {F.gn.v(w)}{F.nu.v(w)}",
            "ending": ending, "form_subtype": sub,
            "pause": pause_level(acc, w == vwords[-1], book),
        })
    return mt


def main():
    TF = Fabric(locations=DSS, silent="deep")
    api = TF.load(FEATURES, silent="deep")
    F, L = api.F, api.L
    mt = load_mt()

    rows = []
    for w in F.otype.s("word"):
        if F.vt.v(w) not in ("ptca", "ptcp") or F.gn.v(w) != "f" or F.nu.v(w) != "s":
            continue
        if F.lang.v(w):  # 'a' = Aramaic; None = Hebrew
            continue
        signs = [s for s in L.d(w, "sign") if "א" <= (F.glyph.v(s) or " ")[:1] <= "ת"]
        cons = letters(F.glyph.v(w) or "")
        suffix = F.g_prs_etcbc.v(w) not in (None, "", "NA") or "X" in (F.morpho.v(w) or "")
        last = signs[-1] if signs else None
        if last is None:
            status = "missing"
        elif F.rec.v(last):
            status = "reconstructed"
        elif F.unc.v(last):
            status = "uncertain"
        else:
            status = "ok"
        if suffix:
            ending = "suffix"
        elif not cons:
            ending = "?"
        else:
            ending = {"ה": "H", "ת": "T", "א": "A", "י": "Y"}.get(cons[-1], "other")
        lexe = F.lex_etcbc.v(w) or ""
        stem, vt = F.vs.v(w), F.vt.v(w)
        # letters other than the last that are reconstructed or uncertain (affects identification and plene counts)
        damaged = [bool(F.rec.v(x) or F.unc.v(x)) for x in signs]
        n_damaged_other = sum(damaged[:-1])
        second_damaged = int(len(damaged) > 1 and damaged[1])
        # plene spelling of the o-vowel after the first radical (qal active qoṭel pattern)
        plene_o = int(stem == "qal" and vt == "ptca" and len(cons) >= 3 and cons[1] == "ו")
        biblical = bool(F.biblical.v(w))
        book, ch, vs_ = F.book_etcbc.v(w) or "", F.chapter.v(w) or "", F.verse.v(w) or ""
        mt_match = mt.get((book, str(ch), str(vs_), lexe), []) if biblical else []
        if len(mt_match) > 1:  # prefer MT participles if the lexeme occurs more than once
            ptc = [r for r in mt_match if " ptc" in r["parse"]]
            mt_match = ptc or mt_match
        prev_w, next_w = w - 1, w + 1
        line = L.u(w, "line")[0]
        lwords = L.d(line, "word")
        rows.append({
            "node": w,
            "scroll": F.scroll.v(L.u(w, "scroll")[0]),
            "fragment": F.fragment.v(L.u(w, "fragment")[0]),
            "line": F.line.v(line),
            "biblical": int(biblical),
            "book": book, "chapter": ch, "verse": vs_,
            "glyph": F.glyph.v(w), "full": F.full.v(w),
            "lex": F.lex.v(w), "lex_etcbc": lexe,
            "stem": stem, "vt": vt, "state": F.st.v(w) or "", "morpho": F.morpho.v(w),
            "root_class": root_class(lexe) if lexe else "?",
            "ending": ending, "last_letter": status,
            "plene_o": plene_o,
            "n_damaged_other": n_damaged_other, "second_letter_damaged": second_damaged,
            "prev_word": F.glyph.v(prev_w) if prev_w in lwords else "",
            "next_word": F.glyph.v(next_w) if next_w in lwords else "",
            "line_text": " ".join(F.glyph.v(x) or "" for x in lwords),
            "mt_word": " | ".join(r["word"] for r in mt_match),
            "mt_ending": " | ".join(r["ending"] for r in mt_match),
            "mt_form_subtype": " | ".join(r["form_subtype"] for r in mt_match),
            "mt_pause": " | ".join(r["pause"] for r in mt_match),
            "mt_parse": " | ".join(r["parse"] for r in mt_match),
        })
    with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print(len(rows), "rows written to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
