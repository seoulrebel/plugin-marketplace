# Retained project scripts

The executable conversion and vendoring scripts are retained at the project
root under `scripts/` so the repository workflows and GitHub Actions can call
them directly:

- `../../scripts/convert_xai_catalog.py`
- `../../scripts/vendor_xai_plugins.py`
- `../../scripts/validate-catalog.py`
- `../../scripts/generate-plugin-index.py`

This file records their retention without maintaining a second divergent copy.
