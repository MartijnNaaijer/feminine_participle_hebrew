"""Add the Samaritan reading (a vocalized transcription of the Samaritan reading
tradition) to data/sp_fsg_participles.csv.

Source: a machine-read (OCR) transcription linked to the SP corpus (data/bh_sp_link.tsv): ~99% of characters, 91-96% of words, vowel marks >99%.

The link file gives for every transcribed word the SP word(s) it reads (dt-ucph/sp 7.2.4 node ids,
which differ from the 5.0.2 nodes used in extract_sp.py). The join therefore does NOT use node ids:
a participle is matched by SP verse (book, chapter:verse of the first linked node) and SP consonants
(the last component of the linked g_cons, i.e. the word without prefixed conjunction/article/preposition).
When the same consonants occur more than once in a verse, occurrences are paired in order.

Run from the project root (after extract_sp.py):  python scripts/add_sp_reading.py
"""
import csv
import os
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SP_CSV = os.path.join(ROOT, "data", "sp_fsg_participles.csv")
LINK = os.path.join(ROOT, "data", "bh_sp_link.tsv")


def main():
    by_verse = defaultdict(list)  # (book, ch, vs) -> [(last consonant group, full g_cons, token)]
    with open(LINK, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            book, ch, vs, num, token, nodes, gcons, score, spverse = line.rstrip("\n").split("\t")
            sch, svs = spverse.split(":")
            by_verse[(book, sch, svs)].append((gcons.split("+")[-1], gcons, token))

    with open(SP_CSV, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    seen = defaultdict(int)
    hits = 0
    for r in rows:
        r["sp_reading"], r["sp_reading_gcons"] = "", ""
        cons = r.get("sp_cons") or ""
        if not cons:
            continue
        key = (r["book"], str(r["chapter"]), str(r["verse"]))
        cands = [c for c in by_verse.get(key, []) if c[0] == cons]
        n = seen[(key, cons)]
        seen[(key, cons)] += 1
        if n < len(cands):
            r["sp_reading"], r["sp_reading_gcons"] = cands[n][2], cands[n][1]
            hits += 1

    with open(SP_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    with_cons = sum(1 for r in rows if r.get("sp_cons"))
    print(f"Samaritan reading found for {hits} of {with_cons} SP words")


if __name__ == "__main__":
    main()
