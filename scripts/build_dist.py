#!/usr/bin/env python3
"""Emit pipeline artifacts into dist/:
  dist/<role>/<id>.json       -> comparative criteria array (EigenBench `constitution.path`)
  dist/<role>/<id>.oct.json   -> {first_person, second_person, third_person} (OCT inputs), if present
plus dist/manifest.json."""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
FOLDERS = ["anchors", "benevolent-traits", "supplementary", "personalized"]
SKIP = {"anchor-set.json", "manifest.json", "manifest.template.json"}

index = []
for folder in FOLDERS:
    d = ROOT / folder
    if not d.exists():
        continue
    out = DIST / folder
    out.mkdir(parents=True, exist_ok=True)
    for f in sorted(d.glob("*.json")):
        if f.name.startswith("_") or f.name in SKIP:
            continue
        data = json.loads(f.read_text())
        (out / f.name).write_text(json.dumps(data["criteria"], indent=2, ensure_ascii=False))
        voices = data.get("voices")
        if voices:
            (out / f"{f.stem}.oct.json").write_text(json.dumps(voices, indent=2, ensure_ascii=False))
        index.append({
            "id": data["id"], "role": data["role"], "version": data["version"],
            "in_basis": data["in_basis"], "valence": data.get("valence"),
            "num_criteria": len(data["criteria"]), "has_voices": bool(voices),
            "path": f"{folder}/{f.name}",
        })

DIST.mkdir(exist_ok=True)
(DIST / "manifest.json").write_text(json.dumps({"constitutions": index}, indent=2))
print(f"Built {len(index)} constitutions into dist/")
