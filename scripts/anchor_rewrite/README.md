# Anchor rewrite (pre-freeze pass, Sep 2026)

Uniform comparative form for the 24 provisional anchors, per the 2026-08-31 meeting:
every criterion and guideline starts `Prefer the response that `, one commitment per
item, items of 45+ words or overload score >= 7.5 split (`words/10 + 3*exception clauses
+ 2*semicolons`). Guidelines of the form `X holds until Y; then Z` become
`Prefer the response that gives Z precedence over X when Y` (or a plain comparative).

```
originals/          frozen copies of the 24 anchors as of main@87cbdab (never edited)
rewrites/<label>.json   per-anchor spec: original index -> list of replacement texts
apply.py            originals + specs -> Provisional Constitutions/Provisional Anchors/ ; writes mapping.json
inventory.py [DIR]  flags per item (prefix / overload); --full prints everything
lint_specs.py       flags any spec text that would still fail the rules
validate_anchors.py [DIR]   validate against schema/constitution.schema.json (v1.2)
mapping.json        original item id -> new item id(s), for audit and for the blind-attribution baseline
variants/uk-v2/     content-level experiment on Universal Kindness (not applied to the main set; only the UK file kept, the other 23 were identical to the main set)
```

Reasoning and scenarios of a split item are inherited by both halves unless the spec
assigns scenario indices explicitly. Nothing here is pushed; branch `juancadile/anchor-rewrite`.

Result: 408 -> 475 items, 0 prefix flags, 0 overload flags, 24/24 validate under schema 1.2.
Blind-attribution re-measurement lives in `~/Documents/01-Academic/Levine/blind-attribution/runs/`.
