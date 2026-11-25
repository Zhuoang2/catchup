import re

from test_install_docs import collapse_whitespace, read_file, readme_section


def test_rsshub_override_is_exact_and_optional():
    assert read_file("compose.rsshub.yaml") == (
        "services:\n"
        "  catchup:\n"
        "    environment:\n"
        "      CATCHUP_RSSHUB_URL: http://rsshub:1200\n"
        "  rsshub:\n"
        "    image: diygod/rsshub:latest\n"
        "    env_file:\n"
        "      - path: .env.rsshub\n"
        "        required: false\n"
        "    restart: unless-stopped\n"
    )
    assert "rsshub" not in read_file("compose.yaml")


def test_rsshub_settings_stay_local():
    assert ".env.*" in read_file(".gitignore").splitlines()
    dockerignore = read_file(".dockerignore").splitlines()
    assert dockerignore[0] == "*"
    assert not any(".env" in line for line in dockerignore)
    assert "# CATCHUP_RSSHUB_URL=http://rsshub:1200" in read_file(".env.example").splitlines()


def test_readme_explains_bilibili_uploaders():
    section = readme_section("Bilibili uploaders")
    text = collapse_whitespace(section)
    for phrase in (
        "CATCHUP_RSSHUB_URL",
        "compose.yaml:compose.rsshub.yaml",
        "compose.yaml:compose.build.yaml:compose.rsshub.yaml",
        "diygod/rsshub:latest",
        "diygod/rsshub:chromium-bundled",
        "CatchUp never contacts Bilibili",
        "section 5.6(3)",
        "BILIBILI_COOKIE_",
        ".env.rsshub",
        "public RSSHub instance",
        "No subtitles from RSSHub",
        "third-party download",
        "Bilibili uploaders need a CatchUp version that includes them",
    ):
        assert phrase in text
    starts = [
        line
        for block in re.findall(r"```sh\n(.*?)```", section, re.DOTALL)
        for line in block.splitlines()
        if "docker compose up -d" in line
    ]
    assert starts
    assert all("--wait" in line for line in starts)
    assert "Bilibili uploaders" in readme_section("Supported sources")
