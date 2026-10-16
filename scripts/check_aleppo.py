"""Compare every MT feminine singular participle (BHSA = Codex Leningradensis) with the
Aleppo-Codex-based edition "מקרא על פי המסורה" (Miqra according to the Masorah) on Hebrew Wikisource.

The edition follows the Aleppo Codex where it survives and closely related Tiberian manuscripts
elsewhere (Torah up to Deut 28:16, and the other lost parts). The column `aleppo_extant`
marks whether the verse lies in a part of the Aleppo Codex that survives (standard list of lacunae).

For each participle the script finds the word with the same consonants in the same verse and
compares (a) the vowel pointing (accents and meteg removed) and (b) the accents.

Chapter pages are cached in data/aleppo_edition/raw/ (raw wikitext, CC-BY-SA, he.wikisource.org).
Output: data/aleppo_comparison.csv. Run from the project root:  python scripts/check_aleppo.py
"""
import csv
import json
import os
import re
import subprocess
import time
import unicodedata
import urllib.parse

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MT = os.path.join(ROOT, "data", "mt_fsg_participles.csv")
OUT = os.path.join(ROOT, "data", "aleppo_comparison.csv")
CACHE = os.path.join(ROOT, "data", "aleppo_edition", "raw")
API = "https://he.wikisource.org/w/api.php"

BOOK_HE = {
    "Genesis": "בראשית", "Exodus": "שמות", "Leviticus": "ויקרא", "Numbers": "במדבר", "Deuteronomy": "דברים",
    "Joshua": "יהושע", "Judges": "שופטים", "1_Samuel": "שמואל א", "2_Samuel": "שמואל ב",
    "1_Kings": "מלכים א", "2_Kings": "מלכים ב", "Isaiah": "ישעיהו", "Jeremiah": "ירמיהו",
    "Ezekiel": "יחזקאל", "Hosea": "הושע", "Joel": "יואל", "Amos": "עמוס", "Obadiah": "עובדיה",
    "Jonah": "יונה", "Micah": "מיכה", "Nahum": "נחום", "Habakkuk": "חבקוק", "Zephaniah": "צפניה",
    "Haggai": "חגי", "Zechariah": "זכריה", "Malachi": "מלאכי", "Psalms": "תהלים", "Job": "איוב",
    "Proverbs": "משלי", "Ruth": "רות", "Song_of_songs": "שיר השירים", "Ecclesiastes": "קהלת",
    "Lamentations": "איכה", "Esther": "אסתר", "Daniel": "דניאל", "Ezra": "עזרא", "Nehemiah": "נחמיה",
    "1_Chronicles": "דברי הימים א", "2_Chronicles": "דברי הימים ב",
}

# Parts of the Aleppo Codex that are lost (standard list); verses here come from related manuscripts.
LACUNAE = [
    ("Genesis", (1, 1), (50, 99)), ("Exodus", (1, 1), (40, 99)), ("Leviticus", (1, 1), (27, 99)),
    ("Numbers", (1, 1), (36, 99)), ("Deuteronomy", (1, 1), (28, 16)),
    ("2_Kings", (14, 21), (18, 13)), ("Jeremiah", (29, 9), (31, 34)),
    ("Amos", (8, 13), (9, 99)), ("Obadiah", (1, 1), (1, 99)), ("Jonah", (1, 1), (4, 99)),
    ("Micah", (1, 1), (5, 1)), ("Psalms", (15, 1), (25, 1)), ("Song_of_songs", (3, 11), (8, 99)),
    ("Ecclesiastes", (1, 1), (12, 99)), ("Lamentations", (1, 1), (5, 99)), ("Esther", (1, 1), (10, 99)),
    ("Daniel", (1, 1), (12, 99)), ("Ezra", (1, 1), (10, 99)), ("Nehemiah", (1, 1), (13, 99)),
]


def extant(book, ch, vs):
    for b, a, z in LACUNAE:
        if b == book and a <= (ch, vs) <= z:
            return 0
    return 1


