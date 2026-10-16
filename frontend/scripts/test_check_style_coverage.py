import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("check-style-coverage.py")


def missing_selectors(*args):
    spec = importlib.util.spec_from_file_location("check_style_coverage", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.missing_selectors(*args)


class StyleCoverageTests(unittest.TestCase):
    def test_cli_reports_the_full_selector_difference(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True, text=True, check=True,
        )
        self.assertIn("Uncovered prototype selectors (0):", result.stdout)
        self.assertIn(".logo: Prototype wordmark", result.stdout)
        self.assertIn(".hero-last: Prototype Last digest line removed from Home", result.stdout)

    def test_reports_prototype_rules_even_when_markup_has_no_static_class(self):
        self.assertEqual(
            missing_selectors(
                {"dynamic-only", "already-owned", "prototype-chrome"},
                {"already-owned"},
                {"prototype-chrome": "Only rendered by the prototype toolbar"},
            ),
            {"dynamic-only"},
        )

    def test_does_not_allow_an_unexplained_prototype_only_selector(self):
        with self.assertRaisesRegex(ValueError, "reason"):
            missing_selectors({"prototype-chrome"}, set(), {"prototype-chrome": ""})


if __name__ == "__main__":
    unittest.main()
