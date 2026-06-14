# Constitutional Evals — Constitutions

The governed constitution set underlying the **Constitutional Evals** benchmark and the
EigenBench v2 pipeline. The single source of truth for the value systems used to fit and query
the shared latent basis. Downstream code consumes *released, versioned* constitutions from here.

## Layout

| Folder | Role | In basis? | Purpose |
|---|---|---|---|
| [`anchors/`](anchors/) | `anchor` | **yes** | The set the latent basis `R^D` is jointly fit on: 24 value-tradition anchors (proposal appendix) **plus misaligned anchors** (selfish power-seeking, unquestioning obedience) marked `valence: misaligned`. |
| [`benevolent-traits/`](benevolent-traits/) | `benevolent-trait` | no | Project-authored frozen specs (loyalty-to-user, love-of-humanity, care-about-externalities); also scored against the basis. |
| [`supplementary/`](supplementary/) | `supplementary` | no | Value systems scored against the basis but not setting it (e.g. Ahimsa, Scientific Rationalism). Expected to grow into the hundreds. |
| [`personalized/`](personalized/) | `personalized` | no | Partner-supplied constitutions (e.g. NYC City Council / Qwen). Per-item license/terms — **not** CC-BY by default. |
| [`sources/`](sources/) | — | — | Foundational documents (.md) each constitution is distilled from, with a redistributable/license guard. |
| [`generation/`](generation/) | — | — | The single shared meta-prompt + generation methodology. |

Only `anchors/` defines the reference frame; everything else is measured *against* it.

## Constitution format

Each constitution carries an `overview`, comparative `criteria` (`"Prefer the response that ..."`,
consumed by the EigenBench judges), `voices` (first/second/third-person phrasings of the same
criteria, used as OCT character-training inputs), and `guidelines` (edge cases). See the
[schema](schema/constitution.schema.json) and [`templates/`](templates/constitution.template.json).

## Frozen-spec contract

Every constitution is immutable per version; revisions make a new version + changelog entry, so
any published score stays reproducible. See [`VERSIONING.md`](VERSIONING.md). The basis is pinned
to a specific anchor set + versions via [`anchors/anchor-set.json`](anchors/anchor-set.json).

## Consuming

`python scripts/build_dist.py` emits `dist/<role>/<id>.json` (comparative criteria, EigenBench
format) and `dist/<role>/<id>.oct.json` (OCT voices). Pin to a release tag, not `main`.

## Licensing

`anchors/`, `benevolent-traits/`, `supplementary/` are **CC-BY-4.0**. `personalized/` follows
per-item `partner.terms`. **Foundational sources may be copyrighted — do not commit
non-redistributable full text to this public repo** (see [`sources/README.md`](sources/README.md));
CI enforces it. Attributions in [`NOTICE.md`](NOTICE.md).

## Status

Interim core-team maintenance; expert co-authoring + update-cadence governance are scoped as
follow-up. See [`GOVERNANCE.md`](GOVERNANCE.md).
