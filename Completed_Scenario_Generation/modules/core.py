"""JSON input normalization, run manifests, and coverage utilities."""

import hashlib
import json
import os
import re
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from . import config as cfg

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def atomic_json(path, value):
    """Write complete JSON atomically; interrupted runs leave prior files intact."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(value, file, indent=2, ensure_ascii=False)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")


def normalized_text(value):
    return " ".join(value.split()).casefold()


def word_count(value):
    return len(re.findall(r"\b[\w'-]+\b", value))


def criterion_id(value):
    """Use integer IDs where possible; preserve identifiers such as 'C07'."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError(f"Invalid criterion ID: {value!r}")
    value = value.strip() if isinstance(value, str) else value
    if not value:
        raise ValueError("Empty criterion ID")
    value = int(value) if str(value).isdecimal() else value
    if isinstance(value, int) and value < 1:
        raise ValueError("Criterion IDs must be positive")
    return value


def sort_criterion_ids(ids):
    return sorted(ids, key=lambda k: (0, k) if isinstance(k, int) else (1, str(k)))


def check_is_str(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or empty {label}")
    return value.strip()


def check_config():
    if len(cfg.GENERATION_MODELS) != 3 or len(set(cfg.GENERATION_MODELS)) != 3:
        raise ValueError("Specify three distinct generators/development judges")
    if not 1 <= len(cfg.RELEVANCE_JUDGES) <= 2:
        raise ValueError("Specify one or two relevance judges")
    if not 1 <= cfg.GENERATION_BATCH_SIZE <= 50 or cfg.MAX_NEW_ATTEMPTS < 0:
        raise ValueError("Invalid generation budget or batch size")
    if cfg.MAX_REVISION_CYCLES not in (0, 1):
        raise ValueError("Revision cycles must be 0 or 1")
    if not 0 <= cfg.REDUNDANCY_COSINE_THRESHOLD <= 1:
        raise ValueError("Redundancy cosine threshold must be between 0 and 1")
    if not 0 <= cfg.REDUNDANCY_LLM_THRESHOLD <= 100:
        raise ValueError("Redundancy LLM threshold must be between 0 and 100")
    if cfg.SCENARIO_QUOTA < 1 or cfg.MIN_DISTINCT_CRITERIA < 1:
        raise ValueError("Invalid coverage quota")
    if cfg.WORKERS < 1 or cfg.HTTP_RETRIES < 1 or cfg.TARGET_MAX_WORDS > cfg.HARD_MAX_WORDS:
        raise ValueError("Invalid worker, retry, or word-limit settings")
    if not cfg.RUN_NAME or re.fullmatch(r"[a-z0-9_-]+", cfg.RUN_NAME) is None:
        raise ValueError("RUN_NAME must use lowercase letters, digits, hyphens or underscores")


check_config()

def load_named_documents(path):
    """Read JSONs from one file, a directory, or a ZIP archive."""
    path = Path(path)
    if path.is_dir():
        return [(p.stem, json.loads(p.read_text(encoding="utf-8")))
                for p in sorted(path.rglob("*.json"))]
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = sorted(n for n in archive.namelist() if n.endswith(".json"))
            return [(Path(n).stem, json.loads(archive.read(n))) for n in names]
    if path.suffix.lower() == ".json":
        return [(path.stem, json.loads(path.read_text(encoding="utf-8")))]
    raise ValueError(f"Expected a JSON file, ZIP, or folder: {path}")


def normalized_criteria(raw):
    if isinstance(raw, dict):
        raw = [{"id": k, "text": v} for k, v in raw.items()]
    if not isinstance(raw, list) or not raw:
        raise ValueError("Constitution requires a nonempty criteria list")

    criteria = []
    for index, entry in enumerate(raw, 1):
        if isinstance(entry, str):
            text, key = entry, index
        elif isinstance(entry, dict):
            text = next((entry[k] for k in
                         ("comparative", "statement", "text", "criterion", "description")
                         if isinstance(entry.get(k), str) and entry[k].strip()), None)
            key = entry.get("id", index)
        else:
            raise ValueError(f"Invalid criterion: {entry!r}")
        criteria.append({"id": criterion_id(key), "text": check_is_str(text, "criterion")})
    if len({x["id"] for x in criteria}) != len(criteria):
        raise ValueError("Duplicate criterion IDs")
    return criteria


def load_constitutions(path):
    result = {}
    for filename, data in load_named_documents(path):
        collection = data.get("constitutions") if isinstance(data, dict) else None
        if isinstance(collection, dict):
            entries = collection.items()
        elif isinstance(collection, list):
            entries = [(x.get("id", x.get("name")), x) for x in collection]
        else:
            entries = [(filename, data)]
        for name, item in entries:
            if not isinstance(item, dict) or "criteria" not in item:
                raise ValueError(f"Invalid constitution {name}")
            key = slug(name)
            if not key or key in result:
                raise ValueError(f"Duplicate or empty constitution ID: {key}")
            result[key] = {
                "id": key,
                "name": str(item.get("name") or name),
                "criteria": normalized_criteria(item["criteria"]),
                "guidelines": item.get("guidelines", []),
                "other_context": {k: v for k, v in item.items()
                                  if k not in {"name", "criteria", "guidelines"}},
            }
    if not result:
        raise ValueError("No constitutions found")
    return dict(sorted(result.items()))


def coerce_ids(values, name, const):
    """Validate imported criterion IDs against a constitution."""
    if values is None:
        return []
    if isinstance(values, dict):
        values = values.get("criterion_ids", values.get("criteria", []))
    if not isinstance(values, (list, tuple, set)):
        raise ValueError(f"Expected a criterion list for {name}")
    allowed = {x["id"] for x in const[name]["criteria"]}
    ids = {criterion_id(x["id"] if isinstance(x, dict) else x) for x in values}
    if not ids <= allowed:
        raise ValueError(f"Unknown criteria for {name}: {ids - allowed}")
    return sort_criterion_ids(ids)


def load_existing_bank(path, const):
    if not path:
        return []
    documents = load_named_documents(path)
    records = {}
    # Unlabeled text arrays must still be evaluated, even if their filenames match.
    def entries(data):
        if isinstance(data, dict):
            data = data.get("scenarios", data.get("benchmark", data.get("rows", [data])))
        return data

    complete_export = (
        {slug(name) for name, _ in documents} == set(const)
        and all(isinstance(item, dict) and ("criteria" in item or "relevance" in item)
                for _, data in documents for item in entries(data))
    )

    for filename, data in documents:
        data = entries(data)
        if not isinstance(data, list):
            raise ValueError(f"Expected scenario array in {filename}")
        file_const = slug(filename) if slug(filename) in const else None
        for item in data:
            item = {"scenario": item} if isinstance(item, str) else item
            if not isinstance(item, dict):
                raise ValueError(f"Invalid scenario in {filename}")
            scenario = check_is_str(item.get("scenario", item.get("text")), "scenario")
            text_key = normalized_text(scenario)
            if text_key not in records:
                records[text_key] = {
                    "scenario_id": str(item.get("scenario_id") or "import_" + digest(text_key)[:14]),
                    "scenario": scenario,
                    "relevance": {}, "_complete": complete_export,
                }
            row = records[text_key]
            row["_complete"] |= "relevance" in item
            for name, ids in (item.get("relevance") or {}).items():
                name = slug(name)
                if name not in const:
                    raise ValueError(f"Unknown constitution: {name}")
                current = set(row["relevance"].get(name, []))
                row["relevance"][name] = sort_criterion_ids(current | set(coerce_ids(ids, name, const)))
            if file_const and "criteria" in item:
                current = set(row["relevance"].get(file_const, []))
                row["relevance"][file_const] = sort_criterion_ids(
                    current | set(coerce_ids(item["criteria"], file_const, const)))

    rows = list(records.values())
    for row in rows:
        if row.pop("_complete"):
            for name in const:
                row["relevance"].setdefault(name, [])
    ids = [row["scenario_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("A scenario ID refers to multiple different texts")
    return rows


def sample_coverage(const, rows):
    counts, criteria = Counter(), defaultdict(Counter)
    for row in rows:
        for name, ids in row.get("relevance", {}).items():
            if ids:
                counts[name] += 1
                criteria[name].update(set(ids))
    return counts, criteria

def mount_workspace():
    root = Path(cfg.LOCAL_RUN_PARENT).expanduser() / cfg.RUN_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def identity_settings():
    """Only changes to meaningful experiment settings invalidate saved runs."""
    return {
        "quota": cfg.SCENARIO_QUOTA, "breadth": cfg.MIN_DISTINCT_CRITERIA,
        "batch_size": cfg.GENERATION_BATCH_SIZE, "seed": cfg.SEED,
        "generation_rotation": cfg.GENERATION_MODELS,
        "development_policy": "other_two_models",
        "heldout": cfg.HELDOUT_JUDGE, "m3": cfg.M3_MODELS,
        "m3_supplementary_count": cfg.M3_SUPPLEMENTARY_COUNT,
        "relevance": cfg.RELEVANCE_JUDGES, "tie_breaker": cfg.RELEVANCE_TIEBREAKER,
        "redundancy": cfg.REDUNDANCY_JUDGE, "embedding": cfg.EMBEDDING_MODEL,
        "quality": [cfg.QUALITY_MIN_AVERAGE, cfg.QUALITY_MIN_DIMENSION,
                    cfg.REVISION_ELIGIBLE_AVERAGE, cfg.REVISION_ELIGIBLE_MIN_DIMENSION,
                    cfg.MAX_REVISION_CYCLES, cfg.MIN_WORDS, cfg.TARGET_MAX_WORDS, cfg.HARD_MAX_WORDS],
        "redundancy_rules": [cfg.REDUNDANCY_COSINE_THRESHOLD,
                             cfg.REDUNDANCY_LLM_THRESHOLD, cfg.MAX_REVIEW_PAIRS],
        "reasoning": cfg.REASONING_EFFORT,
        "prompt_hash": digest(cfg.PROMPTS),
        "system_message_hash": digest(cfg.SYSTEM_MESSAGE),
        "design_vocabulary_hash": digest({
            "quality_dimensions": cfg.QUALITY_DIMS,
            "scenario_types": cfg.SCENARIO_TYPES, "settings": cfg.SETTINGS}),
    }


def initialize_workspace():
    check_config()
    root = mount_workspace()
    inputs = root / "inputs"
    saved_const, saved_bank = inputs / "constitutions.json", inputs / "existing_bank.json"

    if saved_const.exists() and saved_bank.exists():
        const, bank = read_json(saved_const), read_json(saved_bank)
        for path, loader, saved in [
            (cfg.CONSTITUTION_INPUT, load_constitutions, const),
            (cfg.EXISTING_BANK_INPUT, lambda p: load_existing_bank(p, const), bank),
        ]:
            if path and Path(path).exists() and digest(loader(path)) != digest(saved):
                raise RuntimeError("Uploaded inputs differ from saved run. Use another RUN_NAME")
        print("Loaded saved input snapshots")
    else:
        const = load_constitutions(cfg.CONSTITUTION_INPUT)
        bank = load_existing_bank(cfg.EXISTING_BANK_INPUT, const)
        atomic_json(saved_const, const)
        atomic_json(saved_bank, bank)

    settings = identity_settings()
    signature = digest({"settings": settings, "constitutions": const, "bank": bank})
    manifest_path = root / "run_manifest.json"
    manifest = read_json(manifest_path)
    if manifest and manifest["identity"] != signature:
        raise RuntimeError("Saved inputs, prompts, or model settings changed; use another run name")
    if not manifest:
        atomic_json(manifest_path, {
            "identity": signature, "settings": settings,
            "constitution_ids": list(const), "input_bank_size": len(bank),
        })

    for folder in ("cache/chat", "cache/embeddings", "batches", "exports", "audit", "review"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    overrides = root / "review/manual_relevance_overrides.json"
    if not overrides.exists():
        atomic_json(overrides, [])
    return root, const, bank

