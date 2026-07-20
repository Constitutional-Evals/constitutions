# Foundational documents for the `islam` constitution

This bundle distils the ethical core of the Islamic tradition from three foundational
strands named in the project's technical appendix: (1) the **Qur'an**, (2) **al-Ghazali's
Ihya' 'Ulum al-Din** (Revival of the Religious Sciences), and (3) **Ibn Miskawayh's
Tahdhib al-Akhlaq** (The Refinement of Character). See `manifest.json` for every source,
its license, and whether its full text is redistributable.

## Committed (public-domain) texts

| File | Work | ~tokens |
|------|------|--------|
| `quran-ethical-selections-pickthall.md` | Qur'an, ethical passages, Pickthall trans. (1930) | ~9.4k |
| `quran-ethical-selections-muhammad-ali.md` | Qur'an, same ethical passages, Muhammad Ali trans. (1917/1920) | ~9.5k |
| `ghazali-alchemy-of-happiness-field.md` | al-Ghazali, *The Alchemy of Happiness*, Field trans. (1909) | ~35k |

Total committed bundle ≈ **54k tokens** (well under the 120k cap; each file under the 50k cap).

The Qur'anic ethical core is now given in **two independent public-domain translations**
(Pickthall 1930 and Muhammad Ali 1917/1920) over the same selected passages, for translation
diversity and to supply a public-domain interpretive second-translation in place of the
copyright-encumbered Yusuf Ali. See the header of `quran-ethical-selections-muhammad-ali.md`
for its public-domain reasoning and fidelity caveats (al-Fatiha omitted; the Surah-2 divine-name
rendering; the missing 2:275).

## The Qur'anic "ethical surahs" curation

The appendix asks for "ethical surahs" without enumerating them. The Qur'an does not gather
its ethics into one place, so this is a **curated selection of the passages most often cited
as loci of Qur'anic moral teaching**, chosen to cover the recurring ethical themes:

- **Al-Fatiha (1)** — the opening prayer, recited in every ritual prayer.
- **Al-Baqara 2:153-188, 2:261-283** — patience and righteousness; charity (*sadaqa*),
  the prohibition of usury, honest debts and contracts.
- **An-Nisa 4:36, 4:135** — kindness to parents, kin, neighbours and the needy; standing
  firm for justice even against oneself.
- **Al-Ma'ida 5:8** — never letting hatred of a people lead you away from justice.
- **Al-An'am 6:151-153** — the "commandments" passage (do not kill, deal justly, keep the
  covenant).
- **An-Nahl 16:90-97** — "Allah enjoins justice and kindness"; keeping oaths; the good life.
- **Al-Isra 17:23-39** — the decalogue-like sequence of ethical injunctions.
- **Al-Furqan 25:63-76** — the "servants of the Merciful" (*'ibad ar-Rahman*): humility,
  moderation, truthfulness.
- **Luqman (31, full)** — wisdom literature: a father's moral counsel to his son.
- **Al-Hujurat (49, full)** — social manners, brotherhood, against slander, suspicion and
  mockery.
- **Al-Balad (90, full)**, **Al-Asr (103, full)**, **Al-Ma'un (107, full)** — the "steep
  path" of freeing the enslaved and feeding the poor; the accounting of time; the condemnation
  of those who neglect the orphan and the needy.

Verse numbering follows the standard Hafs/Kufan numbering of the Pickthall edition. Whole
short surahs are given in full; longer surahs are represented by their most ethically salient
passages, with the range noted in each heading.

## The Ihya' translation situation (important)

The three respected modern English translations of al-Ghazali's *Ihya' 'Ulum al-Din* — the
**Islamic Texts Society** book-by-book series (translators incl. T.J. Winter / Abdal Hakim
Murad), the **Fons Vitae** Ghazali Series, and the **Fazl-ul-Karim** four-volume rendering —
are all under copyright or of unclear copyright status. None may be committed to this public
repo (see the `redistributable: false` entries in `manifest.json`).

As the public-domain stand-in we include **al-Ghazali's own abridgment of the Ihya**, *The
Alchemy of Happiness* (*Kimiya-yi Sa'adat*), in Claud Field's 1909 translation. Ghazali wrote
it in Persian to condense the Ihya's forty books for a general readership; its eight chapters
track the Ihya's core themes (self-knowledge, knowledge of God, the moral valuation of this
world and the next, spiritual discipline, self-examination, marriage, and the love of God),
and Field notes the first four chapters correspond to the opening of the Ihya. It is the best
genuinely public-domain proxy for the Ihya's ethical content.

## Ibn Miskawayh

The standard English translation of *Tahdhib al-Akhlaq* by **Constantine K. Zurayk** (AUB
Press, 1968) is under copyright — a metadata-only entry, no text stored. No public-domain
English translation is known to exist. Its themes (Greek-influenced virtue ethics: the soul's
faculties, virtue as a mean, justice, love and friendship) are summarised in the manifest note.

## Interpretive / commentary sources

Commentary (*tafsir*) matters for interpretation quality. Recorded in the manifest:

- **Abdullah Yusuf Ali's translation-with-commentary** — extensive interpretive footnotes.
  Frequently assumed to be public domain, but its 1934-1938 *foreign* publication likely
  triggers U.S. URAA copyright restoration (term running to ~2029+), so it is treated here as
  **not redistributable** (metadata + short fair-use excerpt only). See the caution below.
- **Maulana Muhammad Ali's 1917/1920 translation** — a genuinely public-domain (pre-1931)
  alternative interpretive source and second translation, now **committed** as
  `quran-ethical-selections-muhammad-ali.md` (translation of the same ethical passages, taken
  from the scan-backed Wikisource transcription of the 1920 printing — NOT the copyrighted 1951
  revision or modern Zahid-Aziz editions). His extensive PD *commentary* footnotes are not
  committed: they survive cleanly only in the first-edition page-scans and would need
  hand-verified OCR (a human-procurement item); the clean per-verse commentary on
  aaiil.org/muslim.org is the copyrighted revised edition and must not be used.
- **Fazlur Rahman, *Major Themes of the Qur'an*** (1980) — a leading modern academic thematic
  treatment; copyrighted, metadata-only.

## Copyright determinations made

- **Pickthall (1930)** — PUBLIC DOMAIN in the U.S. as of 1 January 2026 (95 years after
  publication). Committed in full (selection). ✅
- **Alchemy of Happiness / Field (1909)** — PUBLIC DOMAIN (pre-1930). Committed in full. ✅
- **Yusuf Ali (1934-1938)** — likely STILL UNDER U.S. COPYRIGHT via URAA restoration of a
  foreign work; treated as not redistributable. ⚠️ (This departs from the initial assumption
  that Yusuf Ali is public domain — see the return notes.)
- **Muhammad Ali (1917/1920)** — PUBLIC DOMAIN (pre-1931; URAA-restored term of 95 yrs from
  1917 already expired in 2012). Now committed as a public-domain second translation. ✅
- **Ihya (ITS / Fons Vitae / Fazl-ul-Karim), Zurayk's Ibn Miskawayh, Fazlur Rahman** —
  copyrighted or unclear; metadata-only, no text stored.

A gitignored `_private/` folder exists for local-only working copies but was **not** used to
obtain the full text of any copyrighted book.
