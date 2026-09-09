#!/usr/bin/env python3
"""Apply rewrite specs onto the frozen originals and write the rewritten anchors.

Spec file: rewrites/<label>.json
  {"criteria":   {"3": ["new text"], "4": ["part A", "part B"]},
   "guidelines": {"1": [{"comparative": "...", "scenarios": [0, 2]}, "..."]},
   "overview": "optional replacement"}

Each original index maps to a list of replacements inserted at that position.
A plain string inherits the original reasoning and scenarios; an object may
restrict `scenarios` to a list of original scenario indices. Items not listed
are copied unchanged. Writes mapping.json (original id -> new ids) for audit.

Usage: apply.py [--check]   (--check only reports, writes nothing)
"""
import json, os, sys, glob, copy

HERE = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(HERE, "originals")
SPECS = os.path.join(HERE, "rewrites")
DEST = os.path.join(HERE, "..", "..", "Provisional Constitutions", "Provisional Anchors")

def apply_one(doc, spec):
    out, mapping = copy.deepcopy(doc), {}
    if "overview" in spec: out["overview"] = spec["overview"]
    for sec in ("criteria", "guidelines"):
        repl = spec.get(sec, {})
        new = []
        for k, it in enumerate(doc.get(sec) or [], 1):
            key = str(k)
            if key not in repl:
                mapping[f"{sec}#{k}"] = [f"{sec}#{len(new)+1}"]; new.append(copy.deepcopy(it)); continue
            ids = []
            for r in repl[key]:
                item = copy.deepcopy(it)
                if isinstance(r, str):
                    item["comparative"] = r
                else:
                    item["comparative"] = r["comparative"]
                    if "scenarios" in r:
                        item["scenarios"] = [it["scenarios"][i] for i in r["scenarios"]]
                    if "reasoning" in r: item["reasoning"] = r["reasoning"]
                new.append(item); ids.append(f"{sec}#{len(new)}")
            mapping[f"{sec}#{k}"] = ids
        unknown = set(repl) - {str(i) for i in range(1, len(doc.get(sec) or []) + 1)}
        if unknown: raise SystemExit(f"spec refers to unknown {sec} index {unknown}")
        out[sec] = new
    return out, mapping

def main():
    check = "--check" in sys.argv
    allmap = {}
    for f in sorted(glob.glob(os.path.join(ORIG, "*.json"))):
        label = os.path.basename(f)[:-5]
        doc = json.load(open(f, encoding="utf-8"))
        sf = os.path.join(SPECS, label + ".json")
        if not os.path.exists(sf):
            continue
        spec = json.load(open(sf, encoding="utf-8"))
        new, mapping = apply_one(doc, spec)
        nc, ng = len(new["criteria"]), len(new.get("guidelines") or [])
        changed = sum(len(v) for s in ("criteria", "guidelines") for v in spec.get(s, {}).values())
        print(f"{label:40} {len(doc['criteria'])}c/{len(doc.get('guidelines') or [])}g -> {nc}c/{ng}g   ({changed} new items)")
        allmap[label] = mapping
        if not check:
            with open(os.path.join(DEST, label + ".json"), "w", encoding="utf-8") as fh:
                json.dump(new, fh, indent=2, ensure_ascii=False); fh.write("\n")
    if not check:
        json.dump(allmap, open(os.path.join(HERE, "mapping.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
