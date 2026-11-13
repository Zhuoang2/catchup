import json
from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[2]


def read_file(relative_path):
    path = ROOT / relative_path
    assert path.is_file(), f"Required installation file is missing: {relative_path}"
    return path.read_text()


def test_python_minimum_matches_ci_image_and_lock():
    project = tomllib.loads(read_file("backend/pyproject.toml"))["project"]
    minimum = re.fullmatch(r">=(\d+\.\d+)", project["requires-python"])
    assert minimum, project["requires-python"]
    ci = re.search(r"python-version: ['\"](\d+\.\d+)['\"]", read_file(".github/workflows/ci.yml"))
    image = re.findall(r"^FROM python:(\d+\.\d+)-", read_file("Dockerfile"), re.MULTILINE)
    lock = tomllib.loads(read_file("backend/uv.lock"))
    assert ci and image, "CI and final Docker image must name Python versions"
    assert minimum.group(1) == ci.group(1) == image[-1] == "3.12"
    assert lock["requires-python"] == ">=3.12"


def test_compose_separates_published_image_and_source_build():
    published = read_file("compose.yaml")
    assert "image: ghcr.io/zhuoang2/catchup:latest" in published
    assert not any(line.strip().startswith("build:") for line in published.splitlines())
    source = read_file("compose.build.yaml")
    assert re.search(
        r"^services:\n  catchup:\n    image: catchup:local\n    build: \.\s*$",
        source,
    ), "The source override must build catchup:local under services.catchup"


def test_release_version_agrees_across_packages_and_locks():
    project = tomllib.loads(read_file("backend/pyproject.toml"))["project"]
    assert project["version"] == "0.2.0"
    for path in (
        "frontend/package.json",
        "extension/package.json",
        "extension/public/manifest.json",
    ):
        assert json.loads(read_file(path))["version"] == "0.2.0", path
    for path in ("frontend/package-lock.json", "extension/package-lock.json"):
        lock = json.loads(read_file(path))
        assert lock["version"] == "0.2.0", path
        assert lock["packages"][""]["version"] == "0.2.0", path
    lock = tomllib.loads(read_file("backend/uv.lock"))
    catchup = next(package for package in lock["package"] if package["name"] == "catchup")
    assert catchup["version"] == "0.2.0"
