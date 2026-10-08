import unittest
from pathlib import Path


REPORT = Path(__file__).resolve().parents[2] / "docs/process/test-report-redesign-ui-ux.md"


class ReviewReportTests(unittest.TestCase):
    def test_final_review_records_every_red_check_and_full_verification(self):
        final = REPORT.read_text().split("## Final review fixes", 1)[-1]
        for task in range(1, 13):
            self.assertIn(f"13.{task}", final)
        for check in (
            "357 passed", "117 passed", "96%", "npm run build",
            "openspec validate redesign-ui-ux --strict",
            "Uncovered prototype selectors (0):", "docker build",
            "scripts/docker-smoke.sh", "5 passed",
        ):
            self.assertIn(check, final)

    def test_second_review_records_checks_and_corrects_c7_counts(self):
        report = REPORT.read_text()
        self.assertIn("## Second review fixes", report)
        review = report.split("## Second review fixes", 1)[-1]
        for check in (
            "uv run pytest --cov=catchup --cov-report=term-missing -q",
            "npm test -- --run",
            "npm run build",
            "openspec validate redesign-ui-ux --strict",
            "docker build",
            "scripts/docker-smoke.sh",
            "  .page-sources: Generic .page grid handles the Sources wrapper",
            "Uncovered prototype selectors (0):",
            "11.1", "11.2", "11.3", "11.4", "11.11",
        ):
            self.assertIn(check, review)
        self.assertIn("index counts are hidden as in C7", report)
        self.assertIn("10.7 text was corrected", report)


if __name__ == "__main__":
    unittest.main()
