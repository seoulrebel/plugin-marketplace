# Contributing

Changes to this fork should preserve the Codex marketplace contract and the source provenance of the xAI catalog.

## Workflow

1. Edit `scripts/convert_xai_catalog.py` when changing the compatibility map.
2. Run `python3 -B scripts/vendor_xai_plugins.py` for a clean checkout, or use `--force` only when intentionally refreshing the locked vendored sources.
3. Run `python3 -B scripts/convert_xai_catalog.py` to regenerate `.agents/plugins/marketplace.json` and the compatibility report.
4. Run `python3 scripts/validate-catalog.py`.
5. Run `python3 scripts/generate-plugin-index.py --check` after generating the index.
6. Review the diff and run the repository's GitHub Actions checks before pushing.

## Requirements

- Keep every remote source pinned to a full 40-character lowercase commit SHA.
- Use `.codex-plugin/plugin.json` for vendored Codex plugins.
- Keep component directories (`skills/`, `commands/`, `agents/`, and so on) at the plugin root.
- Do not add a Grok-only or Cursor-only source to the Codex catalog without a reviewed vendoring conversion and pinned provenance record.
- Preserve original source files and reference material under `source_docs/` when changing the conversion rules.
- Review licenses, MCP endpoints, hooks, scripts, and credential requirements before vendoring or changing an upstream source.

## Source policy

This fork is not the official xAI marketplace and does not imply xAI endorsement. Upstream plugin authors retain ownership of their code, licenses, and terms. Changes that alter a plugin's source path or pinned SHA should explain the compatibility reason in the compatibility report or pull request.
