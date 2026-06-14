#!/usr/bin/env python3
"""Validate constitutions against the schema, enforce folder<->role consistency, check the
anchor-set manifest, and guard against committing non-redistributable source text."""
import json, sys, pathlib
from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parent.parent
FOLDER_ROLE = {
    "anchors": "anchor",
    "benevolent-traits": "benevolent-trait",
    "supplementary": "supplementary",
    "personalized": "personalized",
}
SKIP = {"anchor-set.json", "manifest.json", "manifest.template.json"}
errors = []

con_validator = Draft202012Validator(json.loads((ROOT / "schema" / "constitution.schema.json").read_text()))
seen = {}
for folder, role in FOLDER_ROLE.items():
    d = ROOT / folder
    if not d.exists():
        continue
    for f in sorted(d.glob("*.json")):
        if f.name.startswith("_") or f.name in SKIP:
            continue
        try:
            data = json.loads(f.read_text())
        except Exception as e:
            errors.append(f"{f}: invalid JSON: {e}"); continue
        for err in con_validator.iter_errors(data):
            errors.append(f"{f}: {err.message}")
        if data.get("role") != role:
            errors.append(f"{f}: role '{data.get('role')}' but lives in {folder}/ (expected '{role}')")
        if data.get("id") and f.stem != data["id"]:
            errors.append(f"{f}: filename does not match id '{data['id']}'")
        if data.get("id"):
            seen.setdefault(folder, {})[data["id"]] = data.get("version")

# anchor-set manifest
mp = ROOT / "anchors" / "anchor-set.json"
if mp.exists():
    av = Draft202012Validator(json.loads((ROOT / "schema" / "anchor-set.schema.json").read_text()))
    manifest = json.loads(mp.read_text())
    for err in av.iter_errors(manifest):
        errors.append(f"anchor-set.json: {err.message}")
    anchors_seen = seen.get("anchors", {})
    for e in manifest.get("anchors", []):
        if e.get("id") not in anchors_seen:
            errors.append(f"anchor-set.json references unknown anchor '{e.get('id')}'")
        elif anchors_seen[e["id"]] != e.get("version"):
            errors.append(f"anchor-set.json pins {e['id']}@{e.get('version')} but file is @{anchors_seen[e['id']]}")
    # (No hard count check: the anchor set is 24 value-traditions PLUS misaligned anchors.)

# sources copyright guard: non-redistributable sources must not list committed files
srcdir = ROOT / "sources"
if srcdir.exists():
    for mf in sorted(srcdir.glob("*/manifest.json")):
        man = json.loads(mf.read_text())
        for s in man.get("sources", []):
            if not s.get("redistributable", False) and s.get("files"):
                errors.append(f"{mf}: source '{s.get('title')}' is redistributable:false but lists committed files {s['files']} (keep them in _private/)")

if errors:
    print("VALIDATION FAILED:\n  - " + "\n  - ".join(errors)); sys.exit(1)
print("All constitutions valid.")
