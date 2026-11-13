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


def readme_section(heading):
    readme = read_file("README.md")
    return readme.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


def collapse_whitespace(text):
    return " ".join(text.split())


def test_readme_states_supported_runtime_minimums():
    readme = collapse_whitespace(read_file("README.md"))
    minimum = tomllib.loads(read_file("backend/pyproject.toml"))["project"]["requires-python"][2:]
    assert f"Python {minimum} or newer" in readme
    assert "Node.js 22.12 or newer" in readme
    assert "https://nodejs.org" in readme
    assert "3.11" not in readme_section("Development setup")


def test_ci_node_major_supports_documented_minimum():
    # Guard: CI already uses Node 24, above the documented minimum major.
    versions = re.findall(r"node-version: ['\"](\d+)['\"]", read_file(".github/workflows/ci.yml"))
    assert versions, "CI must install Node.js"
    assert all(int(version) >= 22 for version in versions)


def test_readme_builds_frontend_before_starting_backend_and_names_database():
    development = collapse_whitespace(readme_section("Development setup"))
    assert "backend/data/catchup.sqlite3" in development
    backend = re.search(r"uv run (?:catchup serve|uvicorn)", development)
    assert backend, "Development setup must start the backend"
    assert "npm run build" in development[:backend.start()]


def test_readme_explains_local_docker_source_build():
    readme = collapse_whitespace(read_file("README.md"))
    assert "COMPOSE_FILE=compose.yaml:compose.build.yaml" in readme
    assert "catchup:local" in readme
    assert "git clone https://github.com/Zhuoang2/catchup" in readme


def test_readme_names_health_address_and_response():
    readme = collapse_whitespace(read_file("README.md"))
    assert "/api/health" in readme
    assert '{"status":"ok"}' in readme


def test_readme_creates_private_env_and_backup_files():
    development = collapse_whitespace(readme_section("Development setup"))
    docker = readme_section("Run with Docker")
    blocks = re.findall(r"```sh\n(.*?)```", docker, re.DOTALL)
    secret = next((block for block in blocks if "printf 'CATCHUP_SECRET_KEY=" in block), "")
    backup = next((block for block in blocks if 'mode="w|gz"' in block), "")
    assert re.search(r"\(umask 077;\s*printf 'CATCHUP_SECRET_KEY=", secret)
    assert "umask 077" in development
    assert "umask 077" in backup
    assert '"$HOME/catchup-data.tar.gz"' in backup
    assert "docker compose create" in collapse_whitespace(docker)


def test_readme_user_agent_example_matches_release():
    version = tomllib.loads(read_file("backend/pyproject.toml"))["project"]["version"]
    readme = collapse_whitespace(read_file("README.md"))
    assert f"CatchUp/{version} (+https://github.com/Zhuoang2/catchup; by /u/example)" in readme
