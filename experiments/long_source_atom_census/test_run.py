import unittest

from experiments.long_source_atom_census.analyze import (
    majority_ids,
    paired_bootstrap_interval,
)
from experiments.long_source_atom_census.run import (
    ATOM_SCHEMA,
    blind_probe_cases,
    chunk_text,
    constitution_prompt,
    evidence_is_grounded,
    review_schema_for,
    select_budgeted_clusters,
)


class GroundingTests(unittest.TestCase):
    def test_atom_schema_does_not_impose_the_failed_eight_item_cap(self):
        self.assertEqual(ATOM_SCHEMA["properties"]["atoms"]["maxItems"], 20)

    def test_evidence_grounding_normalizes_whitespace(self):
        source = "Virtue is\n\n  the only good."

        self.assertTrue(evidence_is_grounded("Virtue is the only good.", source))
        self.assertFalse(evidence_is_grounded("Pleasure is good.", source))

    def test_chunking_is_deterministic_and_bounded(self):
        text = "\n\n".join(f"Section {index} " + "x" * 300 for index in range(10))

        first = chunk_text("book.md", text, 1000, 250)
        second = chunk_text("book.md", text, 1000, 250)

        self.assertEqual(first, second)
        self.assertTrue(all(chunk.char_count <= 1000 for chunk in first))


class SelectionTests(unittest.TestCase):
    def test_budgeted_selection_preserves_sources_and_conflicts(self):
        clusters = [
            make_cluster(
                "reference-001",
                ["a.md"],
                ["principle"],
                weight=2.0,
            ),
            make_cluster(
                "reference-002",
                ["b.md"],
                ["principle"],
                weight=2.0,
            ),
            make_cluster(
                "reference-003",
                ["a.md"],
                ["conflict"],
                weight=2.0,
                models=2,
            ),
            make_cluster(
                "reference-004",
                ["a.md", "b.md"],
                ["principle"],
                weight=1.0,
            ),
        ]

        selection = select_budgeted_clusters(
            clusters,
            ["a.md", "b.md"],
            budget_ratio=0.5,
        )

        selected = set(selection["selected_cluster_ids"])
        self.assertIn("reference-003", selected)
        for source in ("a.md", "b.md"):
            self.assertTrue(
                any(
                    source in cluster["source_paths"]
                    and cluster["cluster_id"] in selected
                    for cluster in clusters
                )
            )

    def test_selection_is_order_invariant(self):
        clusters = [
            make_cluster(
                f"reference-{index:03d}",
                ["a.md" if index % 2 else "b.md"],
                ["principle"],
                weight=1 + index / 10,
            )
            for index in range(1, 7)
        ]

        forward = select_budgeted_clusters(
            clusters,
            ["a.md", "b.md"],
            0.5,
        )
        reverse = select_budgeted_clusters(
            list(reversed(clusters)),
            ["a.md", "b.md"],
            0.5,
        )

        self.assertEqual(
            set(forward["selected_cluster_ids"]),
            set(reverse["selected_cluster_ids"]),
        )


class ProbeTests(unittest.TestCase):
    def test_probe_blinding_is_deterministic_and_can_swap(self):
        cases = [
            {
                "case_id": f"case-{index:02d}",
                "prompt": "Prompt",
                "response_a": "A original",
                "response_b": "B original",
            }
            for index in range(1, 13)
        ]

        first, first_swaps = blind_probe_cases(cases, seed=17)
        second, second_swaps = blind_probe_cases(cases, seed=17)

        self.assertEqual(first, second)
        self.assertEqual(first_swaps, second_swaps)
        self.assertTrue(any(first_swaps.values()))
        self.assertTrue(any(not value for value in first_swaps.values()))

    def test_review_schema_constrains_cluster_and_item_ids(self):
        schema = review_schema_for(
            ["reference-001"],
            ["criterion-01"],
        )

        self.assertEqual(
            schema["properties"]["recovered_cluster_ids"]["items"]["enum"],
            ["reference-001"],
        )
        self.assertEqual(
            schema["properties"]["unsupported_item_ids"]["items"]["enum"],
            ["criterion-01"],
        )

    def test_writer_prompt_has_no_condition_label(self):
        prompt = constitution_prompt("Stoicism", "source evidence")

        self.assertNotIn("condition", prompt.lower())
        self.assertIn("source evidence", prompt)


class AnalysisTests(unittest.TestCase):
    def test_majority_ids_requires_reviewer_consensus(self):
        result = majority_ids(
            [
                {"reference-001", "reference-002"},
                {"reference-001"},
                {"reference-003", "reference-001"},
            ]
        )

        self.assertEqual(result, {"reference-001"})

    def test_paired_bootstrap_is_deterministic(self):
        first = paired_bootstrap_interval([1.0, 2.0, 3.0], samples=100)
        second = paired_bootstrap_interval([1.0, 2.0, 3.0], samples=100)

        self.assertEqual(first, second)
        self.assertEqual(first["estimate"], 2.0)


def make_cluster(
    cluster_id,
    sources,
    atom_kinds,
    *,
    weight,
    models=1,
):
    return {
        "cluster_id": cluster_id,
        "label": cluster_id,
        "kind": "criterion",
        "synthesis": f"Synthesis for {cluster_id}",
        "candidate_ids": [f"{cluster_id}-candidate"],
        "source_paths": sources,
        "extractor_models": [f"model-{index}" for index in range(models)],
        "atom_kinds": atom_kinds,
        "support_count": 1,
        "weight": weight,
        "evidence": [],
        "packet_chars": 100,
    }


if __name__ == "__main__":
    unittest.main()
