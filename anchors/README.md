# Anchors (basis-defining)

The constitutions the shared latent basis `R^D` is **jointly fit** on. Once the fit is locked,
any submitted constitution is scored against these axes **without refitting**.

The anchor set spans two kinds, both `in_basis: true` (you want the space to span aligned *and*
misaligned directions):

- **Value-tradition anchors** (24, per the proposal appendix) — breadth across religious,
  philosophical, secular-modern, and indigenous traditions. `valence: aligned`.
- **Misaligned anchors** (e.g. selfish power-seeking, unquestioning obedience) — deliberately
  misaligned value systems that define the "negative" directions of the space. `valence: misaligned`.
  These are also OCT *negative* targets; never use them as positive training targets.

Rules:
- Every file here has `role: anchor`, `in_basis: true`, and a `valence`.
- The set + versions defining the current basis are pinned in [`anchor-set.json`](anchor-set.json).
- **Editing any anchor after the basis is locked forces a refit and a new `basis_version`.**

Generation: one fixed meta-prompt (see [`../generation/`](../generation/)); 3-4 frontier models
distill each tradition from its foundational bundle in `../sources/<id>/`; drafts are critiqued
across models and reconciled to consensus; a researcher pass triages errors/anachronisms.

Note on placement: **Hinduism** is an anchor; **Ahimsa** (a distinctive variant) and
**Scientific Rationalism** live in `../supplementary/`, not here.
