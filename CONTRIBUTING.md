# Contributing

## Adding or changing a constitution

1. Copy [`templates/constitution.template.json`](templates/constitution.template.json) into the
   folder matching its `role` (`anchors/`, `benevolent-traits/`, `supplementary/`,
   `personalized/`). Filename is `<id>.json`.
2. Fill in `overview`, `criteria` (comparative — the pipeline reads these), `voices`
   (first/second/third person for OCT), `guidelines`, and `provenance`.
   - Anchors: set `valence` (`aligned` / `misaligned`); misaligned anchors are negative OCT targets.
   - Personalized: include a `partner` block with `terms`.
3. Assemble foundational docs under `sources/<id>/` and record them in `sources/<id>/manifest.json`
   (see the copyright rule below). Reference the files used in `provenance.source_bundle`.
4. Generate with the single shared meta-prompt ([`generation/meta-prompt.md`](generation/meta-prompt.md));
   do not add a per-constitution coverage checklist.
5. Validate: `python scripts/validate.py`. Open a PR; the `governance` team reviews.

## Rules

- **Never edit a published constitution in place** — bump `version`, add a `changelog` entry.
- **Anchors are high-friction**: editing one after the basis is locked forces a refit + new
  `basis_version`. Flag it in the PR.
- **Copyright** (public repo): do not commit full text of copyrighted sources. Mark them
  `redistributable: false` in the manifest and keep working `.md` in `sources/<id>/_private/`
  (gitignored). CI fails if a non-redistributable source lists committed files.
- **Personalized** content stays under its partner's terms; never relicense as CC-BY.

CI runs schema + role + manifest + copyright checks on every PR.
