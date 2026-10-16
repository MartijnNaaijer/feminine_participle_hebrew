# The qal feminine singular participle in Biblical Hebrew: scripts

These are the scripts behind the CACCHT blog post and report on the feminine singular active participle in Biblical Hebrew. The study covers the forms קֹטְלָה (*qoṭlā*), קֹטֵלָה (*qoṭelā*) and קֹטֶלֶת (*qoṭelet*) in the Masoretic Text (MT), the Dead Sea Scrolls (DSS) and the Samaritan Pentateuch (SP).

Authors: Martijn Naaijer and Claude.

This repository holds the code only. The data files, the hand coding and the generated tables are not included (see below).

## Requirements

- Python 3.13.
- Packages: `text-fabric`, `pandas`, `scipy` (and `numpy`), with the versions used pinned in `requirements.txt`. Install them with `pip install -r requirements.txt`. `tabulate` is not needed, because `mdtable.py` renders the Markdown tables.
- `curl` on the PATH, used by `check_aleppo.py` and `download_aleppo_edition.py`.
- Text-Fabric corpora in the default locations:
  - BHSA 2021 (MT, Codex Leningradensis): `~/text-fabric-data/etcbc/bhsa/tf/2021`
  - ETCBC/dss 2.0.1: `~/text-fabric-data/github/ETCBC/dss/tf/2.0.1`
  - dt-ucph/sp: `~/text-fabric-data/dt-ucph/sp/tf/<version>`, where the highest version present is used. The study used 5.0.2.

## Folder layout expected

Run every script from the repository root, for example `python scripts/extract_mt.py`. Each script reads from and writes to a `data/` folder in the repository root:

```
data/
  mt_fsg_participles.csv        made by extract_mt.py
  dss_fsg_participles.csv       made by extract_dss.py
  sp_fsg_participles.csv        made by extract_sp.py, extended by add_sp_reading.py
  bh_sp_link.tsv                Samaritan transcription link file: NOT included, must be supplied
  aleppo_edition/               made by download_aleppo_edition.py / check_aleppo.py
  hexapla_cache/                made by hexapla_check.py
  coding/                       hand coding: NOT generated, must be supplied
    qal_h_coding.csv            three-axis coding of the qal ה forms
    position_coding.csv         clause position
    stich_coding.csv            stich position in poetry (consensus)
    poetry_T_coding.csv         syntax of the ת forms in poetry
    dss_parallel_check.csv      manual check of the DSS biblical parallels
```

All hand coding was done by Claude. A second Claude pass shows that the coding is repeatable, but it is not an independent check. The coding files are not in this repository.

## External sources not included

- **Samaritan reading tradition.** `add_sp_reading.py` and `analyse_sp_reading.py` read `data/bh_sp_link.tsv`, which links a machine-read (OCR) vocalized transcription of the Samaritan reading tradition to the dt-ucph/sp corpus. This file is not public. Without it, these two scripts cannot run.
- **Aleppo Codex.** The text is downloaded from the edition מקרא על פי המסורה (*Miqra according to the Masorah*) on Hebrew Wikisource (CC-BY-SA 4.0).
- **Hexapla.** Readings are fetched from the Göttingen Hexapla Database v3 API (CC BY-NC-SA 4.0).

## Scripts and order

| Step | Script | Reads | Writes |
|---|---|---|---|
| 1 | `extract_mt.py` | BHSA | `data/mt_fsg_participles.csv` (793 forms; Lev 7:9 excluded) |
| 2 | `analyse_mt.py` | MT csv | `data/mt_tables.md` |
| 3 | `extract_dss.py` | DSS, BHSA (imports helpers from `extract_mt.py`) | `data/dss_fsg_participles.csv` |
| 4 | `analyse_dss.py` | DSS csv | `data/dss_tables.md` |
| 5 | `extract_sp.py` | SP, MT csv | `data/sp_fsg_participles.csv` |
| 6 | `add_sp_reading.py` | SP csv, `data/bh_sp_link.tsv` | adds the Samaritan reading to the SP csv |
| 7 | `analyse_sp.py` | SP csv | `data/sp_tables.md` |
| 8 | `analyse_sp_reading.py` | SP and MT csv, BHSA, `data/bh_sp_link.tsv` | `data/sp_reading_tables.md` |
| 9 | `analyse_ending.py` | MT csv, `coding/qal_h_coding.csv`, `coding/poetry_T_coding.csv` | `data/ending_tables.md` |
| 10 | `analyse_qal_h.py` | MT csv, `coding/qal_h_coding.csv`, `position_coding.csv`, `stich_coding.csv` | `data/qal_h_tables.md` |
| 11 | `make_stich_sheet.py` | MT csv, BHSA, `coding/qal_h_coding.csv` | `data/coding/stich_blind.csv` (blank sheet for coding) |
| 12 | `dss_parallels.py` | DSS csv, DSS, BHSA, `coding/dss_parallel_check.csv` | `data/dss_parallels.csv`, `data/dss_parallels_tables.md` |
| 13 | `download_aleppo_edition.py` | Wikisource (network), BHSA | `data/aleppo_edition/` |
| 14 | `check_aleppo.py` | MT csv, Aleppo edition | `data/aleppo_comparison.csv` |
| 15 | `aleppo_subset.py` | Aleppo comparison, MT csv | prints Leningrad vs Aleppo for the forms the vowel argument rests on |
| 16 | `hexapla_check.py` | MT csv, Hexapla API (network) | `data/hexapla_fsg.csv` |

`mdtable.py` is a helper module and is not run on its own.
