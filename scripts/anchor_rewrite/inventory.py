#!/usr/bin/env python3
"""Inventory of rewrite flags over the 24 anchors.

Flags per item (criteria and guidelines):
  prefix   : criteria only: text does not start with "Prefer the response that" (guidelines keep their own form)
  overload : words >= 45  or  words/10 + 3*exception_clauses + 2*semicolons >= 7.5

Usage:  inventory.py [ANCHOR_DIR] [--json OUT] [--full]
"""
import json, glob, os, re, sys, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(HERE, "..", "..", "Provisional Constitutions", "Provisional Anchors")
PREFIX = "Prefer the response that "
CLAUSE = re.compile(r"\b(until|unless|except|only if|only when|even if|even when|however|"
                    r"but not|not at the cost|but where|but when|but if|; then|then favou?r)\b", re.I)

def score(t):
    w = len(t.split())
    k = len(CLAUSE.findall(t))
    s = w / 10 + 3 * k + 2 * t.count(";")
    return w, k, round(s, 1)

def flags(t, sec="criteria"):
    w, k, s = score(t)
    f = []
    if sec == "criteria" and not t.startswith(PREFIX): f.append("prefix")
    if w >= 45 or s >= 7.5: f.append("overload")
    return f, w, k, s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?", default=DEFAULT_DIR)
    ap.add_argument("--json"); ap.add_argument("--full", action="store_true")
    ap.add_argument("--only", help="substring filter on anchor label")
    a = ap.parse_args()
    out, tot = {}, {"prefix": 0, "overload": 0, "items": 0}
    for f in sorted(glob.glob(os.path.join(a.dir, "*.json"))):
        label = os.path.basename(f)[:-5]
        if a.only and a.only.lower() not in label.lower(): continue
        j = json.load(open(f, encoding="utf-8"))
        rows = []
        for sec in ("criteria", "guidelines"):
            for k, it in enumerate(j.get(sec) or [], 1):
                t = it["comparative"] if isinstance(it, dict) else it
                fl, w, kc, s = flags(t, sec)
                rows.append({"id": f"{sec}#{k}", "flags": fl, "words": w, "clauses": kc, "score": s, "text": t})
                tot["items"] += 1
                for x in fl: tot[x] += 1
        out[label] = rows
        nflag = [r for r in rows if r["flags"]]
        print(f"## {label}  ({len(j['criteria'])}c/{len(j.get('guidelines') or [])}g)  "
              f"prefix={sum('prefix' in r['flags'] for r in rows)} overload={sum('overload' in r['flags'] for r in rows)}")
        for r in (rows if a.full else nflag):
            tag = ",".join(r["flags"]) or "ok"
            print(f"  [{tag:16}] {r['id']:14} {r['words']:3}w s={r['score']:4}  {r['text']}")
    print(f"\nTOTAL items={tot['items']}  prefix-missing={tot['prefix']}  overload={tot['overload']}")
    if a.json: json.dump(out, open(a.json, "w"), indent=1, ensure_ascii=False)

if __name__ == "__main__":
    main()
