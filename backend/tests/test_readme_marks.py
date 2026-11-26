from pathlib import Path


def test_readme_describes_bookmarks_and_their_privacy():
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text()
    intro = " ".join(readme.split("\n## ", 1)[0].split())
    privacy = " ".join(readme.split("## Privacy", 1)[1].split("\n## ", 1)[0].split())
    assert "bookmarked items are listed under Bookmarks, linked from History" in intro
    assert "They are never sent to the model provider, and they do not change later digests." in privacy
