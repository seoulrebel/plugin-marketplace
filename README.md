# xAI plugins for Codex

This repository is a Codex-compatible community fork of the [official xAI Plugin Marketplace](https://github.com/xai-org/plugin-marketplace). It adapts the xAI catalog to the Codex marketplace format so it can be imported from GitHub.

## Codex layout

```text
.agents/plugins/marketplace.json       # Codex marketplace catalog
external_plugins/neon/.codex-plugin/   # vendored Codex plugin manifest
source_docs/                           # preserved source catalogs and references
scripts/                               # conversion and validation tooling
```

Codex marketplace entries use the OpenAI-compatible `source` and `policy` fields. Remote entries remain pinned to the original upstream commit SHA. Where the same repository provides a non-Grok plugin subtree, the catalog points to that subtree: Stripe uses `providers/codex/plugin` and TinyFish uses `claude`. Browser Use's exact pinned Grok subtree is vendored and converted because its other subtrees are different plugins.

The original xAI catalog and generated index are preserved in `source_docs/xai-original/`. Entries that only exposed a Grok or Cursor layout were vendored at their original pinned SHAs and converted to `.codex-plugin/plugin.json`; provenance is recorded in `source_docs/xai-original/vendored-sources.json`. See [`docs/compatibility-report.md`](docs/compatibility-report.md) for the exact conversion boundary.

## Import into Codex / ChatGPT

Use the repository URL:

```text
https://github.com/seoulrebel/plugin-marketplace
```

Leave Path empty because `.agents/plugins/marketplace.json` is at the repository root. Workspace marketplace import requires an administrator and GitHub access to this repository and all referenced repositories.

## Validate locally

```bash
python3 -B scripts/vendor_xai_plugins.py
python3 -B scripts/convert_xai_catalog.py
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
python3 scripts/validate-catalog.py
python3 scripts/generate-plugin-index.py
python3 scripts/generate-plugin-index.py --check
```

The generated component index is `.agents/plugins/plugin-index.json`; it is derived from the catalog and must not be edited by hand.

Use `python3 -B scripts/vendor_xai_plugins.py --force` only when intentionally refreshing the seven vendored plugins from their locked upstream SHAs.

## Security and maintenance

Review every upstream plugin before installation. Plugins can execute code, start MCP servers, access connected services, or request credentials. Remote sources remain SHA-pinned, but each upstream repository and its future updates still require review before changing a pin.
