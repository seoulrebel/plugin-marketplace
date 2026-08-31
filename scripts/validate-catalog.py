#!/usr/bin/env python3
"""Validate the Codex marketplace catalog and local plugin layouts.

Enforces, for every plugin with `"source": {"source": "url", ...}`:

  - `sha` field is present and non-empty
  - `sha` is a 40-character lowercase hex string (full commit SHA, not a
    tag, branch, or abbreviation)

This is the catalog-level enforcement layer for SHA pinning. Without a
pin, the installer would fall back to `git clone --branch <ref>` (or HEAD),
which means a vendor force-push or repo compromise immediately ships to
every user who installs or updates that plugin. Pinning to a specific
commit + content-verifying it at install time is the only thing that
survives that class of attack.

For local entries this also verifies the Codex plugin root and manifest. This
prevents a catalog entry from passing JSON validation while pointing at a
missing or foreign plugin layout.

Run locally:    python3 scripts/validate-catalog.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# This fork publishes the Codex marketplace catalog only.
CATALOG_PATHS = [Path(".agents/plugins/marketplace.json")]
REPO_ROOT = Path(__file__).resolve().parent.parent


def validate_local_source(name: str, source: dict) -> list[str]:
    errors: list[str] = []
    path = source.get("path")
    if not isinstance(path, str) or not path.strip():
        return [f"plugin '{name}': local source requires a non-empty `path`"]
    if (
        path.startswith("/")
        or "\\" in path
        or any(part in ("..", "") for part in path.split("/"))
    ):
        return [
            f"plugin '{name}': local source path {path!r} must stay inside the repository"
        ]
    resolved = (REPO_ROOT / path).resolve()
    if not resolved.is_relative_to(REPO_ROOT) or not resolved.is_dir():
        return [f"plugin '{name}': local source directory does not exist: {path!r}"]

    manifest_path = next(
        (
            candidate
            for candidate in (
                resolved / ".codex-plugin/plugin.json",
                resolved / ".claude-plugin/plugin.json",
            )
            if candidate.is_file()
        ),
        None,
    )
    if manifest_path is None:
        return [
            f"plugin '{name}': local source has no .codex-plugin/plugin.json "
            "or .claude-plugin/plugin.json"
        ]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"plugin '{name}': failed to parse {manifest_path}: {exc}"]
    if manifest.get("name") != name:
        errors.append(
            f"plugin '{name}': manifest name {manifest.get('name')!r} "
            "does not match catalog name"
        )
    return errors


def validate_entry(entry: dict, idx: int) -> list[str]:
    """Return a list of human-readable error strings for a single plugin entry."""
    errors: list[str] = []
    name = entry.get("name") or f"<unnamed at index {idx}>"
    source = entry.get("source")
    if not isinstance(name, str) or not NAME_RE.match(name):
        errors.append(f"plugin at index {idx}: name must be kebab-case, got {name!r}")

    if not isinstance(source, dict):
        errors.append(f"plugin '{name}': source must be an object")
        return errors

    source_kind = source.get("source") or source.get("type")
    if source_kind == "local":
        errors.extend(validate_local_source(name, source))
        return errors
    if source_kind != "url":
        errors.append(f"plugin '{name}': unsupported source type {source_kind!r}")
        return errors

    sha = source.get("sha")
    if not sha:
        errors.append(
            f"plugin '{name}': missing `sha` field on url source "
            f"(url={source.get('url')!r}). All url-sourced plugins must "
            f"be pinned to a specific commit so a vendor force-push can't "
            f"silently ship new code to installed users."
        )
        return errors

    if not isinstance(sha, str):
        errors.append(
            f"plugin '{name}': sha must be a string, got {type(sha).__name__}"
        )
        return errors

    if not SHA_RE.match(sha):
        errors.append(
            f"plugin '{name}': sha {sha!r} is not a 40-character lowercase "
            f"hex string. Use the full commit SHA — not a tag, branch, or "
            f"abbreviated SHA."
        )

    path = source.get("path")
    if path is not None:
        if not isinstance(path, str) or not path.strip():
            errors.append(
                f"plugin '{name}': url source `path` must be a non-empty string when present."
            )
        elif (
            path.startswith("/")
            or "\\" in path
            or any(part in ("..", "") for part in path.split("/"))
        ):
            errors.append(
                f"plugin '{name}': url source `path` {path!r} must be a relative "
                f"subdirectory inside the repo (no leading '/', no '..', no backslashes)."
            )

    return errors


def validate_file(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        return [f"{path}: failed to parse: {e}"]

    plugins = data.get("plugins", [])
    if not isinstance(plugins, list):
        return [f"{path}: `plugins` must be an array, got {type(plugins).__name__}"]

    errors: list[str] = []
    names: set[str] = set()
    for idx, entry in enumerate(plugins):
        if not isinstance(entry, dict):
            errors.append(f"{path}: plugin index {idx} must be an object")
            continue
        name = entry.get("name")
        if isinstance(name, str):
            if name in names:
                errors.append(f"{path}: duplicate plugin name {name!r}")
            names.add(name)
        errors.extend(f"{path}: {e}" for e in validate_entry(entry, idx))
    return errors


def main() -> int:
    catalog_files = [p for p in CATALOG_PATHS if p.exists()]
    if not catalog_files:
        print(
            "ERROR: no catalog file found. Expected one of: "
            + ", ".join(str(p) for p in CATALOG_PATHS),
            file=sys.stderr,
        )
        return 1

    all_errors: list[str] = []
    for path in catalog_files:
        all_errors.extend(validate_file(path))

    if all_errors:
        print("Catalog validation failed:", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    summary = " + ".join(str(p) for p in catalog_files)
    print(f"Catalog OK ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
