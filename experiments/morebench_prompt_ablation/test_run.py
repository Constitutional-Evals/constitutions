import unittest

from experiments.morebench_prompt_ablation.analyze import factorial_contrasts
from experiments.morebench_prompt_ablation.run import (
    CONSTITUTION_SCHEMA,
    JUDGE_SCHEMA,
    MOREBENCH_GENERATOR_ADDENDUM,
    MOREBENCH_REVIEW_ADDENDUM,
    generation_task,
    merge_judgments,
    render_meta_prompt,
    review_task,
)


def judgment(score, tagged=False):
    weakness = "[ATOMICITY] Split the item." if tagged else "Split the item."
    return {
        "reasoning": "Reason",
        "score": score,
        "subscores": {
            "breadth": score,
            "source_faithfulness": score,
            "llm_behavioral_usefulness": score,
            "clarity_nonredundancy": score,
            "edge_case_handling": score,
            "reasoning_groundedness": score,
            "question_quality": score,
        },
        "major_missing_dimension": score < 50,
        "strengths": ["Grounded"],
        "weaknesses": [weakness],
        "revision_suggestions": [weakness],
    }


class ContractTests(unittest.TestCase):
    def test_contracts_are_style_independent(self):
        conventional = generation_task("Test", "conventional")
        morebench = generation_task("Test", "morebench")

        self.assertNotIn(MOREBENCH_GENERATOR_ADDENDUM.strip(), conventional)
        self.assertIn(MOREBENCH_GENERATOR_ADDENDUM.strip(), morebench)
        self.assertEqual(CONSTITUTION_SCHEMA["required"], conventional_schema_required())

    def test_review_addendum_uses_existing_text_fields(self):
        candidate = {"overview": "O", "criteria": [], "guidelines": []}

        conventional = review_task("Test", candidate, "conventional")
        morebench = review_task("Test", candidate, "morebench")

        self.assertNotIn("[ATOMICITY]", conventional)
        self.assertIn(MOREBENCH_REVIEW_ADDENDUM.strip(), morebench)
        self.assertIn("weakness", MOREBENCH_REVIEW_ADDENDUM)
        self.assertNotIn("diagnostics", JUDGE_SCHEMA["properties"])

    def test_meta_prompt_substitution_requires_dynamic_slot(self):
        rendered = render_meta_prompt(
            "{CONSTITUTION_NAME}|{FOUNDATIONAL_DOCUMENTS}|{Dynamic_Task}",
            "Stoicism",
            "Evidence",
            "Task",
        )

        self.assertEqual(rendered, "Stoicism|Evidence|Task")
        with self.assertRaisesRegex(ValueError, "Dynamic_Task"):
            render_meta_prompt("No slot", "Test", "Evidence", "Task")

    def test_judgment_merge_preserves_diagnostics_and_averages_scores(self):
        merged = merge_judgments([judgment(40), judgment(80, tagged=True)])

        self.assertEqual(merged["score"], 60)
        self.assertTrue(merged["major_missing_dimension"])
        self.assertEqual(len(merged["weaknesses"]), 2)

    def test_factorial_contrast_recovers_known_effects(self):
        records = []
        for seed in (17, 29):
            for generator in ("conventional", "morebench"):
                for reviewer in ("conventional", "morebench"):
                    records.append(
                        {
                            "generator_style": generator,
                            "review_style": reviewer,
                            "seed": seed,
                            "metric": (
                                1
                                + (2 if generator == "morebench" else 0)
                                + (3 if reviewer == "morebench" else 0)
                            ),
                        }
                    )

        effects = factorial_contrasts(records, "metric")

        self.assertEqual(effects["generator_main_effect"]["mean"], 2)
        self.assertEqual(effects["review_main_effect"]["mean"], 3)
        self.assertEqual(effects["interaction"]["mean"], 0)
        self.assertEqual(effects["combined_minus_control"]["mean"], 5)


def conventional_schema_required():
    return ["overview", "criteria", "guidelines"]


if __name__ == "__main__":
    unittest.main()
