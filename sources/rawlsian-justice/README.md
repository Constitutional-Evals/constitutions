# Foundational documents for `rawlsian-justice`

This bundle supplies the source texts the `rawlsian-justice` anchor constitution is distilled
from. It is built around an unavoidable constraint and a deliberate solution.

## The constraint: the three named sources are all copyrighted

The constitution's appendix names three modern, in-copyright works. **None of their text is
stored anywhere in this repo** (not even in `_private/`):

| Work | Publisher | Status |
|---|---|---|
| John Rawls, *A Theory of Justice* (1971) | Harvard UP / Belknap | copyright-withheld, metadata only |
| John Rawls, *Political Liberalism* (1993) | Columbia UP | copyright-withheld, metadata only |
| T. M. Scanlon, *What We Owe to Each Other* (1998) | Harvard UP / Belknap | copyright-withheld, metadata only |

For each, `manifest.json` carries `redistributable: false`, `files: []`, a publisher URL, and a
short (<200-word) fair-use characterization of its key ideas, so the distillation still has a
conceptual anchor even though the text is absent:

- **A Theory of Justice** — the original position, the veil of ignorance, justice as fairness, the
  two principles (equal basic liberties; fair equality of opportunity + the difference principle),
  the priority rules, reflective equilibrium, primary goods, the critique of utilitarianism.
- **Political Liberalism** — the fact of reasonable pluralism, the political vs. comprehensive
  conception, overlapping consensus, public reason.
- **What We Owe to Each Other** — contractualism (an act is wrong if it violates principles no one
  could reasonably reject), the separateness of persons, mutual justifiability.

Two interpretive/secondary works (Freeman's *Rawls*; the *Cambridge Companion to Rawls*) are also
listed metadata-only, as orientation pointers for the human distiller.

## The solution: public-domain intellectual antecedents

Because the named sources cannot be committed, the **committable** part of the bundle is built from
the public-domain works Rawls explicitly builds on or defines his theory in relation to. These are
not substitutes for Rawls — they are the tradition his theory extends, and each maps onto a
specific Rawlsian device:

| Committed PD text | License / source | Rawlsian connection |
|---|---|---|
| `rousseau-social-contract.md` | PD, Cole trans. 1913, Gutenberg #46333 | The social-contract lineage Rawls revives; the *general will* as an ancestor of a will oriented to the common good under fair procedure. |
| `hume-of-justice.md` | PD, Gutenberg #4320 | Rawls explicitly adopts Hume's *circumstances of justice* (moderate scarcity + limited altruism) as the background conditions of the original position. |
| `smith-moral-sentiments.md` | PD, Gutenberg #58559 | Smith's *impartial spectator* — judging conduct from a well-informed, impartial standpoint — is a recognized ancestor of the original position's move to strip away partiality. |

**Kant and Mill were deliberately not added here.** Rawls's Kantian constructivism and his running
argument against Mill/utilitarianism are both justice-relevant, but that material overlaps the
separate `kantian-deontology` and `mill-utilitarianism` anchors in this project. To avoid
duplicating those bundles, this bundle keeps Rousseau + Hume + Smith as its core trio. If the
distillation later needs the utilitarian foil or the Kantian grounding, pull the justice-specific
excerpts from those sibling bundles rather than re-adding them here.

## Selection & cleaning

Each committed text is trimmed to the portions most relevant to Rawlsian justice (rationale in each
file's header and in `manifest.json`) and converted to clean Markdown: Gutenberg boilerplate,
footnote apparatus, and page-number markers removed; hard-wrapped lines reflowed to paragraphs.
Bundle total ≈ 301k characters (~75k tokens), under the 120k-token cap; each document is under the
50k-token per-document cap.

- `rousseau-social-contract.md` — 97,935 chars (Books I, II, IV.i–ii)
- `hume-of-justice.md` — 36,594 chars (Enquiry, Section III complete)
- `smith-moral-sentiments.md` — 166,597 chars (Part I.i and Part III selections)

Working files (raw downloads, extraction script) are in `_private/` (gitignored).

## Open question for the human reviewer

Is the PD-antecedent strategy the right weighting, or should the bundle instead lean on short
fair-use *excerpts* of the actual Rawls/Scanlon text (a few paragraphs each, clearly within fair
use) so the distillation anchors on Rawls's own words rather than only on his predecessors? The
current bundle takes the conservative path: zero copyrighted text, antecedents + fair-use
characterizations only.
