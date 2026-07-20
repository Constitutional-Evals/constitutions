# Foundational documents for `stoicism`

Source texts for the Stoicism anchor constitution. All committed files are clean
Markdown converted from public-domain sources (Project Gutenberg, English Wikisource).
Copyrighted works are recorded metadata-only in `manifest.json` (`redistributable: false`,
no text stored).

## Committed files

**Primary bundle** (loaded together — five files, ~111k tokens):

| File | Work | Translation | Size |
|------|------|-------------|------|
| `epictetus-enchiridion-long.md` | Epictetus, *Enchiridion* (complete, 53 ch.) | George Long | ~10.5k tok |
| `epictetus-discourses-long-selection.md` | Epictetus, *Discourses* (17 selected chapters) | George Long | ~19.3k tok |
| `marcus-aurelius-meditations-long-books1-6.md` | Marcus Aurelius, *Meditations* Books 1-6 (complete) | George Long (1862) | ~27.5k tok |
| `marcus-aurelius-meditations-long-books7-12.md` | Marcus Aurelius, *Meditations* Books 7-12 (complete) | George Long (1862) | ~31.5k tok |
| `seneca-moral-letters-selection.md` | Seneca, *Moral Letters to Lucilius* (10 letters) | R. M. Gummere (1917-25) | ~22.3k tok |
| **Primary-config total** | | | **~111k tok** |

**Optional / not part of the primary bundle** (committed, but loaded only for translation-sensitivity or interpretive probing — do not count against the ~111k primary total):

| File | Work | Translation | Size |
|------|------|-------------|------|
| `marcus-aurelius-meditations-casaubon-books2-4.md` | Marcus Aurelius, *Meditations* Books II-IV — *translation-sensitivity variant* | Meric Casaubon (1634) | ~14.5k tok |
| `interpretive-long-philosophy-of-antoninus.md` | George Long, 'The Philosophy of Antoninus' — *interpretive-layer essay* | — | ~17k tok |

The three foundational primary authors are all represented: **Epictetus** (Enchiridion +
Discourses), **Marcus Aurelius** (Meditations), and **Seneca** (Moral Letters, serving as
the public-domain stand-in for the systematic-ethics role). The primary bundle keeps the two
"definitional" texts complete (the Enchiridion in full, and both Meditations files in full)
and trims only the two already-curated selection files (Discourses, Seneca) to stay under the
~120k bundle cap.

## Selection decisions

- **Epictetus.** The *Enchiridion* is short and included complete. The *Discourses* are long
  (4 books); 17 chapters were selected for the ethically richest material: the dichotomy of
  control ("what is up to us"), desire and aversion, providence and the rational order, the
  nature of the good, kinship with God and human dignity, roles and duties, freedom, bearing
  adversity and sickness, tranquillity, friendship, and attention (*prosochē*). (An earlier
  22-chapter draft was trimmed to 17 to fit the primary bundle; the five dropped chapters —
  Of Contentment, Not Being Angry at Others' Faults, On Constancy, What Solitude Is, On Freedom
  From Fear — are each thematically covered by a retained chapter.) Both texts are from George
  Long's translation; a P.E. Matheson (1916) rendering could later be added as a
  translation-sensitivity variant.
- **Marcus Aurelius.** *Meditations* is short, so the complete twelve books are included
  (George Long, 1862), split across two files only to respect the per-document size cap. The
  Meric Casaubon (1634) translation of Books II-IV is committed as an **optional** deliberate
  archaic-idiom sensitivity probe — not part of the primary bundle.
- **Seneca (the Becker fix).** Becker's *A New Stoicism* (the requested systematic modern
  reconstruction) is copyrighted and cannot be committed. Its role — virtue as the only good,
  "following the facts," Stoic axiology, ideal rational agency — is carried by a selection of
  10 of Seneca's 124 *Moral Letters* (Gummere, public domain): the supreme good and virtue as
  the only good (71, 76, 120), the divine reason within and following nature (41, 107),
  philosophy as therapy and the guide of life (23), the equal humanity of all persons incl.
  slaves (47), self-sufficiency and friendship (9), and the mortality of each day and facing
  death (1, 26). (An earlier 15-letter draft was trimmed to 10 for the primary bundle; dropped:
  5, 7, 8, 16, 44.)
- **Interpretive layer.** George Long's 1862 essay "The Philosophy of Antoninus" is committed
  as an **optional** public-domain scholarly framing — not part of the primary bundle. E.
  Vernon Arnold's *Roman Stoicism* (1911, PD) is recorded metadata-only as an available fuller
  option; Pierre Hadot's *The Inner Citadel* (1998) and Becker's *A New Stoicism* (1998) are
  recorded metadata-only as copyrighted modern studies.

## Copyright

US framework (2026): works first published before 1930 are public domain. All committed
translations qualify — Casaubon 1634, Long 1862/1877, Gummere 1917-1925. Ancient authorship is
irrelevant to copyright; the translation date is what matters. Becker (1998) and Hadot (1998)
are copyrighted and stored metadata-only. No copyrighted full text is stored anywhere in this
folder, including `_private/`.

## Note on a common cataloguing error

Project Gutenberg #2680, frequently cited as "the George Long *Meditations*," is actually the
**Meric Casaubon (1634)** translation (verified against the opening of Book I). The genuine
George Long translation is Gutenberg **#15877** and is used here as the primary Meditations.

## Recommended assembly

The committed files total more than one 120k-token bundle because they include translation
variants and interpretive material meant to be swapped, not all loaded at once. The **primary
configuration** is the five files listed in the primary table above — the two Meditations
(Long) files + Enchiridion + Discourses selection + Seneca selection — which total **~111k
tokens**, comfortably under the ~120k bundle cap. The Casaubon variant (~14.5k tok) and the
Long essay (~17k tok) are committed but **optional**: load them individually for
translation-sensitivity or interpretive probing, not as part of the primary ~111k bundle.