def heb_num(n):
    units = ["", "א", "ב", "ג", "ד", "ה", "ו", "ז", "ח", "ט"]
    tens = ["", "י", "כ", "ל", "מ", "נ", "ס", "ע", "פ", "צ"]
    s = ""
    if n >= 100:
        s += "קרש"[n // 100 - 1] if n < 400 else "ת"
        n %= 100
    if n == 15:
        return s + "טו"
    if n == 16:
        return s + "טז"
    return s + tens[n // 10] + units[n % 10]


def fetch(book, ch):
    os.makedirs(CACHE, exist_ok=True)
    fn = os.path.join(CACHE, f"{book}_{ch}.txt")
    if os.path.exists(fn):
        return open(fn, encoding="utf-8").read()
    title = f"{BOOK_HE[book]} {heb_num(ch)}/טעמים"
    url = API + "?" + urllib.parse.urlencode(
        {"action": "parse", "page": title, "prop": "wikitext", "format": "json"})
    # curl instead of urllib: Python's certificate store fails on this machine
    for attempt in range(6):
        raw = subprocess.run(["curl", "-s", "-A", "feminine-participle-research/1.0", url],
                             capture_output=True, check=True).stdout
        try:
            data = json.loads(raw.decode("utf-8"))
            break
        except ValueError:  # empty reply = rate limited; back off
            time.sleep(5 * (attempt + 1))
    else:
        raise RuntimeError("no reply for " + title)
    text = data["parse"]["wikitext"]["*"]
    open(fn, "w", encoding="utf-8").write(text)
    time.sleep(1.5)
    return text


def _resolve(m):
    parts = m.group(1).split("|")
    name, args = parts[0].strip(), [a for a in parts[1:] if not re.match(r"^\s*[^=]{1,3}=", a) or a.startswith("1=")]
    if name == 'כו"ק' and len(parts) >= 3:            # ketiv / qere: keep both
        return f" {parts[1]} {parts[2]} "
    if not args:                                      # layout templates (line breaks, paragraph marks)
        return " "
    return args[0].replace("1=", "", 1)               # main text (variant notes, accent variants, large letters)


def clean(text):
    """Resolve the edition's templates to plain pointed text, innermost first."""
    while "{{" in text:
        new = re.sub(r"\{\{([^{}]*)\}\}", _resolve, text)
        if new == text:
            break
        text = new
    return text


def verses(wikitext):
    out = {}
    for m in re.finditer(r"<קטע התחלה=([א-ת]+)/>(.*?)<קטע סוף=\1/>", wikitext, re.S):
        out[m.group(1)] = clean(m.group(2))
    return out


ACCENTS = {chr(c) for c in range(0x0591, 0x05B0)} | {"ֽ", "׀", "׃"}


def norm_vowels(w):
    """Pointing without accents, meteg, sof pasuq, holam (placed differently in the two
    encodings: BHSA puts the holam of holam-male on the preceding consonant) and the
    dagesh of the first letter (BHSA marks the conjunctive dagesh forte)."""
    w = unicodedata.normalize("NFD", w)
    w = "".join(c for c in w if c not in ACCENTS and c not in "ֹֺ")
    w = w.replace("ׇ", "ָ")  # qamets qatan -> qamets
    # editorial marks of the edition (U+FB1E after a vocal shewa) and shin/sin dots (absent in unpointed ketiv)
    w = w.replace("ﬞ", "").replace("ׁ", "").replace("ׂ", "")
    if len(w) > 1 and w[1] == "ּ":
        w = w[0] + w[2:]
    return unicodedata.normalize("NFC", w)


def accents_of(w):
    return "".join(unicodedata.name(c, "?").replace("HEBREW ACCENT ", "").lower() + ";"
                   for c in unicodedata.normalize("NFD", w) if c in ACCENTS and c not in "׀׃")


def cons(w):
    # NFD first: the edition sometimes uses precomposed presentation forms (e.g. U+FB2A shin with dot)
    return "".join(c for c in unicodedata.normalize("NFD", w) if "א" <= c <= "ת")


def strip_prefix(w, n):
    """Remove the first n consonants (with their marks) from a pointed word."""
    w = unicodedata.normalize("NFD", w)
    seen, i = 0, 0
    while i < len(w):
        if "א" <= w[i] <= "ת":
            if seen == n:
                break
            seen += 1
        i += 1
    return unicodedata.normalize("NFC", w[i:])


def candidates(text, targets):
    """Words of a verse with the target consonants; BHSA writes article, conjunction and some
    prepositions as separate words, the edition writes them joined, so prefixed words count too."""
    out = []
    for w in re.split(r"[\s־]+", text):
        c = cons(w)
        if c in targets:
            out.append(w)
            continue
        for t in targets:
            n = len(c) - len(t)
            if c.endswith(t) and 0 < n <= 2 and set(c[:n]) <= set("הובכלמש"):
                out.append(strip_prefix(w, n))
                break
    return out


def pause_class(w, verse_final, book):
    """Pause level of the edition's word, with the same definition as extract_mt.pause_level."""
    from extract_mt import pause_level, accents
    return pause_level(accents(w), verse_final, book)


def main():
    rows = list(csv.DictReader(open(MT, encoding="utf-8-sig")))
    out = []
    for r in rows:
        book, ch, vs = r["book"], int(r["chapter"]), int(r["verse"])
        res = {"book": book, "chapter": ch, "verse": vs, "lex": r["lex"], "stem": r["stem"],
               "ending": r["ending"], "form_subtype": r["form_subtype"], "pause": r["pause"],
               "aleppo_extant": extant(book, ch, vs), "L_word": r["word"]}
        try:
            allv = verses(fetch(book, ch))
            v = allv.get(heb_num(vs), "")
            # the edition sometimes numbers verses differently: also look one verse before/after
            v_near = " ".join(allv.get(heb_num(x), "") for x in (vs - 1, vs + 1) if x > 0)
        except Exception as e:  # noqa: BLE001
            v, v_near, res["error"] = "", "", str(e)
        # reference form: the pointed qere where BHSA has an unpointed ketiv
        ref = r["qere"] if r["qere"] else r["word"]
        targets = {cons(r["word"]), cons(ref)}
        cands = candidates(v, targets)
        res["verse_shift"] = 0
        if not cands and v_near:  # the edition sometimes numbers verses differently
            cands = candidates(v_near, targets)
            res["verse_shift"] = int(bool(cands))
        # several words of the same lexeme in a verse: take the one closest to the Leningrad form
        exact = [w for w in cands if norm_vowels(w) == norm_vowels(ref)]
        exact_acc = [w for w in exact if accents_of(w) == accents_of(ref)]
        a = (exact_acc or exact or cands or [""])[0]
        res["A_word"] = a
        res["n_candidates"] = len(cands)
        res["L_reference"] = ref
        res["vowels_equal"] = int(bool(a) and norm_vowels(a) == norm_vowels(ref))
        res["accents_equal"] = int(bool(a) and accents_of(a) == accents_of(ref))
        res["L_accents"], res["A_accents"] = accents_of(ref), accents_of(a) if a else ""
        res["L_pause"], res["A_pause"] = r["pause"], pause_class(a, r["verse_final"] == "1", book) if a else ""
        out.append(res)
    keys = list(dict.fromkeys(k for o in out for k in o))
    with open(OUT, "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys)
        wr.writeheader()
        wr.writerows(out)
    found = sum(1 for o in out if o["A_word"])
    print(f"{len(out)} rows; Aleppo-edition word found for {found}; "
          f"vowels equal {sum(o['vowels_equal'] for o in out)}; accents equal {sum(o['accents_equal'] for o in out)}")


if __name__ == "__main__":
    main()
