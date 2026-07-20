# Foundational documents for the `judaism` anchor constitution

This bundle distills the Jewish moral-philosophical tradition through three foundational sources
(named in the project's technical appendix) plus supporting bridge and interpretive works. The
emphasis throughout is on **ethics** — how a person should act, what makes conduct good, and the
account of human perfection — rather than on ritual law, metaphysics, or exegesis for their own
sake.

## Included texts (committed to this public repo)

| File | Work | Translation | License |
|------|------|-------------|---------|
| `pirkei-avot-kulp.md` | Pirkei Avot (Ethics of the Fathers), full | Joshua Kulp (Mishnah Yomit) | CC-BY |
| `pirkei-avot-taylor.md` | Pirkei Avot, full | Charles Taylor (1897) | Public domain |
| `maimonides-guide-selections-friedlander.md` | Guide for the Perplexed, ethics selections | M. Friedländer (1904) | Public domain |
| `maimonides-eight-chapters-gorfinkle.md` | Eight Chapters (Shemonah Perakim), full | J. I. Gorfinkle (1912) | Public domain |
| `bahya-duties-of-the-heart-collins.md` | Duties of the Heart (Hovot ha-Levavot), Collins selection | Edwin Collins (1904) | Public domain |

- **Pirkei Avot** is the tradition's most concentrated collection of practical ethical maxims —
  transmitted teachings on justice, humility, study, speech, work, and the weighing of deeds. It
  is short, so it is included in full, in **two translations** (a modern scholarly one and a
  classic 1897 one) as a deliberate translation/formatting sensitivity probe.
- **Maimonides' Guide** supplies the rigorous philosophical frame: the purpose of the
  commandments, moral education, and the culminating doctrine (III:54) that true human perfection —
  knowledge of God — must express itself in *ḥesed* (loving-kindness), *mishpaṭ* (justice), and
  *ẓedaḳah* (righteousness). Only the ethics-relevant chapters are extracted (rationale in the
  file header); the full work is far over the per-document cap.
- **Maimonides' Eight Chapters** is the bridge between the two: his ethical psychology and
  introduction to Avot itself, on virtue as a disposition, the "mean," and free will. Full text.
- **Bahya's Duties of the Heart** supplies the tradition's inward/devotional ethics (mussar) —
  intention, gratitude, humility, trust in God, and the love of God — the strand that the
  copyrighted Heschel (source #3) also represents. Added as the **public-domain companion to the
  Heschel slot** so that dimension is present in the committable bundle. Collins's 1904 volume is
  an abridged selection of Bahya's ten "gates," reproduced in full here; his Introduction doubles
  as an interpretive essay. (From a Google Books OCR scan; minor OCR artifacts may remain.)

## Metadata-only (copyrighted or unverified — NOT committed)

Recorded in `manifest.json` with `redistributable: false` (or empty `files`), per the repo's
copyright rules:

- **Abraham Joshua Heschel, *God in Search of Man* (1955)** — foundational source #3, copyrighted.
  The major modern philosophy of Judaism (wonder / radical amazement, the ineffable, revelation,
  mitzvot as sacred deeds). Library/purchase link only. Its inward-ethics dimension is represented
  in the committable bundle by the public-domain **Bahya, *Duties of the Heart*** (above); for the
  distillation run, Heschel's own text should be supplied from a legally-obtained copy placed in
  `_private/` (never committed).
- **Menachem Kellner, *Maimonides on Human Perfection* (1990)** — interpretive; academic study of
  Guide III:54.
- **John C. Merkle, *The Genesis of Faith* (1985)** — interpretive; systematic exposition of
  Heschel's thought.
- **R. Travers Herford, *Pirke Aboth: The Ethics of the Talmud*** — classic PD-eligible commentary
  on Avot, but left uncommitted pending verification of a genuine 1925-first-edition text (later
  reprints are still under copyright). See the manifest note; flagged as an open question.

## Selection & sourcing decisions

- Sources fetched from clean machine-readable endpoints: the **Sefaria v3 API** (Avot, with
  per-version license metadata), **Project Gutenberg** (Guide), and the **Wikisource** proofread
  transcription (Eight Chapters). Navigation cruft, page numbers, footnote apparatus, and license
  boilerplate were stripped; every file was spot-checked.
- Full bundle is ~384k characters (~96k tokens), within the 120k-token cap; each file is within
  the ~50k-token per-document cap (largest is the Guide selection at ~30k tokens).

Working copies and fetch scripts are kept in the gitignored `_private/` folder.
