"""Extract all feminine singular participles (all stems) from the BHSA (MT, Codex Leningradensis).

Output: data/mt_fsg_participles.csv, one row per occurrence, with morphological,
form-type, accent/pause and syntactic annotations.

Requires Text-Fabric and the BHSA data (version 2021) in ~/text-fabric-data/etcbc/bhsa/tf/2021.
Run from the project root:  python scripts/extract_mt.py
"""
import csv
import os
import re
import unicodedata

from tf.fabric import Fabric

BHSA = os.path.expanduser("~/text-fabric-data/etcbc/bhsa/tf/2021")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "mt_fsg_participles.csv")

FEATURES = (
    "g_word g_word_utf8 lex voc_lex_utf8 gloss sp vs vt gn nu st prs pdp "
    "language qere_utf8 function typ rela txt domain det"
)

BOOK_GROUP = {
    **dict.fromkeys(["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"], "Torah"),
    **dict.fromkeys(["Joshua", "Judges", "1_Samuel", "2_Samuel", "1_Kings", "2_Kings"], "Former Prophets"),
    **dict.fromkeys(["Isaiah", "Jeremiah", "Ezekiel"], "Major Prophets"),
    **dict.fromkeys(["Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
                     "Zephaniah", "Haggai", "Zechariah", "Malachi"], "Minor Prophets"),
    **dict.fromkeys(["Psalms", "Job", "Proverbs"], "Poetry (Ps/Job/Prov)"),
    **dict.fromkeys(["Ruth", "Song_of_songs", "Ecclesiastes", "Lamentations", "Esther"], "Megillot"),
    **dict.fromkeys(["Daniel", "Ezra", "Nehemiah", "1_Chronicles", "2_Chronicles"], "Late prose"),
}

# Lexemes that BHSA tags as adjective/noun but that are formally qal active fsg participles
# (found by a pattern search for qoṭel-type feminine forms outside the verb tagging).
LEXICALIZED_QAL_PTC = {
    "CWBB/": "CBB[",   # שׁוֹבֵבָה / שׁוֹבְבָה 'backsliding': adjective שׁוֹבָב, reduplicated from שׁוב
    "CWQQ/": "CQQ[",   # שׁוֹקֵקָה 'thirsty, longing' (Isa 29:8; Ps 107:9), root שׁקק (II-gem)
    "XBRT/": "XBR[",   # חֹבֶרֶת 'that which couples' (Exod 26; 36)
    "QHLT/": "QHL[",   # קֹהֶלֶת 'Qohelet'
}
# Root-class labels for the lexicalized forms (the pseudo-root above only drives the generic classifier)
LEXICALIZED_ROOT_CLASS = {"CWBB/": "II-w/y (reduplicated adjective)"}
# tagged fsg in BHSA but masculine: Lev 7:9 נַעֲשָׂה
EXCLUDE = {("Leviticus", 7, 9, "<FH[")}

CONSONANTS = set("BGDHWZXVJKLMNSPYQRFCT<>")
GUTTURALS = set(">HX<")  # ETCBC transliteration: alef, he, het, ayin

VOWEL = {":A": "hatef patah", ":E": "hatef segol", ":@": "hatef qamets",
         ":": "shewa", ";": "sere", "E": "segol", "A": "patah", "@": "qamets",
         "I": "hireq", "O": "holam", "U": "qibbuts"}


def accents(word_utf8):
    """Unicode names of the accents (and meteg) on a pointed word."""
    out = []
    for ch in word_utf8:
        if unicodedata.category(ch) == "Mn":
            n = unicodedata.name(ch, "")
            if "ACCENT" in n or n == "HEBREW POINT METEG":
                out.append(n.replace("HEBREW ACCENT ", "").replace("HEBREW POINT ", "").lower())
    return out


def groups(g_word):
    """Split an ETCBC g_word transliteration into [consonant, marks] groups (accent digits removed)."""
    s = re.sub(r"[0-9]", "", g_word)
    s = re.sub(r"[*&\-]", "", s)
    out = []
    for ch in s:
        if ch in CONSONANTS:
            out.append([ch, ""])
        elif out:
            out[-1][1] += ch.replace(".", "")
    return out, s


