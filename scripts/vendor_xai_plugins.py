#!/usr/bin/env python3
"""Vendor the Grok/Cursor-only entries as Codex plugin directories.

SOURCE: URLs and commit SHAs are copied from
``source_docs/xai-original/marketplace.json``.
SOURCE: Codex plugin layout follows ``source_docs/codex-reference/`` and the
public ``openai/plugins`` repository: components live at the plugin root and
the manifest is ``.codex-plugin/plugin.json``.

Only archive extraction is performed. No vendored scripts, package managers,
or plugin runtimes are executed.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = REPO_ROOT / "external_plugins"
LOCK_PATH = REPO_ROOT / "source_docs/xai-original/vendored-sources.json"

VENDOR_SPECS = {
    "sentry": {
        "url": "https://github.com/getsentry/plugin-grok.git",
        "sha": "7f9d7823a68a7668867786a573ef587ef2783f7d",
        "manifest": ".grok-plugin",
        "paths": [".grok-plugin/plugin.json", ".mcp.json", "LICENSE", "README.md", "assets", "skills"],
    },
    "axiom": {
        "url": "https://github.com/axiomhq/skills.git",
        "sha": "0e98ebaeec76a70c8fda9a7737605800c2f1245d",
        "manifest": ".grok-plugin",
        "paths": [".grok-plugin/plugin.json", ".mcp.json", "LICENSE", "README.md", "skills"],
    },
    "firecrawl": {
        "url": "https://github.com/firecrawl/firecrawl-grok-plugin.git",
        "sha": "af6c6c083ccfd74ae476761068ee4311a56e8282",
        "manifest": ".grok-plugin",
        "paths": [".grok-plugin/plugin.json", ".mcp.json", "README.md", "commands", "skills"],
    },
    "exa": {
        "url": "https://github.com/exa-labs/exa-grok-plugin.git",
        "sha": "879fae0c814765c43f39ea8f56aae1d44e9d9bc8",
        "manifest": ".grok-plugin",
        "paths": [".grok-plugin/plugin.json", ".mcp.json", "README.md", "commands", "rules", "skills"],
    },
    "tavily": {
        "url": "https://github.com/tavily-ai/tavily-grok-plugin.git",
        "sha": "0cfd0c2be2df4a2a90c683abaadaf36ef7f2f59d",
        "manifest": ".grok-plugin",
        "paths": [".grok-plugin/plugin.json", ".mcp.json", "LICENSE", "README.md", "skills"],
    },
    "pstack": {
        "url": "https://github.com/cursor/plugins.git",
        "sha": "bdf7aa355337897f167153e05069aca505dae17c",
        "manifest": ".cursor-plugin",
        "path": "pstack",
        "paths": [
            "pstack/.cursor-plugin",
            "pstack/LICENSE",
            "pstack/README.md",
            "pstack/agents",
            "pstack/skills",
        ],
    },
    "browser-use": {
        "url": "https://github.com/browser-use/plugins.git",
        "sha": "4749bcbfe456e5384b98281a8a66119352197f59",
        "manifest": ".grok-plugin",
        "path": "grok",
        "paths": ["grok/.grok-plugin/plugin.json", "grok/.mcp.json", "grok/README.md", "grok/skills"],
    },
}


def run(command: list[str], *, cwd: Path | None = None, capture: bool = False) -> bytes:
    result = subprocess.run(
        command,
        cwd=cwd or REPO_ROOT,
        check=False,
        capture_output=capture,
    )
    if result.returncode:
        detail = (result.stderr or b"").decode(errors="replace").strip()
        raise RuntimeError(f"{' '.join(command)} failed: {detail or result.returncode}")
    return result.stdout if capture else b""


def adapt_manifest_metadata(manifest_path: Path) -> None:
    """Normalize product-specific display copy without changing plugin behavior."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def adapt(value):
        if isinstance(value, str):
            return (
                value.replace("Grok Build", "Codex")
                .replace("from Grok", "in Codex")
                .replace("for Grok", "for Codex")
                .replace("directly from Grok", "directly in Codex")
            )
        if isinstance(value, list):
            return [adapt(item) for item in value]
        if isinstance(value, dict):
            return {key: adapt(item) for key, item in value.items()}
        return value

    manifest_path.write_text(
        json.dumps(adapt(manifest), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sanitize_example_credentials(name: str, destination: Path) -> None:
    """Remove credential-looking literals from known upstream example docs."""
    if name != "axiom":
        return
    # SOURCE: this path and its example-only credential fields come from the
    # pinned Axiom tree listed in VENDOR_SPECS; they are documentation, not
    # runtime configuration.
    example_path = destination / "skills/sre/reference/grafana.md"
    if not example_path.is_file():
        return
    replacements = {
        "cf_access_client_id": "<your-client-id>",
        "cf_access_client_secret": "<your-client-secret>",
        "username": "<your-username>",
        "password": "<your-password>",
    }
    content = example_path.read_text(encoding="utf-8")
    for key, placeholder in replacements.items():
        content = re.sub(
            rf'^{re.escape(key)}\\s*=\\s*"[^"]*"$',
            f'{key} = "{placeholder}"',
            content,
            flags=re.MULTILINE,
        )
    example_path.write_text(content, encoding="utf-8")


def vendor_one(name: str, spec: dict, staging: Path, force: bool) -> None:
    destination = OUTPUT_ROOT / name
    if destination.exists():
        if not force:
            raise RuntimeError(f"destination exists; rerun with --force: {destination}")
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    checkout = staging / name
    run(["git", "clone", "--filter=blob:none", "--no-checkout", spec["url"], str(checkout)])
    run(["git", "-C", str(checkout), "fetch", "--depth=1", "origin", spec["sha"]])
    archive = run(["git", "-C", str(checkout), "archive", "--format=tar", spec["sha"], "--", *spec["paths"]], capture=True)
    tar_command = ["/usr/bin/tar", "-xf", "-", "-C", str(destination)]
    if spec.get("path"):
        tar_command.append("--strip-components=1")
    subprocess.run(tar_command, input=archive, check=True)

    source_manifest = destination / spec["manifest"]
    target_manifest = destination / ".codex-plugin"
    if not source_manifest.is_dir() or not (source_manifest / "plugin.json").is_file():
        raise RuntimeError(f"{name}: archived source manifest missing at {source_manifest}")
    source_manifest.rename(target_manifest)
    adapt_manifest_metadata(target_manifest / "plugin.json")
    sanitize_example_credentials(name, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="replace existing vendored plugin directories")
    args = parser.parse_args()

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    staging_parent = REPO_ROOT / "tmp"
    staging_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="xai-vendor-", dir=staging_parent) as staging_dir:
        staging = Path(staging_dir)
        for name, spec in VENDOR_SPECS.items():
            vendor_one(name, spec, staging, args.force)

    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.write_text(
        json.dumps(
            {
                "generated_by": "scripts/vendor_xai_plugins.py",
                "plugins": VENDOR_SPECS,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Vendored {len(VENDOR_SPECS)} plugins under {OUTPUT_ROOT}")
    print(f"Wrote provenance lock {LOCK_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
