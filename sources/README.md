# Foundational documents

The source texts each constitution is distilled from, one folder per constitution id
(e.g. `sources/ahimsa/`). Constitutions reference the exact files used via
`provenance.source_bundle`.

## Format & prep
- Convert every source to **Markdown** (`.md`). Check the Allen Institute's **OLMo** training
  data first \u2014 many foundational texts may already be available in clean, ingestible form.
- Cap each document at **50k tokens**; for longer texts, use a frontier LLM to extract the most
  relevant 50k. Cap each constitution's full bundle at **120k tokens**.
- **Spot-check** every `.md` for conversion quality (no garbled markup / stray formatting).
- **Multiple `.md` files per document is encouraged** (e.g. different translations of the
  Bhagavad Gita). Varying the selection, ordering, and formatting of the bundle is a sensitivity
  probe: it lets us measure how much formatting affects the final constitution.

## Each constitution folder has a manifest
`sources/<id>/manifest.json` records every source: URL, license, and whether its full text may
be redistributed. See [`manifest.template.json`](manifest.template.json).

## Copyright (this repo is PUBLIC)
**Do not commit the full text of copyrighted sources to this public repo.** Many foundational
texts are public domain (ancient scriptures, old translations) and can be stored in full. But
modern, copyrighted sources (e.g. recent translations, essays, manifestos, agency web pages)
must NOT be redistributed here. For those, set `redistributable: false` in the manifest and keep
the working `.md` in a local `sources/<id>/_private/` folder (gitignored) \u2014 store only the URL +
license + a short fair-use excerpt publicly. CI enforces this: a source marked
`redistributable: false` may not have committed text files.
