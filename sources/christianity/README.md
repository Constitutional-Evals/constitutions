# Foundational documents for the `christianity` anchor

Source texts the `christianity` constitution is distilled from. Every file here is public
domain and has been converted to clean Markdown; the modern scholarly works used only for
interpretation are recorded in `manifest.json` as metadata (no text stored). See
`manifest.json` for full provenance, licenses, and per-source notes.

## The bundle

| File | Work | Translation | ~chars |
|------|------|-------------|-------:|
| `sermon-on-the-mount-web.md` | Sermon on the Mount (Matthew 5–7) | World English Bible (public domain) | 14.5k |
| `sermon-on-the-mount-kjv.md` | Sermon on the Mount (Matthew 5–7) | King James Version | 14.7k |
| `augustine-city-of-god-selections-dods.md` | Augustine, *City of God* (selections) | Marcus Dods, 1871 | 163.5k |
| `aquinas-summa-II-II-selections.md` | Aquinas, *Summa Theologiae* II-II (selections) | English Dominican Province, 1920 | 184.5k |
| `chrysostom-homilies-on-matthew-selections.md` | Chrysostom, *Homilies on Matthew* (2 homilies) | NPNF, Prevost/Riddle, 1888 | 86k |

Total ≈ 463k characters ≈ 110–115k tokens (at or just under the ~120k-token bundle cap).

## Selection decisions

Three works are the **foundational** sources; two of the three are far larger than the
per-document size cap (~50k tokens), so each large work carries a **selection rationale in its
own file header**. In brief:

- **Sermon on the Mount** — included in full in two public-domain translations (WEB and KJV),
  so the bundle carries both a plain modern rendering and the familiar Early Modern English of
  the same short, self-contained ethical discourse. The two translations also serve as the
  repo's formatting-sensitivity probe.
- **Augustine, *City of God*** — **Book XIX in full** (the ethical heart: the supreme good,
  peace as "the tranquillity of order," justice, ordered love, the ends of the two cities),
  plus selected chapters of **Book XIV** (living according to man vs. God; the will and love;
  pride; the two cities formed by two loves — *"the earthly by the love of self … the heavenly
  by the love of God"*), **Book I** (mercy to the defeated; providence to good and wicked
  alike; the two cities intermingled), and **Book V** (glory, domination, and true happiness in
  rule).
- **Aquinas, *Summa* II-II** — a coherent ethical core across the three theological virtues and
  the chief social cardinal virtue, keeping whole Questions so the dialectical structure
  survives: **Q4** faith, **Q17** hope, **Q23** charity (friendship with God; the form of the
  virtues), **Q25** the object of charity (love of neighbour and of enemies — resonating with
  the Sermon's "love your enemies"), and **Q58** justice. The full charity treatise (qq. 23–27,
  including Q26 "Of the Order of Charity") and the prudence/fortitude/temperance definitions
  were omitted for length; the *ordo amoris* theme they develop is covered extensively by the
  Augustine selections.

### Interpretive works (interpretation matters for distillation quality)

- **John Chrysostom, *Homilies on Matthew*** — public domain and **included** (Homilies 15 and
  18), the classic patristic exposition of the Beatitudes and of non-retaliation / love of
  enemies. It shows how the early Church actually read the Sermon's ethics.
- **Betz, *The Sermon on the Mount*** (Hermeneia); **Markus, *Saeculum*** (on Augustine's two
  cities); **Pinckaers, *The Sources of Christian Ethics*** (on Thomistic virtue ethics) —
  modern, copyrighted; recorded **metadata-only** in `manifest.json` (`redistributable: false`,
  no files, with a short fair-use summary and no quoted text).

## Conversion notes

All files were converted from public-domain plain-text / HTML sources (ebible.org, Project
Gutenberg, New Advent's NPNF reproduction). Gutenberg/site boilerplate, navigation, donation
banners, page markers, and scripture-reference/Latin footnotes were stripped; original
italics were preserved as Markdown emphasis; **no words of any translation were altered**. Each
file was spot-checked for garbled markup, stray entities, and footnote/nav residue.
