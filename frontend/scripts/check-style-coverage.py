"""Report statically named UI classes without rules in the owned C7 stylesheets."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
# The C7 prototype lives with the redesign-ui-ux change, which is archived after merge.
PROTOTYPE = next(
    (path for path in [ROOT / "openspec/changes/redesign-ui-ux/prototypes",
                       *sorted((ROOT / "openspec/changes/archive").glob("*-redesign-ui-ux/prototypes"))]
     if path.is_dir()),
    ROOT / "openspec/changes/redesign-ui-ux/prototypes",
)
CASCADE = [
    PROTOTYPE / "shared/base.css",
    *(PROTOTYPE / f"directions/{name}.css" for name in ("c", "c3", "c3b", "c7")),
]
OWNED = [FRONTEND / f"src/styles/{name}.css" for name in ("base", "layout", "components")]
PROTOTYPE_ONLY = {
    "code": "Offline command block uses self-contained inline CSS",
    "hero-last": "Prototype Last digest line removed from Home",
    "item-long": "Archived C7 prototype long-item layout",
    "item-short": "Archived C7 prototype short-item layout",
    "logo": "Prototype wordmark; standalone offline logo was removed",
    "logo-lg": "Prototype-only large wordmark",
    "offline-brand": "Prototype offline card; standalone page owns its own CSS",
    "offline-card": "Prototype offline card; standalone page owns its own CSS",
    "page-history": "Generic .page grid handles the History wrapper",
    "page-offline": "Standalone offline page does not load app CSS",
    "page-sources": "Generic .page grid handles the Sources wrapper",
}


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


def missing_selectors(prototype: set[str], owned: set[str],
                      allowed: dict[str, str]) -> set[str]:
    if any(not reason.strip() for reason in allowed.values()):
        raise ValueError("Every allowed prototype-only selector needs a reason")
    return prototype - owned - allowed.keys()


def main() -> int:
    used = markup_classes((PROTOTYPE / "shared/render.js").read_text())
    for source in (FRONTEND / "src").rglob("*.tsx"):
        if not source.name.endswith(".test.tsx"):
            used.update(markup_classes(source.read_text()))

    prototype, owned = selectors(CASCADE), selectors(OWNED)
    static = sorted((used & prototype) - owned)
    missing = sorted(missing_selectors(prototype, owned, PROTOTYPE_ONLY))
    print(f"Static UI classes with C7 rules but no app rules ({len(static)}):")
    for name in static:
        print(f"  .{name}")
    print(f"Allow-listed prototype-only selectors ({len(PROTOTYPE_ONLY)}):")
    for name, reason in sorted(PROTOTYPE_ONLY.items()):
        print(f"  .{name}: {reason}")
    print(f"Uncovered prototype selectors ({len(missing)}):")
    for name in missing:
        print(f"  .{name}")
    return bool(missing)


if __name__ == "__main__":
    raise SystemExit(main())
