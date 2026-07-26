import json
import random
import unittest

from experiments.long_source_distillation.run import (
    Chunk,
    chunk_document,
    cluster_schema_for,
    constitution_schema_for,
    limit_chunks_stratified,
    normalize_review_scores,
    parse_json_object,
    select_scored_chunks,
    strip_provenance,
)


class ChunkingTests(unittest.TestCase):
    def test_chunking_is_bounded_and_overlapping(self):
        text = "\n\n".join(f"Paragraph {index} " + ("x" * 350) for index in range(12))
        chunks = chunk_document("book.md", text, target_chars=1200, overlap_chars=400)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.char_count <= 1200 for chunk in chunks))
        self.assertEqual(chunks[0].index, 1)
        self.assertNotEqual(chunks[0].sha256, chunks[1].sha256)

    def test_stratified_limit_covers_sources_before_second_chunks(self):
        chunks = [
            make_chunk("a.md", 1),
            make_chunk("a.md", 2),
            make_chunk("b.md", 1),
            make_chunk("b.md", 2),
        ]

        selected = limit_chunks_stratified(chunks, 2)

        self.assertEqual({chunk.source_path for chunk in selected}, {"a.md", "b.md"})


class SelectionTests(unittest.TestCase):
    def test_selection_preserves_per_source_coverage_and_audit(self):
        chunks = [
            make_chunk("a.md", 1),
            make_chunk("a.md", 2),
            make_chunk("b.md", 1),
            make_chunk("b.md", 2),
        ]
        scores = {
            chunks[0].chunk_id: make_score(4),
            chunks[1].chunk_id: make_score(0),
            chunks[2].chunk_id: make_score(1),
            chunks[3].chunk_id: make_score(2),
        }
        random.seed(1)

        selected, reasons = select_scored_chunks(
            chunks,
            scores,
            min_score=3,
            audit_low_score_count=1,
            max_selected=3,
            seed=1,
        )

        self.assertEqual(len(selected), 3)
        self.assertEqual({chunk.source_path for chunk in selected}, {"a.md", "b.md"})
        self.assertTrue(any("low-score-audit" in values for values in reasons.values()))
        self.assertEqual(
            {chunk.chunk_id for chunk in selected},
            set(reasons),
        )

    def test_tied_scores_have_a_stable_chunk_id_tiebreaker(self):
        chunks = [
            make_chunk("a.md", 1),
            make_chunk("a.md", 2),
            make_chunk("b.md", 1),
            make_chunk("b.md", 2),
        ]
        scores = {chunk.chunk_id: make_score(3) for chunk in chunks}

        selected_forward, _ = select_scored_chunks(
            chunks,
            scores,
            min_score=3,
            audit_low_score_count=0,
            max_selected=3,
            seed=1,
        )
        selected_reverse, _ = select_scored_chunks(
            list(reversed(chunks)),
            scores,
            min_score=3,
            audit_low_score_count=0,
            max_selected=3,
            seed=1,
        )

        self.assertEqual(
            {chunk.chunk_id for chunk in selected_forward},
            {chunk.chunk_id for chunk in selected_reverse},
        )


class SerializationTests(unittest.TestCase):
    def test_parse_json_object_accepts_fence(self):
        self.assertEqual(parse_json_object('```json\n{"ok": true}\n```'), {"ok": True})

    def test_parse_json_object_repairs_mechanical_key_and_brace_errors(self):
        malformed = """{
        "clusters": [{
          "cluster_id": "one",
          description": "first",
          "candidates": ["1"],
        }, {
        {
          "cluster_id": "two",
          description: "second",
          "candidates": ["2"]
        }]
        }"""

        parsed = parse_json_object(malformed)

        self.assertEqual(len(parsed["clusters"]), 2)
        self.assertEqual(parsed["clusters"][0]["description"], "first")
        self.assertEqual(parsed["clusters"][1]["description"], "second")

    def test_strip_provenance_keeps_standard_constitution_shape(self):
        enriched = {
            "overview": "Test",
            "criteria": [
                {
                    "comparative": "Prefer the response that tests.",
                    "reasoning": "Grounded.",
                    "questions": ["One?", "Two?"],
                    "candidate_ids": ["c1"],
                }
            ],
            "guidelines": [],
        }

        constitution, provenance = strip_provenance(enriched)

        self.assertNotIn("candidate_ids", constitution["criteria"][0])
        self.assertEqual(provenance, {"criterion-01": ["c1"]})
        json.dumps(constitution)

    def test_dynamic_schemas_constrain_provenance_ids(self):
        cluster_schema = cluster_schema_for(["c1", "c2"], max_clusters=2)
        cluster_id_schema = cluster_schema["properties"]["clusters"]["items"][
            "properties"
        ]["candidates"]["items"]
        constitution_schema = constitution_schema_for(["c1", "c2"])
        criterion_id_schema = constitution_schema["properties"]["criteria"]["items"][
            "properties"
        ]["candidate_ids"]["items"]

        self.assertEqual(cluster_id_schema["enum"], ["c1", "c2"])
        self.assertEqual(criterion_id_schema["enum"], ["c1", "c2"])

    def test_cluster_schema_accepts_requested_census_size(self):
        schema = cluster_schema_for(["c1"], max_clusters=40)

        self.assertEqual(
            schema["properties"]["clusters"]["maxItems"],
            40,
        )

    def test_review_scores_normalize_fractional_and_percentage_scales(self):
        review = {
            "coverage_score": 0.75,
            "grounding_score": 82.4,
            "redundancy_score": 1,
        }

        normalized = normalize_review_scores(review)

        self.assertEqual(normalized["coverage_score"], 75)
        self.assertEqual(normalized["grounding_score"], 82)
        self.assertEqual(normalized["redundancy_score"], 100)


def make_chunk(source_path: str, index: int) -> Chunk:
    text = f"{source_path}-{index}"
    return Chunk(
        chunk_id=f"{source_path}::chunk-{index:04d}",
        source_path=source_path,
        index=index,
        text=text,
        char_count=len(text),
        sha256=str(index),
    )


def make_score(value: int):
    return {
        "normative_yield": value,
        "contains_conflict_resolution": False,
        "contains_rare_exception": False,
        "themes": [],
        "rationale": "",
    }


if __name__ == "__main__":
    unittest.main()
