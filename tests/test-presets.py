import importlib.util
import json
import pathlib
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "lora_presets", pathlib.Path(__file__).resolve().parents[1] / "presets.py"
)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class PresetTests(unittest.TestCase):
    def test_disk_persistence_normalized_keys_and_multiple_models(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "presets.json"
            row = {
                "sm": 0.7,
                "sc": 0.3,
                "categories": ["Eyes", "Style"],
                "triggers": ["trigger"],
                "custom": ["custom"],
                "on": False,
                "id": "old",
            }
            p.write_preset(path, "Krea2\\Model.safetensors", row)
            p.write_preset(path, "Other.safetensors", {"sm": -0.5})
            saved = p.read_presets(path)
            self.assertEqual(
                saved[p.key_for("krea2/model.SAFETENSORS")]["categories"],
                ["Eyes", "Style"],
            )
            self.assertEqual(saved["krea2/model.safetensors"]["sc"], 0.3)
            self.assertEqual(len(saved), 2)
            self.assertNotIn("on", saved["krea2/model.safetensors"])
            self.assertNotIn("id", saved["krea2/model.safetensors"])
            self.assertEqual(
                len(json.loads(path.with_suffix(".json.bak").read_text())["presets"]), 1
            )

    def test_invalid_data_cannot_replace_a_good_library(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "presets.json"
            p.write_preset(path, "good.safetensors", {"sm": 1})
            before = path.read_bytes()
            for row in [
                {"sm": float("nan")},
                {"sc": 12},
                {"categories": "Eyes"},
                {"triggers": [3]},
            ]:
                with self.assertRaises(ValueError):
                    p.write_preset(path, "bad.safetensors", row)
                self.assertEqual(before, path.read_bytes())
            for name in ["../outside", "C:/models/test", "/absolute", ""]:
                with self.assertRaises(ValueError):
                    p.write_preset(path, name, {"sm": 1})

    def test_corrupt_library_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "presets.json"
            path.write_text("broken")
            with self.assertRaises(ValueError):
                p.write_preset(path, "model", {"sm": 1})
            self.assertEqual(path.read_text(), "broken")


unittest.main()
