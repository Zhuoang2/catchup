import json
from pathlib import Path
import re
import tomllib

import pytest


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
    assert read_file("backend/.python-version").strip() == minimum.group(1)


def test_compose_separates_published_image_and_source_build():
    published = read_file("compose.yaml")
    assert "image: ghcr.io/zhuoang2/catchup:latest" in published
    assert not any(line.strip().startswith("build:") for line in published.splitlines())
    source = read_file("compose.build.yaml")
    assert source == (
        "services:\n"
        "  catchup:\n"
        "    image: catchup:local\n"
        "    build: .\n"
        "    pull_policy: never\n"
    ), "The source override must build locally without attempting a pull"


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
    # Guard: the original commands already used private creation masks.
    development = command_block("Development setup", "printf 'CATCHUP_SECRET_KEY=")
    secret = command_block("Run with Docker", "printf 'CATCHUP_SECRET_KEY=")
    backup = command_block("Run with Docker", 'mode="w|gz"')
    assert "umask 077" in development
    assert "umask 077" in secret
    assert "umask 077" in backup
    assert "docker compose create" in command_block("Run with Docker", "docker compose create")


def test_readme_user_agent_example_matches_release():
    version = tomllib.loads(read_file("backend/pyproject.toml"))["project"]["version"]
    readme = collapse_whitespace(read_file("README.md"))
    assert f"CatchUp/{version} (+https://github.com/Zhuoang2/catchup; by /u/example)" in readme


def command_blocks(heading):
    return re.findall(r"```sh\n(.*?)```", readme_section(heading), re.DOTALL)


def command_block(heading, phrase):
    block = next((block for block in command_blocks(heading) if phrase in block), None)
    assert block is not None, f"Missing {heading} command block containing {phrase!r}"
    return block


def assert_in_order(block, phrases):
    previous = -1
    for phrase in phrases:
        position = block.find(phrase)
        assert position >= 0, f"Missing command or check: {phrase}"
        assert position > previous, f"Command or check is out of order: {phrase}"
        previous = position


@pytest.mark.parametrize("heading", ["Development setup", "Run with Docker"])
def test_secret_blocks_refuse_replacement_and_require_openssl(heading):
    block = command_block(heading, "printf 'CATCHUP_SECRET_KEY=")
    assert "set -C" in block
    assert "openssl rand -hex 32" in block
    assert "python3" not in block
    assert block.strip().startswith("(") and block.strip().endswith(")")
    redirect = re.search(r">\s*\.env(?=\s|\)|$)", block)
    assert redirect, "Secret block must write .env"
    for setting in ("umask 077", "set -C"):
        assert 0 <= block.find(setting) < redirect.start(), setting


@pytest.mark.parametrize("heading", ["Development setup", "Run with Docker"])
def test_readme_names_secret_and_test_prerequisites_outside_commands(heading):
    text = collapse_whitespace(
        re.sub(r"```sh\n.*?```", "", readme_section(heading), flags=re.DOTALL)
    )
    assert "openssl" in text
    if heading == "Development setup":
        assert "git clone https://github.com/Zhuoang2/catchup" in command_block(
            heading, "git clone"
        )
        assert "frontend tests run" in text.lower()
        assert "`python3`" in text


def test_source_build_configuration_is_separate_guarded_and_idempotent():
    block = command_block("Run with Docker", "COMPOSE_FILE=compose.yaml:compose.build.yaml")
    assert "[ -s .env ] ||" in block
    assert "grep -qx 'COMPOSE_FILE=compose.yaml:compose.build.yaml' .env ||" in block
    assert "printf '\\nCOMPOSE_FILE=compose.yaml:compose.build.yaml\\n'" in block
    assert "docker compose" not in block
    assert "docker compose up -d --build --wait" in command_block(
        "Run with Docker", "docker compose up -d --build --wait"
    )
    upgrade = command_block("Run with Docker", "git pull")
    docker = readme_section("Run with Docker")
    note = docker.find("Existing source-build users")
    assert 0 <= note < docker.find(upgrade)
    assert "docker image rm ghcr.io/zhuoang2/catchup:latest" in docker[note:docker.find(upgrade)]


def test_every_docker_compose_start_waits_for_health():
    starts = [
        line
        for block in command_blocks("Run with Docker")
        for line in block.splitlines()
        if "docker compose up -d" in line
    ]
    assert starts, "Docker instructions must start the service"
    for line in starts:
        assert "--wait" in line, line


def test_backup_block_uses_unique_private_atomic_files():
    block = command_block("Run with Docker", 'mode="w|gz"')
    for phrase in (
        "set -e", "docker compose config -q", "umask 077",
        '"$HOME/catchup-backups"', "date -u", '[ ! -e "$backup" ]',
        ".partial", "mv",
    ):
        assert phrase in block, phrase
    assert "catchup-data.tar.gz" not in block


def test_restore_checks_whole_archive_before_stopping_or_emptying():
    block = command_block("Run with Docker", "iterdir")
    assert "set -e" in block
    assert "tarfile.data_filter" in block
    assert_in_order(block, (
        "docker compose config -q", '[ -s "$backup" ]', "gzip.GzipFile",
        "docker compose stop catchup", "iterdir", "extractall",
        "docker compose up -d --wait",
    ))


def test_new_machine_restore_checks_archive_and_refuses_existing_data():
    block = command_block("Run with Docker", "docker compose create")
    assert "set -e" in block
    assert_in_order(block, (
        "docker compose config -q", '[ -s "$backup" ]', "docker compose create",
        "gzip.GzipFile", 'any(Path("/data").iterdir())', "extractall",
        "docker compose up -d --wait",
    ))


@pytest.mark.parametrize("heading", ["Development setup", "Run with Docker"])
def test_commands_can_be_pasted_without_shell_history_or_comment_hazards(heading):
    # Guard: the original blocks already avoid both interactive-shell hazards.
    for block in command_blocks(heading):
        assert not re.search(r"(?m)^\s*#", block)
        assert not re.search(r'"[^"\n]*![^"\n]*"', block)
