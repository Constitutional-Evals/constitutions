#!/usr/bin/env python3
"""Flag any rewritten text in rewrites/*.json that still fails the prefix/overload rules."""
import json, glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inventory import flags
bad = 0
for f in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rewrites", "*.json"))):
    sp = json.load(open(f, encoding="utf-8"))
    for sec in ("criteria", "guidelines"):
        for k, v in sp.get(sec, {}).items():
            for r in v:
                t = r if isinstance(r, str) else r["comparative"]
                fl, w, kc, s = flags(t)
                if fl: bad += 1; print(f"{os.path.basename(f)[:28]:28} {sec}#{k} {fl} {w}w s={s}  {t[:90]}")
print(f"{bad} problems")
