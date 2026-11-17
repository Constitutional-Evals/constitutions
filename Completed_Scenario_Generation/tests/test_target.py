import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from modules import config as cfg
from modules.core import initialize_workspace, read_json
from modules.pipeline import run_pipeline


class StubClient:
    def __init__(self):
        self.m3_inputs = []
        self.generation_inputs = []

    def chat(self, model, prompt, payload, validate):
        if prompt == cfg.PROMPTS["m3"]:
            self.m3_inputs.append(payload)
            result = {"picks": [{"constitution": "kindness", "id": 1, "why": "Plausible tension"}]}
        elif prompt == cfg.PROMPTS["generate"]:
            self.generation_inputs.append(payload)
            result = {"candidates": [{
                "slot_id": slot["slot_id"],
                "scenario": (
                    "Our town can build a new flood barrier this year or use the same funds "
                    "to raise the houses in the most exposed area. How should we decide?"
                ),
            } for slot in payload["slots"]]}
        elif prompt == cfg.PROMPTS["quality"]:
            result = {"scores": dict.fromkeys(cfg.QUALITY_DIMS, 90), "reason": "Pass"}
        elif prompt == cfg.PROMPTS["relevance"]:
            matches = [{"id": 1, "evidence": "The decision affects residents."}]
            result = {"matches": [] if payload["constitution_id"] == "rights" else matches}
        else:
            raise AssertionError(f"Unexpected prompt: {prompt}")
        validate(result)
        return result

    def embeddings(self, texts):
        return np.eye(len(texts))


class TargetCoverageTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.pool = Path(temporary.name) / "pool.json"
        self.pool.write_text(json.dumps({"constitutions": {
            "oct-goodness": {"criteria": ["Avoid long-term harm to humanity."]},
            "kindness": {"criteria": ["Help the people most immediately in need."]},
            "rights": {"criteria": ["Protect freedom of conscience."]},
        }}), encoding="utf-8")
        settings = patch.multiple(
            cfg, CONSTITUTION_INPUT=str(self.pool), EXISTING_BANK_INPUT="",
            TARGET_CONSTITUTION="OCT Goodness", LOCAL_RUN_PARENT=temporary.name, RUN_NAME="test",
            SCENARIO_QUOTA=1, MIN_DISTINCT_CRITERIA=1, GENERATION_BATCH_SIZE=1,
            MAX_NEW_ATTEMPTS=3,
        )
        settings.start()
        self.addCleanup(settings.stop)

    def test_target_limits_coverage_and_preserves_m3_pool(self):
        root, pool, bank = initialize_workspace()
        client = StubClient()
        result = run_pipeline(root, pool, bank, client)

        self.assertEqual(result["progress"]["attempts"], 1)
        self.assertTrue(result["optimizer"]["feasible"])
        self.assertEqual([row["constitution"] for row in result["report"]], ["oct-goodness"])
        self.assertEqual(len(client.m3_inputs), len(cfg.M3_MODELS))
        for payload in client.m3_inputs:
            self.assertEqual(payload["target"]["id"], "oct-goodness")
            self.assertEqual({card["constitution"] for card in payload["others"]}, {"rights", "kindness"})
        self.assertEqual(len(client.generation_inputs), 1)
        generation = client.generation_inputs[0]
        self.assertEqual(generation["slots"][0]["target_constitution"], "oct-goodness")
        self.assertEqual(generation["supplementary_criteria"][0]["constitution"], "kindness")
        self.assertEqual(result["selected"][0]["relevance"], {"oct-goodness": [1], "kindness": [1]})
        summary = read_json(root / "exports/run_summary.json")
        self.assertEqual((summary["constitutions"], summary["target_coverage"]), (3, 1))
        with patch.object(cfg, "TARGET_CONSTITUTION", "kindness"):
            with self.assertRaisesRegex(RuntimeError, "settings changed"):
                initialize_workspace()

    def test_unknown_target_is_rejected_before_snapshot(self):
        with patch.object(cfg, "TARGET_CONSTITUTION", "missing"):
            with self.assertRaisesRegex(ValueError, "Unknown target constitution 'missing'"):
                initialize_workspace()
        self.assertFalse((self.pool.parent / cfg.RUN_NAME / "inputs/constitutions.json").exists())

    def test_no_target_uses_all_constitutions(self):
        with patch.multiple(cfg, TARGET_CONSTITUTION="", MAX_NEW_ATTEMPTS=0):
            root, pool, bank = initialize_workspace()
            result = run_pipeline(root, pool, bank, StubClient())
            self.assertNotIn("target_constitution", read_json(root / "run_manifest.json")["settings"])
            self.assertEqual({row["constitution"] for row in result["report"]}, set(pool))
            self.assertEqual(read_json(root / "exports/run_summary.json")["target_coverage"], 3)
