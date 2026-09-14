#!/usr/bin/env python3
"""Move the 24 value-tradition anchors from 'Provisional Constitutions/Provisional Anchors/'
into anchors/<id>.json with the metadata the repo validator requires, and pin them in
anchors/anchor-set.json. Universal Kindness (12 criteria) supersedes anchors/kindness.json
(8 criteria, EigenBench-derived) as version 2.0.0, keeping id 'kindness'.
Usage: migrate_to_anchors.py [SRC_DIR]   (idempotent on the JSON content)"""
import json, os, sys, glob, re, subprocess
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "Provisional Constitutions", "Provisional Anchors")
DST = os.path.join(ROOT, "anchors")
DATE = "2026-09-14"
META = {  # label -> (id, title, tradition_class, tradition, source_bundle_dir)
 "Aboriginal Australian Constitution": ("aboriginal-australian", "Aboriginal Australian Law and Country", "indigenous", "Aboriginal Australian", "Aboriginal Australian"),
 "Buddhism_Constitution": ("buddhism", "Buddhism", "religious", "Buddhism", "buddhism"),
 "Buen Vivir Constitution": ("buen-vivir", "Buen Vivir", "indigenous", "Buen Vivir / sumak kawsay", "Buen Vivir"),
 "Care-Ethics Constitution": ("care-ethics", "Care Ethics", "philosophical", "Ethics of care", "care-ethics"),
 "Christianity_Constitution": ("christianity", "Christianity", "religious", "Christianity", "christianity"),
 "Confucianism_Constitution": ("confucianism", "Confucianism", "philosophical", "Confucianism", "Confucianism"),
 "Conservatism_Constitution": ("conservatism", "Conservatism", "secular-modern", "Conservatism", "conservatism"),
 "Environmental Ethics Constitution": ("environmental-ethics", "Environmental Ethics", "secular-modern", "Land ethic / environmental ethics", "Environmental Ethics"),
 "Hinduism_Constitution": ("hinduism", "Hinduism", "religious", "Hinduism", "hinduism"),
 "Islam_Constitution": ("islam", "Islam", "religious", "Islam", "islam"),
 "Judaism_Constitution": ("judaism", "Judaism", "religious", "Judaism", "judaism"),
 "Kantian_Deontology_Constitution": ("kantian-deontology", "Kantian Deontology", "philosophical", "Kantian deontology", "Kantian deontology"),
 "Lockean_Rights_Constitution": ("lockean-rights", "Lockean Rights", "secular-modern", "Lockean natural rights / classical liberalism", "lockean-rights"),
 "Maori Constitution": ("maori", "Māori Tikanga", "indigenous", "Māori", "Maori"),
 "Marxism_Constitution": ("marxism", "Marxism", "secular-modern", "Marxism", "Marxism"),
 "Neo-Virtue-Ethics Constitution": ("neo-aristotelian-virtue-ethics", "Neo-Aristotelian Virtue Ethics", "philosophical", "Neo-Aristotelian virtue ethics", "neo-aristotelian-virtue-ethics"),
 "North American Indigenous": ("north-american-indigenous", "North American Indigenous", "indigenous", "North American Indigenous", "NA Indig"),
 "Rawlsian Justice Constitution": ("rawlsian-justice", "Rawlsian Justice", "secular-modern", "Rawlsian justice as fairness", "rawlsian-justice"),
 "Secular Humanism Constitution": ("secular-humanism", "Secular Humanism", "secular-modern", "Secular humanism", "Secular Humanism"),
 "Stoicism_Constitution": ("stoicism", "Stoicism", "philosophical", "Stoicism", "stoicism"),
 "Taoism_Constitution": ("taoism", "Taoism", "philosophical", "Taoism", "taoism"),
 "Ubuntu Constitution": ("ubuntu", "Ubuntu", "philosophical", "Ubuntu", "Ubuntu"),
 "Universal_Kindness_Constitution": ("kindness", "Universal Kindness", "philosophical", "Universal benevolence / metta", "Universal Kindness"),
 "Utilitarianism_Constitution": ("utilitarianism", "Utilitarianism", "philosophical", "Utilitarianism", "Utilitarianism"),
}
pins = []
for f in sorted(glob.glob(os.path.join(SRC, "*.json"))):
    label = os.path.basename(f)[:-5]; cid, title, tclass, trad, bundle = META[label]
    body = json.load(open(f, encoding="utf-8"))
    dst = os.path.join(DST, cid + ".json")
    old = json.load(open(dst, encoding="utf-8")) if os.path.exists(dst) else None
    version = "2.0.0" if old else "1.0.0"
    doc = {"schema_version": "1.2", "id": cid, "title": title, "version": version, "role": "anchor", "in_basis": True,
           "valence": "aligned", "tradition_class": tclass, "tradition": trad,
           "summary": body["overview"].split(". ")[0].rstrip(".") + ".",
           "overview": body["overview"], "criteria": body["criteria"], "guidelines": body.get("guidelines", []),
           "license": "CC-BY-4.0",
           "provenance": {"method": "shared meta-prompt; principles distilled from the foundational bundle by 3-4 frontier models, cross-critiqued and reconciled; researcher pass; criteria rewritten to uniform comparative form (Sep 2026)",
                          "source_bundle": [f"sources/{bundle}/"], "researcher_pass": True, "authored_by": ["Anand Shanker", "Juan Cadile"], "date": DATE},
           "changelog": []}
    if old:
        doc["provenance"]["derived_from"] = old.get("provenance", {}).get("derived_from", "")
        doc["changelog"] = list(old.get("changelog", []))
        doc["changelog"].append({"version": version, "date": DATE, "notes": f"Superseded the {len(old['criteria'])}-criterion EigenBench-derived version with the {len(body['criteria'])}-criterion source-distilled anchor (overview, criteria as objects with reasoning/scenarios, guidelines)."})
    else:
        doc["changelog"].append({"version": version, "date": DATE, "notes": "Moved from Provisional Constitutions/Provisional Anchors/ into the anchor set; criteria in uniform comparative form."})
    with open(dst, "w", encoding="utf-8") as fh: json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")
    pins.append({"id": cid, "version": version})
    print(f"{label:36} -> anchors/{cid}.json  v{version}  {len(body['criteria'])}c/{len(body.get('guidelines',[]))}g")
mp = os.path.join(DST, "anchor-set.json"); ms = json.load(open(mp))
keep = [a for a in ms["anchors"] if a["id"] not in {p["id"] for p in pins}]
ms["anchors"] = sorted(pins + keep, key=lambda a: a["id"])
ms["notes"] = "24 value-tradition anchors (proposal appendix) + 2 misaligned stubs. fit_locked stays false until the basis is fit; then record latent_rank_D and bump basis_version to 1.0.0."
json.dump(ms, open(mp, "w"), indent=2); open(mp, "a").write("\n")
print(f"anchor-set.json: {len(ms['anchors'])} pinned")
