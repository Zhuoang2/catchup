"""Report statically named UI classes without rules in the owned C7 stylesheets."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
PROTOTYPE = ROOT / "openspec/changes/redesign-ui-ux/prototypes"
CASCADE = [
    PROTOTYPE / "shared/base.css",
    *(PROTOTYPE / f"directions/{name}.css" for name in ("c", "c3", "c3b", "c7")),
]
OWNED = [FRONTEND / f"src/styles/{name}.css" for name in ("base", "layout", "components")]


def selectors(paths: list[Path]) -> set[str]:
    classes = set()
    for path in paths:
        css = re.sub(r"/\*.*?\*/", "", path.read_text(), flags=re.S)
        for selector in re.findall(r"([^{}]+)\{", css):
            classes.update(re.findall(r"\.([a-zA-Z][\w-]*)", selector))
    return classes


def markup_classes(text: str) -> set[str]:
    classes = set()
    for match in re.finditer(
        r"\bclass(?:Name)?=(?:[\"']([^\"']+)[\"']|\{`([^`]+)`\})", text
    ):
        value = match.group(1) or match.group(2)
        classes.update(token for token in value.split()
                       if re.fullmatch(r"[a-zA-Z][\w-]*", token))
    return classes


used = markup_classes((PROTOTYPE / "shared/render.js").read_text())
for source in (FRONTEND / "src").rglob("*.tsx"):
    if not source.name.endswith(".test.tsx"):
        used.update(markup_classes(source.read_text()))

missing = sorted((used & selectors(CASCADE)) - selectors(OWNED))
print(f"Static UI classes with C7 rules but no app rules ({len(missing)}):")
for name in missing:
    print(f"  .{name}")
