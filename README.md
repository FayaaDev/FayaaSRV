# Rakkib - runtime branch

This branch is the slim install snapshot used by the public installer.

Allowed paths:
- `.gitignore`
- `README.md`
- `install.sh`
- `pyproject.toml`
- `src/rakkib/**`

Do not develop on this branch. Land changes on `main`, then regenerate `runtime`
with `scripts/runtime-branch.sh sync --push`.
