from pathlib import Path


def test_readme_documents_public_context_limits_and_robots():
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text()
    for phrase in (
        "CATCHUP_LINKS_PER_ITEM` (default 8)",
        "CATCHUP_CONTEXT_FETCHES_PER_RUN` (default 60)",
        "CATCHUP_AUTHOR_REPLIES` (default on)",
        "robots.txt",
        "public pages",
    ):
        assert phrase in readme
