import importlib.util
import json
import pathlib
import unittest

PACK = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("category_policy", PACK / "policy.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def prompt(categories):
    return {
        "1": {
            "class_type": "LoraCategoryControls",
            "inputs": {"category_state": json.dumps({"categories": categories})},
        }
    }


class CategoryTests(unittest.TestCase):
    def test_any_disabled_category_blocks_row_without_mutating_original(self):
        original = {
            "loras": [
                {"on": True, "categories": ["Eyes", "Breasts"], "triggers": ["test"]}
            ]
        }
        for policy in [
            {"Eyes": False},
            {"Breasts": False},
            {"Eyes": True, "Breasts": False},
        ]:
            self.assertFalse(
                p.filter_stack(original, p.categories_from_prompt(prompt(policy)))[
                    "loras"
                ][0]["on"]
            )
        self.assertTrue(original["loras"][0]["on"])

    def test_enabling_category_does_not_enable_disabled_rows(self):
        state = {
            "loras": [
                {"on": False, "categories": ["Eyes"]},
                {"on": True, "categories": []},
            ]
        }
        result = p.filter_stack(state, p.categories_from_prompt(prompt({"Eyes": True})))
        self.assertFalse(result["loras"][0]["on"])
        self.assertTrue(result["loras"][1]["on"])

    def test_case_insensitive_and_unknown_categories_default_on(self):
        state = {
            "loras": [
                {"on": True, "categories": [" eyes "]},
                {"on": True, "categories": ["New"]},
            ]
        }
        result = p.filter_stack(
            state, p.categories_from_prompt(prompt({"EYES": False}))
        )
        self.assertFalse(result["loras"][0]["on"])
        self.assertTrue(result["loras"][1]["on"])

    def test_cache_changes_and_separate_workflow_has_no_shared_state(self):
        on = prompt({"Eyes": True})
        off = prompt({"Eyes": False})
        self.assertNotEqual(p.policy_signature(on), p.policy_signature(off))
        self.assertEqual(p.categories_from_prompt({}), {})
        self.assertTrue(p.categories_from_prompt(on)["eyes"])
        data = {
            "prompt": dict(
                off, loader={"class_type": "CategoryLoraLoader", "inputs": {}}
            )
        }
        p.inject_category_policy(data)
        self.assertEqual(
            json.loads(data["prompt"]["loader"]["inputs"]["CategoryPolicy"]),
            {"eyes": False},
        )

    def test_multiple_controllers_and_invalid_switch_fail_clearly(self):
        d = prompt({"Eyes": False})
        d["2"] = d["1"]
        with self.assertRaisesRegex(ValueError, "one Category Controls"):
            p.categories_from_prompt(d)
        with self.assertRaisesRegex(ValueError, "boolean"):
            p.categories_from_prompt(prompt({"Eyes": "false"}))


unittest.main()
