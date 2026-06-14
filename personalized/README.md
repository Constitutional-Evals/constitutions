# Personalized constitutions

Partner/client-supplied constitutions for bespoke engagements — e.g. character-training a
model for an external body on a constitution **they** supply (such as a Qwen model trained for
the New York City Council on a constitution the Council provides).

`role: personalized`, `in_basis: false`. These never affect the basis; they are scored
against it and/or used as character-training targets.

## Licensing — read this

**Personalized constitutions are NOT CC-BY by default.** Each carries its own terms in the
`partner` block (`partner.terms`). The content is supplied by, and typically remains the
property of, the partner. Do not redistribute, relicense, or publish a personalized
constitution without confirming `partner.terms`. If a partner requires confidentiality, keep
that constitution out of this public repo entirely.

Each file MUST include a `partner` block with at least `name` and `terms`.
