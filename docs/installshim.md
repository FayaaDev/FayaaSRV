# Public Runtime Repository

Rakkib uses two repositories for launch:

- `FayaaDev/rakkib-dev` is the private development repository.
- `FayaaDev/rakkib` is the public runtime repository cloned by `install.sh`.

The public runtime repository is generated. Do not edit it directly.

## Runtime Allowlist

Only these paths are published:

- `.gitignore`
- `README.md` from `docs/public/README.md`
- `LICENSE`
- `install.sh`
- `pyproject.toml`
- `src/rakkib/**`

Everything else remains private development material.

## Publish Flow

After changes land on private `main`, publish the public runtime repo:

```bash
scripts/publish-runtime-repo.sh sync --push
```

Preview without pushing:

```bash
scripts/publish-runtime-repo.sh sync
```

Verify an existing public checkout:

```bash
scripts/publish-runtime-repo.sh verify --public-dir /path/to/public/rakkib
```

The generated commit message includes the private source short SHA:

```text
Publish runtime from <short-sha>

Source: FayaaDev/rakkib-dev@<full-sha>
```

## Installer Defaults

`install.sh` defaults to:

```text
RAKKIB_REPO=https://github.com/FayaaDev/rakkib.git
RAKKIB_BRANCH=main
```

Development-tree installs must be explicit:

```bash
RAKKIB_REPO=git@github.com:FayaaDev/rakkib-dev.git RAKKIB_BRANCH=main bash install.sh
```

Existing checkouts with the old `FayaaDev/Rakkib` origin are migrated to the public runtime repo on reinstall.

## Validation

Local regression checks:

```bash
python3 -m py_compile src/rakkib/cli.py
.venv/bin/python -m pytest tests/test_install_sh.py tests/test_cli.py tests/test_publish_runtime_repo.py
```

Public repo content check:

```bash
git clone https://github.com/FayaaDev/rakkib.git /tmp/rakkib-public-check
git -C /tmp/rakkib-public-check ls-files
```

Fresh-server validation must run on the test server, not the dev workstation:

```bash
curl -fsSL https://install.rakkib.app | bash
/root/.local/bin/rakkib --help
/root/.local/bin/rakkib update
git -C /root/Rakkib remote -v
git -C /root/Rakkib branch --show-current
```

Expected checkout state:

```text
origin -> https://github.com/FayaaDev/rakkib.git
branch -> main
```
