"""Compare the feminine singular participles of the MT Pentateuch with the Samaritan Pentateuch (SP).

The SP corpus (dt-ucph/sp, Text-Fabric) is consonantal; it has no stem feature and no vocalization.
Alignment works in both directions:
  1. every MT fsg participle in Genesis-Deuteronomy (data/mt_fsg_participles.csv, from extract_mt.py)
     is matched with the SP word(s) of the same lexeme in the same verse;
  2. every SP word tagged as fsg participle that has no MT fsg participle partner is added as an SP-only row.

Output: data/sp_fsg_participles.csv.
Run from the project root (after extract_mt.py):  python scripts/extract_sp.py
"""
import csv
import glob
import os

from tf.fabric import Fabric

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MT = os.path.join(ROOT, "data", "mt_fsg_participles.csv")
OUT = os.path.join(ROOT, "data", "sp_fsg_participles.csv")
SP = sorted(glob.glob(os.path.expanduser("~/text-fabric-data/dt-ucph/sp/tf/*")))[-1]
TORAH = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"]
LETTER = {"H": "H", "T": "T", ">": "A", "J": "Y"}


def ending(cons, prs):
    if prs not in (None, "", "absent", "n/a"):
        return "suffix"
    return LETTER.get(cons[-1:], "other") if cons else "?"


def main():
    TF = Fabric(locations=SP, silent="deep")
    api = TF.load("g_cons g_cons_utf8 lex vt gn nu g_prs mt_feat", silent="deep")
    F, L, T = api.F, api.L, api.T

    sp_by_key = {}
    for w in F.otype.s("word"):
        book, ch, vs_ = T.sectionFromNode(w)
        sp_by_key.setdefault((book, str(ch), str(vs_), F.lex.v(w)), []).append(w)

    def sp_info(w):
        cons = F.g_cons.v(w) or ""
        return {
            "sp_word": F.g_cons_utf8.v(w), "sp_cons": cons,
            "sp_parse": f"{F.vt.v(w)} {F.gn.v(w)}{F.nu.v(w)}",
            "sp_ending": ending(cons, F.g_prs.v(w)),
            "sp_mt_aligned": F.mt_feat.v(w) or "",
        }

    rows, used = [], set()
    with open(MT, encoding="utf-8-sig") as fh:
        mt_rows = [r for r in csv.DictReader(fh) if r["book"] in TORAH]
    for r in mt_rows:
        cands = sp_by_key.get((r["book"], r["chapter"], r["verse"], r["lex"]), [])
        cands = [w for w in cands if w not in used]
        # prefer an SP word tagged as fsg participle, then any participle, then any form of the lexeme
        cands.sort(key=lambda w: (not (F.vt.v(w) in ("ptca", "ptcp") and F.gn.v(w) == "f" and F.nu.v(w) == "sg"),
                                  F.vt.v(w) not in ("ptca", "ptcp")))
        w = cands[0] if cands else None
        if w is not None:
            used.add(w)
        row = {
            "source": "MT+SP" if w is not None else "MT only",
            "book": r["book"], "chapter": r["chapter"], "verse": r["verse"],
            "lex": r["lex"], "stem": r["stem"], "vt": r["vt"], "state": r["state"],
            "root_class": r["root_class"], "mt_word": r["word"], "mt_qere": r["qere"],
            "mt_ending": r["ending"], "mt_form_subtype": r["form_subtype"], "mt_pause": r["pause"],
            "mt_role": r["role"], "mt_function": r["phrase_function"],
        }
        row.update(sp_info(w) if w is not None else
                   {"sp_word": "", "sp_cons": "", "sp_parse": "", "sp_ending": "", "sp_mt_aligned": ""})
        rows.append(row)

    for w in F.otype.s("word"):
        if w in used or F.vt.v(w) not in ("ptca", "ptcp") or F.gn.v(w) != "f" or F.nu.v(w) != "sg":
            continue
        book, ch, vs_ = T.sectionFromNode(w)
        row = {"source": "SP only", "book": book, "chapter": ch, "verse": vs_, "lex": F.lex.v(w),
               "stem": "", "vt": F.vt.v(w), "state": "", "root_class": "", "mt_word": "", "mt_qere": "",
               "mt_ending": "", "mt_form_subtype": "", "mt_pause": "", "mt_role": "", "mt_function": ""}
        row.update(sp_info(w))
        rows.append(row)

    # second pass: pair an unmatched MT row with an SP-only row in the same verse
    # (covers lexemes spelled differently in the two databases, e.g. MT M>R[ vs SP MR>[)
    mt_only = [r for r in rows if r["source"] == "MT only"]
    sp_only = [r for r in rows if r["source"] == "SP only"]
    for r in mt_only:
        for s_ in sp_only:
            if (s_["book"], str(s_["chapter"]), str(s_["verse"])) == (r["book"], r["chapter"], r["verse"]):
                for k in ("sp_word", "sp_cons", "sp_parse", "sp_ending", "sp_mt_aligned"):
                    r[k] = s_[k]
                r["source"] = "MT+SP (lexeme differs)"
                sp_only.remove(s_)
                rows.remove(s_)
                break

    with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print(len(rows), "rows written to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
