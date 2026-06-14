# Versioning & the frozen-spec contract

## Per-constitution versioning

Each constitution carries a semantic `version` (`MAJOR.MINOR.PATCH`).

- A published version is **immutable**. Never edit criteria in place.
- Any change = a **new version** + a new entry in that constitution's `changelog`.
- Scores are always published **against a specific version**, so they remain reproducible
  and comparable across time.

Suggested bump semantics:
- **PATCH** — typo/wording fix that does not change meaning.
- **MINOR** — added/clarified criterion that is backward-compatible in intent.
- **MAJOR** — a criterion changes meaning, or criteria are removed/reordered.

## Anchor-set (basis) versioning

The shared latent basis `R^D` is fit jointly on the 24 anchors. The exact set + versions
that define a given basis are pinned in [`anchors/anchor-set.json`](anchors/anchor-set.json)
as a `basis_version`.

- While `fit_locked: false`, the anchor set is still being assembled (current phase).
- Once `fit_locked: true`, **any** change to **any** anchor (even a PATCH) requires a new
  `basis_version` and a refit, because the coordinate system has moved.
- User-submitted, supplementary, benevolent-trait, and personalized constitutions are scored
  *against* a basis version; they never alter it.

## Releases

Cut a Git tag per release (e.g. `anchors-v1.0.0`, or a repo-wide `vX.Y.Z`). Each release is a
citable, immutable snapshot; attach a DOI (Zenodo) when the set is published. Downstream code
pins to a tag.
