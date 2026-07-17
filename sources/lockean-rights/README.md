# Foundational documents for `lockean-rights`

Source texts distilled into the `lockean-rights` anchor constitution — a natural-rights ethic:
individuals hold **life, liberty, and property** as pre-political rights; the state is a limited
**fiduciary trust** instituted to protect those rights; its power is bounded by consent and the
rule of law; and its perversion into arbitrary or redistributive coercion is illegitimate.

## The bundle (committed, all public domain)

| File | Work | Selection |
|------|------|-----------|
| `locke-second-treatise-1-natural-law-and-property.md` | Locke, *Second Treatise of Government* (1689) — Part 1 | Ch. I–V |
| `locke-second-treatise-2-civil-society-and-dissolution.md` | Locke, *Second Treatise of Government* (1689) — Part 2 | Ch. VII–IX, XI, XVIII–XIX |
| `locke-letter-concerning-toleration.md` | Locke, *A Letter Concerning Toleration* (1689, Popple trans.) | full |
| `spencer-man-versus-the-state-selected.md` | Spencer, *The Man versus the State* (1884) | "The Coming Slavery"; "The Great Political Superstition" |

**Primary config** = the four files above ≈ **115k tokens** (under the 120k bundle cap); each
document is under the 50k-token per-document cap.

**Optional / supplementary (committed, public domain, NOT in the primary config):**

| File | Work | Selection |
|------|------|-----------|
| `bastiat-the-law.md` | Bastiat, *The Law* (*La Loi*, 1850, Stirling 1874 trans.) | full essay + Bastiat's footnotes |

Bastiat's *The Law* (~24k tokens) is committed and public domain, but adding it to the primary
config would push the bundle to ≈ 139k tokens, over the 120k cap. It is therefore held out of the
primary config: use it as a swap-in for, or an add-on alongside, Spencer (both carry the same
natural-rights / minimal-state / anti-plunder dimension).

## Selection decisions

**Locke, *Second Treatise* (the core text).** The full treatise is ~35k words / ~78k tokens,
over the 50k-token per-document cap. It is split into two files and reduced to the chapters most
load-bearing for a natural-rights ethic, following the appendix's guidance:

- **Part 1 — Natural law and property (Ch. I–V):** the definition of political power; the state
  of nature and the law of nature that binds it; the state of war; the limits of legitimate
  subjection (slavery); and the labour theory of property with its provisos. This is the
  foundation: individuals hold life, liberty, and estate as natural rights.
- **Part 2 — Civil society, trust, and revolution (Ch. VII–IX, XI, XVIII–XIX):** the origin of
  political society; its beginning by consent; the ends of government (preserving "property"
  broadly understood — lives, liberties, and estates); the extent of and limits on the
  legislative power, including government as a *fiduciary trust*, the rule of settled law, and no
  taxation without consent; tyranny as power exercised beyond right; and the dissolution of
  government and the people's right to resume power — the right of revolution.
- **Omitted:** Ch. VI (paternal power), X (forms of a commonwealth), and XII–XVII (the mechanics
  and derivation of executive/federative/prerogative powers, conquest, usurpation) — Locke's
  anti-Filmer and institutional material, less central to the rights core.

**Locke, *A Letter Concerning Toleration* — full.** Short and thematically essential: it supplies
the freedom-of-conscience and civil/religious-separation dimensions. Civil government exists only
to secure civil interests; the care of souls is not the magistrate's; coercion cannot produce
belief; toleration is the mark of the true church. Popple's 1689 English translation (public
domain).

**Herbert Spencer, *The Man versus the State* — the "Nozick fix."** The appendix names Robert
Nozick's *Anarchy, State, and Utopia* (1974) as a foundational source, but that work is under
copyright and cannot be reproduced in this public CC-BY repo. To carry the same libertarian /
minimal-state / natural-rights dimension **with a public-domain text**, the bundle substitutes two
essays from Spencer (d. 1903):

- **"The Coming Slavery"** — state-administered relief and the expansion of compulsory over
  voluntary cooperation as a slide toward servitude; coercively redistributing the products of
  some men's labour is a form of bondage. This is the public-domain ancestor of Nozick's claim
  that "taxation of earnings from labour is on a par with forced labour," and of the
  night-watchman critique of the redistributive state.
- **"The Great Political Superstition"** — rights are **not** the gift of parliaments or the
  state; the "divine right of parliaments" is a superstition; individual rights are pre-political
  and the state's authority is strictly bounded and instrumental. This parallels both Locke's
  natural rights and Nozick's rights-first framework.

**Bastiat, *The Law* — the appendix's first-choice PD candidate (now committed, optional).** An
earlier audit concluded that no clean pre-1930 English translation exists and that every available
English text is the copyrighted 1950 Dean Russell translation. That was a misidentification. The
text carried by Project Gutenberg #44800 is not the Russell translation but the **Patrick James
Stirling** translation first published in *Essays on Political Economy* (G. P. Putnam's Sons,
**1874**), which is public domain by age. (Diagnostic: Stirling opens *"The law perverted! The
law—and, in its wake, all the collective forces of the nation…"*; Russell opens *"The law
perverted! And the police powers of the state perverted along with it!"*.) The Stirling text and
Bastiat's own footnotes are now committed as `bastiat-the-law.md`; the 2007 Mises Institute
foreword (Thomas DiLorenzo), index, and cover matter — which carry a fresh 2007 copyright — were
stripped. It is held **optional** only for the token-budget reason above; Spencer remains the
in-config carrier of this dimension.

## Copyright status (this repo is public, CC-BY-4.0)

- **Committed (public domain):** the two Locke works and the Spencer essays (primary config), plus
  Bastiat's *The Law* in the 1874 Stirling translation (optional/supplementary). All pre-1930,
  with transcriptions carrying no new rights; the Bastiat file excludes the copyrighted 2007 Mises
  reset material (see above).
- **Metadata-only (`redistributable: false`, no text stored):**
  - **Nozick, *Anarchy, State, and Utopia* (1974)** — copyrighted (Basic Books); fair-use
    characterization only.
  - **A. John Simmons, *The Lockean Theory of Rights* (1992)** — copyrighted interpretive work.
- **Public-domain interpretive companion, listed but not committed** (to stay under the
  token cap): **Sterling P. Lamprecht, *The Moral and Political Philosophy of John Locke* (1918)**.

## Notes on transcription

- Locke texts: HTML/markup stripped, chapters reflowed into paragraphs, `Sect. N.` markers
  retained, chapter headings normalized to `## Chapter N — Title`.
- Spencer: OCR from the Internet Archive scan, cleaned — line-break hyphenation rejoined, running
  page-headers and page numbers removed, Spencer's bibliographic footnotes to his own works
  dropped; print-edition editorial `[bracketed]` insertions retained. Spot-checked: no HTML, no
  page numbers, no residual OCR junk. (A few cosmetic OCR typos remain, e.g. *primd facie*,
  *utiliarianism* — the text is unmistakably Spencer.)
- Bastiat: from Project Gutenberg #44800; the 2007 Mises front/back matter (DiLorenzo foreword,
  index, cover blurb) removed, keeping only Bastiat's 1874-Stirling essay text and his four
  footnotes; page markers `{N}` stripped, paragraphs reflowed across page breaks, ASCII `--`
  normalized to em dashes.
- Working files and build scripts are in `_private/` (gitignored). No copyrighted text is stored
  there — only public-domain source scans and the conversion scripts.
