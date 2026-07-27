import json
import tempfile
import unittest
from pathlib import Path

from experiments.long_source_v3.evaluate import load_adjudicated_cases
from experiments.long_source_v3.run import (
    adaptive_cluster_order,
    cluster_batches,
    router_audit,
    run_iterative,
    set_similarity,
    validate_provenance,
)


class QueueClient:
    def __init__(self, responses):
        self.responses = list(responses)

    def chat_json(self, **_kwargs):
        if not self.responses:
            raise AssertionError("Unexpected model call")
        return self.responses.pop(0)


def cluster(index, source="a.md", kind="principle", weight=1.0, size=100):
    cluster_id = f"reference-{index:03d}"
    return {
        "cluster_id": cluster_id,
        "kind": "criterion" if kind == "principle" else "guideline",
        "synthesis": f"Distinct principle {index}",
        "source_paths": [source],
        "extractor_models": ["model-a", "model-b"],
        "atom_kinds": [kind],
        "support_count": 2,
        "weight": weight,
        "packet_chars": size,
        "candidate_ids": [f"atom-{index}"],
        "evidence": [
            {
                "candidate_id": f"atom-{index}",
                "source_path": source,
                "evidence": f"Evidence {index}",
            }
        ],
    }


def draft(ids):
    return {
        "overview": "Draft",
        "items": [
            {
                "kind": "criterion",
                "comparative": "Prefer the response that applies the principle.",
                "reasoning": "Grounded.",
                "questions": ["Prompt one?", "Prompt two?"],
                "cluster_ids": [ids[0]],
            }
        ],
        "observed_cluster_ids": ids,
    }


def final(ids):
    item = {
        "kind": "criterion",
        "comparative": "Prefer the response that applies one clear principle.",
        "reasoning": "Grounded.",
        "questions": ["Prompt one?", "Prompt two?"],
        "cluster_ids": [ids[0]],
    }
    guideline = {
        "kind": "guideline",
        "comparative": "When duties conflict, preserve the more basic duty.",
        "reasoning": "Grounded.",
        "questions": ["Conflict one?", "Conflict two?"],
        "cluster_ids": [ids[-1]],
    }
    return {
        "overview": "Final",
        "criteria": [dict(item) for _ in range(10)],
        "guidelines": [dict(guideline) for _ in range(4)],
        "observed_cluster_ids": ids,
    }


class BatchingTests(unittest.TestCase):
    def test_batches_preserve_every_cluster_in_order(self):
        clusters = [cluster(1, size=80), cluster(2, size=80), cluster(3, size=80)]

        batches = cluster_batches(clusters, max_chars=150)

        self.assertEqual(
            [[item["cluster_id"] for item in batch] for batch in batches],
            [["reference-001"], ["reference-002"], ["reference-003"]],
        )

    def test_adaptive_order_starts_with_conflicts_and_source_coverage(self):
        clusters = [
            cluster(1, source="a.md", weight=1),
            cluster(2, source="b.md", weight=4),
            cluster(3, source="a.md", kind="conflict", weight=2),
        ]

        ordered, reasons = adaptive_cluster_order(clusters, ["a.md", "b.md"])

        first = {item["cluster_id"] for item in ordered[:2]}
        self.assertEqual(first, {"reference-002", "reference-003"})
        self.assertIn(
            "high-confidence-conflict-or-exception",
            reasons["reference-003"],
        )


class ProvenanceTests(unittest.TestCase):
    def test_missing_observed_cluster_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "provenance mismatch"):
            validate_provenance(
                draft(["reference-001"]),
                {"reference-001", "reference-002"},
                {"reference-001", "reference-002"},
            )

    def test_iterative_merge_covers_all_batches(self):
        clusters = [cluster(1), cluster(2)]
        ids = ["reference-001", "reference-002"]
        client = QueueClient(
            [
                draft(["reference-001"]),
                draft(["reference-002"]),
                draft(ids),
                final(ids),
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            constitution, trace = run_iterative(
                Path(directory),
                client,
                "writer",
                "Test",
                clusters,
                batch_chars=100,
            )

        self.assertEqual(set(constitution["observed_cluster_ids"]), set(ids))
        self.assertTrue(trace["complete_input_coverage"])
        self.assertEqual(client.responses, [])

    def test_similarity_detects_identical_constitutions(self):
        self.assertEqual(
            set_similarity(final(["reference-001"]), final(["reference-001"])),
            1.0,
        )


class RouterAuditTests(unittest.TestCase):
    def test_router_audit_measures_omitted_reference_material(self):
        clusters = [cluster(1), cluster(2)]
        atoms = [
            {"candidate_id": "atom-1", "chunk_id": "chunk-1"},
            {"candidate_id": "atom-2", "chunk_id": "chunk-2"},
        ]
        manifest = {
            "selected_chunk_ids": ["chunk-1"],
            "selected_chunks": 1,
            "total_chunks": 2,
        }

        audit = router_audit(atoms, clusters, manifest)

        self.assertEqual(audit["available_atom_recall_from_selected_chunks"], 0.5)
        self.assertEqual(audit["routed_atom_recall"], 0.5)
        self.assertEqual(audit["represented_cluster_recall"], 0.5)
        self.assertEqual(audit["unrepresented_cluster_ids"], ["reference-002"])


class EvaluationGateTests(unittest.TestCase):
    def test_final_evaluation_rejects_pending_human_labels(self):
        cases = {
            "cases": [
                {
                    "case_id": "case-01",
                    "cluster_id": "reference-001",
                    "prompt": "P",
                    "response_a": "A",
                    "response_b": "B",
                    "author_intended_aligned": "A",
                }
            ]
        }
        labels = {
            "annotations": [
                {
                    "case_id": "case-01",
                    "status": "pending",
                    "adjudicated_label": None,
                }
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            cases_path = Path(directory) / "cases.json"
            labels_path = Path(directory) / "labels.json"
            cases_path.write_text(json.dumps(cases), encoding="utf-8")
            labels_path.write_text(json.dumps(labels), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not accepted"):
                load_adjudicated_cases(cases_path, labels_path)

    def test_final_evaluation_requires_two_annotators(self):
        cases = {
            "cases": [
                {
                    "case_id": "case-01",
                    "cluster_id": "reference-001",
                    "prompt": "P",
                    "response_a": "A",
                    "response_b": "B",
                    "author_intended_aligned": "A",
                }
            ]
        }
        labels = {
            "annotations": [
                {
                    "case_id": "case-01",
                    "annotator_1": "A",
                    "annotator_2": None,
                    "status": "accepted",
                    "adjudicated_label": "A",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            cases_path = Path(directory) / "cases.json"
            labels_path = Path(directory) / "labels.json"
            cases_path.write_text(json.dumps(cases), encoding="utf-8")
            labels_path.write_text(json.dumps(labels), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "two valid"):
                load_adjudicated_cases(cases_path, labels_path)


if __name__ == "__main__":
    unittest.main()
