#!/usr/bin/env python3
"""Validate the Provisional Anchors against schema/constitution.schema.json (v1.2)."""
import json, glob, os, sys
from jsonschema import Draft202012Validator
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "anchors")
v = Draft202012Validator(json.load(open(os.path.join(ROOT, "schema", "constitution.schema.json"))))
bad = 0
for f in sorted(glob.glob(os.path.join(d, "*.json"))):
    errs = list(v.iter_errors(json.load(open(f, encoding="utf-8"))))
    if errs:
        bad += 1; print(f"FAIL {os.path.basename(f)}")
        for e in errs[:3]: print("   ", "/".join(map(str, e.absolute_path)), e.message[:120])
print(f"{bad} failing of {len(glob.glob(os.path.join(d, '*.json')))}")