def vname(marks):
    for k in (":A", ":E", ":@", ":", ";", "E", "A", "@", "I", "O", "U"):
        if k in marks:
            return VOWEL[k]
    return "none"


def form_type(g_word, prs):
    """Classify the feminine ending and the vowel pattern before it.

    ending: 'H' (-ā, written ה), 'T' (-t), 'suffix' (pronominal suffix attached), 'other'.
    subtype for H: vowel under the consonant before the last radical
                   (shewa/hatef = reduced, qoṭlā type; sere = full, qoṭelā type; others listed).
    subtype for T: 'segolate' (two short vowels before t, e.g. -eCet, -aCat, -āCet),
                   'Ct' (consonant + t, qoṭalt type), 'Vt' (vowel + t, e.g. III-alef yoṣēt).
    """
    grp, s = groups(g_word)
    if prs and prs not in ("absent", "n/a"):
        return "suffix", ""
    if s.endswith("@H") and len(grp) >= 3:
        return "H", vname(grp[-3][1])
    if grp and grp[-1][0] == "T":
        prev = grp[-2] if len(grp) >= 2 else ["", ""]
        prev2 = grp[-3] if len(grp) >= 3 else ["", ""]
        vprev, vprev2 = vname(prev[1]), vname(prev2[1])
        if vprev in ("segol", "patah"):
            return "T", "segolate:" + vprev2 + "-" + vprev
        if vprev in ("shewa",):
            return "T", "Ct:" + vprev2
        if vprev == "none":
            return "T", "Vt:" + vprev2
        return "T", "other:" + vprev2 + "-" + vprev
    return "other", s


def root_class(lex):
    rad = re.sub(r"[\[/=]", "", lex)
    rc = []
    if len(rad) != 3:
        return "non-triliteral"
    if rad[2] == "H":
        rc.append("III-y")
    if rad[2] == ">":
        rc.append("III-alef")
    if rad[2] in "X<":
        rc.append("III-gutt")
    if rad[1] in "WJ":
        rc.append("II-w/y")
    if rad[1] == rad[2]:
        rc.append("II-gem")
    if rad[0] in GUTTURALS:
        rc.append("I-gutt")
    if rad[0] == "N":
        rc.append("I-n")
    if rad[0] in "JW":
        rc.append("I-y/w")
    if rad[1] in GUTTURALS or rad[1] == "R":
        rc.append("II-gutt/r")
    return ",".join(rc) or "strong"


POETIC_ACCENT_BOOKS = {"Psalms", "Proverbs", "Job"}  # Job 3:2-42:6 strictly; whole book used here
MINOR_DISJ = {"dehi", "zaqef qatan", "zaqef gadol", "segol", "revia", "tipeha", "pashta", "yetiv",
              "tevir", "zarqa", "pazer", "geresh", "gershayim", "qarney para", "telisha gedola"}


def pause_level(acc, verse_final, book):
    """'major' = silluq (verse end), atnah, or (poetic books) oleh-we-yored;
    'minor' = other disjunctive accents; 'none' = conjunctive accent only."""
    if verse_final or "etnahta" in acc:
        return "major"
    if book in POETIC_ACCENT_BOOKS and "ole" in acc and "merkha" in acc:
        return "major"
    if any(a in MINOR_DISJ for a in acc):
        return "minor"
    return "none"


def syntactic_role(w, F, L):
    """Rough role of the participle in its phrase:
    'attribute'  - inside a subphrase with relation 'atr' that it heads (follows a noun),
    'genitive'   - nomen rectum (subphrase relation 'rec') headed by the participle,
    'head'       - first content word of its phrase (after article / preposition),
    'other'      - anything else (apposition, parallel member, ...)."""
    for sp in L.u(w, "subphrase"):
        sw = L.d(sp, "word")
        first = [x for x in sw if F.pdp.v(x) not in ("art", "prep", "conj")]
        if first and first[0] == w:
            r = F.rela.v(sp)
            if r == "atr":
                return "attribute"
            if r == "rec":
                return "genitive"
    phrase = L.u(w, "phrase")[0]
    pw = [x for x in L.d(phrase, "word") if F.pdp.v(x) not in ("art", "prep", "conj")]
    if pw and pw[0] == w:
        return "head"
    return "other"


