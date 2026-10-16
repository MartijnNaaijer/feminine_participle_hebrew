"""Download the complete Hebrew Bible of the edition "מקרא על פי המסורה" (Miqra according to the
Masorah, Hebrew Wikisource; based on the Aleppo Codex and closely related manuscripts), with
vowels and accents.

Output (in data/aleppo_edition/):
  raw/<Book>_<chapter>.txt   the raw wikitext of each chapter page (keeps the edition's notes,
                             e.g. {{נוסח|...}} variant notes, ketiv/qere and layout templates)
  <NN>_<Book>.tsv            one verse per line: book, chapter, verse, pointed text
                             (templates resolved: main text of variant notes kept)
  README.md                  source, licence and format

Licence of the text: CC-BY-SA 4.0. Attribution: "מקרא על פי המסורה", he.wikisource.org.
Chapter counts are taken from the BHSA. Already-downloaded chapters (also those in
data/aleppo_cache/) are reused. Run from the project root:  python scripts/download_aleppo_edition.py
"""
import os
import shutil
import sys

from tf.fabric import Fabric

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_aleppo as ca  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUTDIR = os.path.join(ROOT, "data", "aleppo_edition")
RAW = os.path.join(OUTDIR, "raw")
BHSA = os.path.expanduser("~/text-fabric-data/etcbc/bhsa/tf/2021")


def chapter_counts():
    TF = Fabric(locations=BHSA, silent="deep")
    api = TF.load("", silent="deep")
    F, T = api.F, api.T
    books = []
    for b in F.otype.s("book"):
        name = T.sectionFromNode(b)[0]
        books.append((name, len(api.L.d(b, "chapter"))))
    return books


def main():
    os.makedirs(RAW, exist_ok=True)
    # reuse pages already fetched by check_aleppo.py
    for f in os.listdir(ca.CACHE) if os.path.isdir(ca.CACHE) else []:
        if not os.path.exists(os.path.join(RAW, f)):
            shutil.copy(os.path.join(ca.CACHE, f), RAW)
    ca.CACHE = RAW  # fetch() now reads/writes the raw folder
    books = chapter_counts()
    missing = []
    for i, (book, n) in enumerate(books, 1):
        lines = []
        for ch in range(1, n + 1):
            try:
                text = ca.fetch(book, ch)
            except Exception as e:  # noqa: BLE001
                missing.append(f"{book} {ch}: {e}")
                continue
            vs = ca.verses(text)
            for heb, t in vs.items():
                if heb == "סימן":
                    continue
                num = heb_to_int(heb)
                t = " ".join(t.split())
                lines.append((ch, num, t))
        lines.sort()
        with open(os.path.join(OUTDIR, f"{i:02d}_{book}.tsv"), "w", encoding="utf-8") as fh:
            fh.write("book\tchapter\tverse\ttext\n")
            for ch, num, t in lines:
                fh.write(f"{book}\t{ch}\t{num}\t{t}\n")
        print(book, n, "chapters,", len(lines), "verses", flush=True)
    if missing:
        print("MISSING:", *missing, sep="\n")


def heb_to_int(s):
    val = {"א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9, "י": 10, "כ": 20,
           "ל": 30, "מ": 40, "נ": 50, "ס": 60, "ע": 70, "פ": 80, "צ": 90, "ק": 100, "ר": 200, "ש": 300, "ת": 400}
    return sum(val.get(c, 0) for c in s)


if __name__ == "__main__":
    main()
