# Foundational documents for the `taoism` anchor

Source texts the `taoism` constitution is distilled from. The bundle uses James Legge's
complete public-domain translation of the *Tao Te Ching* and the received 33-book
*Zhuangzi*, together with his introductions, explanatory notes, appendices, and
supplementary Daoist texts. The two full source volumes are converted to clean Markdown
before a relevance-and-coverage extractor selects approximately 50k tokens from each.

## The bundle

| File | Work | Translation / interpretation | Source | License | ~tokens |
|------|------|------------------------------|--------|---------|--------:|
| `TTC + Zhuangzhi P1.md` | Legge, *The Texts of Taoism*, SBE 39: complete *Tao Te Ching* and *Zhuangzi* Books I–XVII, with introductions and notes | James Legge, 1891 | [Sacred Texts: SBE 39](https://www.sacred-texts.com/tao/sbe39/index.htm) | [Public domain in the U.S.](https://www.sacred-texts.com/cnote.htm) | 315.4k → ~50k |
| `Zhuangzhi P2.md` | Legge, *The Texts of Taoism*, SBE 40: *Zhuangzi* Books XVIII–XXXIII, supplementary Daoist texts, appendices, and index | James Legge, 1891 | [Sacred Texts: SBE 40](https://www.sacred-texts.com/tao/sbe40/index.htm) | [Public domain in the U.S.](https://www.sacred-texts.com/cnote.htm) | 168.2k → ~50k |

Full sources total ≈ 483.6k tokens. The extracted Taoism bundle is targeted at approximately
100k tokens, split evenly across SBE 39 and SBE 40.

## Selection decisions

Both volumes are **foundational** sources and are much larger than the per-document size cap
(~50k tokens), so each is passed through a source-specific extractor. In brief:

- **SBE 39** — the full source contains the complete 81-chapter *Tao Te Ching*, Legge's
  general introduction to Daoism, his introduction to the *Zhuangzi*, *Zhuangzi* Books
  I–XVII, and interpretive or philological notes. The extractor prioritizes passages on
  *dao*, *de*, *wu wei*, naturalness, simplicity, humility, softness, emptiness,
  noncompetition, restrained government, perspectivism, transformation, usefulness and
  uselessness, skillful action, knowledge, language, life, and death.
- **SBE 40** — the full source completes the *Zhuangzi* with Books XVIII–XXXIII and adds the
  *Treatise of Actions and Their Retributions*, shorter Daoist texts, interpretive
  appendices, analyses attributed to Lin Hsi-kung, and other supporting material. The
  extractor prioritizes philosophically and ethically relevant passages while limiting
  indexes, long name lists, OCR debris, repetitive anecdotes, and purely technical
  philological discussion.
- **Cross-volume balance** — each volume receives its own ~50k-token budget so the shorter
  second volume and the later books of the *Zhuangzi* cannot be crowded out by SBE 39.
  Selected passages are returned to their original source order.

### Interpretive works (interpretation matters for distillation quality)

No separate modern commentary is stored. Legge's introductions, chapter notes, comparisons
with Chinese commentators, and the appendices in SBE 39–40 are included in the extraction
pool. These provide substantial interpretation, although they do not constitute a complete
line-by-line translation of a single traditional commentary such as Guo Xiang's.

Legge's nineteenth-century comparative and occasionally Christian framing is part of the
historical source and should not automatically be treated as the only or final account of
Daoist thought. The extractor therefore favors passages that clarify the internal reasoning
of the *Tao Te Ching* and *Zhuangzi* over comparisons that add little to the Daoist concepts
themselves.

## Conversion notes

The files were produced from the complete public-domain SBE 39–40 scans or OCR text.
Scan boilerplate, isolated page numbers, navigation text, and obvious OCR artifacts may be
removed; simple line-break hyphenation may be repaired. The extractor performs **verbatim
selection rather than prose summarization**: selected source passages are not paraphrased and
are restored to their original order. The unusual filename spelling `Zhuangzhi` is retained
to match the existing repository files; the conventional modern romanization is *Zhuangzi*.