def main():
    TF = Fabric(locations=BHSA, silent="deep")
    api = TF.load(FEATURES, silent="deep")
    F, L, T = api.F, api.L, api.T

    rows = []
    for w in F.otype.s("word"):
        if F.language.v(w) != "Hebrew":
            continue
        lexicalized = F.lex.v(w) in LEXICALIZED_QAL_PTC
        if not lexicalized and (F.vt.v(w) not in ("ptca", "ptcp") or F.gn.v(w) != "f" or F.nu.v(w) != "sg"):
            continue
        if lexicalized and (F.nu.v(w) != "sg" or not re.sub(r"[0-9]", "", F.g_word.v(w)).endswith(("@H", "T"))):
            continue
        book, ch, vs_ = T.sectionFromNode(w)
        if (book, ch, vs_, F.lex.v(w)) in EXCLUDE:
            continue
        vwords = L.d(L.u(w, "verse")[0], "word")
        clause = L.u(w, "clause")[0]
        cwords = L.d(clause, "word")
        phrase = L.u(w, "phrase")[0]
        pwords = L.d(phrase, "word")
        nxt = w + 1 if w + 1 <= vwords[-1] else None
        # ketiv words are unpointed in BHSA: take the accents from the pointed qere
        acc = accents(F.qere_utf8.v(w) or F.g_word_utf8.v(w))
        ending, sub = form_type(F.g_word.v(w), F.prs.v(w))
        rows.append({
            "node": w,
            "book": book, "chapter": ch, "verse": vs_,
            "book_group": BOOK_GROUP.get(book, "?"),
            "word": F.g_word_utf8.v(w),
            "translit": F.g_word.v(w),
            "qere": F.qere_utf8.v(w) or "",
            "lex": F.lex.v(w), "lex_utf8": F.voc_lex_utf8.v(w), "gloss": F.gloss.v(w),
            "bhsa_tag": F.sp.v(w) if lexicalized else "ptc",
            "stem": "qal" if lexicalized else F.vs.v(w),
            "vt": "ptca" if lexicalized else F.vt.v(w),
            "state": F.st.v(w), "suffix": F.prs.v(w),
            "root_class": LEXICALIZED_ROOT_CLASS.get(F.lex.v(w))
            or root_class(LEXICALIZED_QAL_PTC.get(F.lex.v(w), F.lex.v(w))),
            "ending": ending, "form_subtype": sub,
            "pattern_first_vowel": vname(groups(F.g_word.v(w))[0][0][1]) if F.g_word.v(w) else "",
            "accents": ";".join(acc),
            "pause": pause_level(acc, w == vwords[-1], book),
            "role": syntactic_role(w, F, L),
            "clause_has_object": int(any(F.function.v(p) in ("Objc", "PreO", "PtcO")
                                         for p in L.d(clause, "phrase"))),
            "verse_final": int(w == vwords[-1]),
            "atnah": int("etnahta" in acc),
            "clause_final": int(w == cwords[-1]),
            "article": int(w - 1 in pwords and F.lex.v(w - 1) == "H"),
            "prev_word": F.g_word_utf8.v(w - 1) if w - 1 >= vwords[0] else "",
            "prev_lex": F.lex.v(w - 1) if w - 1 >= vwords[0] else "",
            "next_word": F.g_word_utf8.v(nxt) if nxt else "",
            "next_lex": F.lex.v(nxt) if nxt else "",
            "next_pdp": F.pdp.v(nxt) if nxt else "",
            "phrase_function": F.function.v(phrase),
            "phrase_type": F.typ.v(phrase),
            "phrase_det": F.det.v(phrase) or "",
            "clause_type": F.typ.v(clause),
            "clause_rela": F.rela.v(clause),
            "domain": F.domain.v(clause) or "",
            "txt": F.txt.v(clause) or "",
            "clause_text": T.text(cwords),
        })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print(len(rows), "rows written to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
