from pathlib import Path


def test_readme_describes_top_items():
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text()
    intro = " ".join(readme.split("\n## ", 1)[0].split())
    assert (
        "In Settings → Digest, **Items to show** can limit each digest to its most important items: "
        "each summary rates its item from 1 to 5, and a button shows the rest."
    ) in intro
