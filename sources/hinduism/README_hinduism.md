# Foundational documents for the `hinduism` anchor

Source texts the `hinduism` constitution is distilled from. The bundle combines a complete
translation and integrated commentary on the *Bhagavad Gītā* with James Haughton Woods's
complete Harvard edition of Patañjali's *Yoga Sūtras*, the *Yoga-bhāṣya*, and the
*Tattva-vaiśāradī*. Both source works are public domain in the United States.

## The bundle

| File | Work | Translation / interpretation | Source | License | ~tokens |
|------|------|------------------------------|--------|---------|--------:|
| `Bhagavad Gita.md` | *Srimad-Bhagavad-Gita*: all 18 chapters with integrated commentary | English translation and commentary by Swami Swarupananda, 1909 | [Sacred Texts: *Srimad-Bhagavad-Gita*](https://www.sacred-texts.com/hin/sbg/index.htm) | [Public domain in the U.S.](https://www.sacred-texts.com/cnote.htm) | 60.2k |
| `Yoga Sutras.md` | Woods, *The Yoga-System of Patañjali*: complete *Yoga Sūtras*, *Yoga-bhāṣya*, and *Tattva-vaiśāradī* | Translated from Sanskrit by James Haughton Woods; Harvard University Press, 1914 | [HathiTrust Digital Library: Harvard edition](https://catalog.hathitrust.org/Record/100320326) | Public domain in the U.S. | 310.5k → ~50k |

Full sources total ≈ 370.7k tokens. The working Hinduism bundle is targeted at approximately
110k tokens: the complete 60.2k-token *Bhagavad Gītā* file plus an approximately 50k-token
Yoga corpus.

## Selection decisions

Both works are **foundational** sources, but they are handled differently:

- **The *Bhagavad Gītā*** — included in full despite being modestly above the nominal
  ~50k-token per-document cap. Keeping all 18 chapters preserves the text's complete
  progression through action, knowledge, meditation, devotion, the nature of the self,
  divine manifestation, the three guṇas, duty, renunciation, and liberation. The integrated
  commentary is retained because it supplies interpretive context rather than merely a bare
  translation.
- **The *Yoga-System of Patañjali*** — the complete 310.5k-token Harvard source is too large
  for the per-document budget, so it is reduced to approximately 50k tokens by a
  source-specific extractor. The complete standalone English translation of all four pādas
  of the *Yoga Sūtras* is preserved first. The remaining budget is filled with the most
  relevant interpretive passages from the *Yoga-bhāṣya* attributed to Vyāsa,
  Vācaspati Miśra's *Tattva-vaiśāradī*, and Woods's explanatory apparatus.
- **Coverage safeguards** — the Yoga extraction is balanced across all four pādas and
  prioritizes restraint of mental fluctuations, the seer, practice and dispassion,
  concentration and samādhi, Īśvara, afflictions, karma and latent impressions, suffering,
  yama and niyama, the eight limbs, attention and meditation, extraordinary powers and their
  dangers, discernment between *puruṣa* and *prakṛti*, and liberation.

### Interpretive works (interpretation matters for distillation quality)

No separate Yoga commentary is required because Woods's Harvard volume already contains
three connected textual layers:

1. Patañjali's complete root sūtras;
2. the complete *Yoga-bhāṣya*, traditionally attributed to Vyāsa;
3. Vācaspati Miśra's *Tattva-vaiśāradī*, explaining the *Yoga-bhāṣya*.

The extraction is **not a prose summary**. It preserves the complete translated root sūtras
and selects verbatim passages from the two commentarial layers. The score report should be
checked after extraction to confirm representation from all four pādas and substantial
material classified as `yoga_bhasya`, `tattva_vaisaradi`, or `mixed_commentary`.

The *Bhagavad Gītā* source is presented by Sacred Texts as Swami Swarupananda's translation
and commentary. Sacred Texts notes a historical attribution question involving Sister
Nivedita; the repository follows the edition's published attribution while preserving this
caveat in provenance metadata if a manifest is maintained.

## Conversion notes

The *Bhagavad Gītā* was converted from the complete 1909 Sacred Texts edition, with site
navigation and boilerplate removed while preserving the translation and commentary. The
Yoga source was obtained from the **HathiTrust Digital Library copy of the 1914 Harvard
University Press edition**, not from a later abridgement or modern paraphrase.

For the Yoga volume, scan/OCR boilerplate, isolated page numbers, and obvious OCR artifacts
may be removed, and simple line-break hyphenation may be repaired. Selected passages remain
verbatim and are restored to their original source order. Public-domain status is stated for
the United States; users elsewhere should check local copyright rules.
