#!/usr/bin/env bash

set -Eeuo pipefail

RUNTIME_BRANCH_CLEANUP_DIR=""

pick_temp_parent() {
  if [[ -n "${TMPDIR:-}" && -d "${TMPDIR}" ]]; then
    printf '%s\n' "${TMPDIR%/}"
    return 0
  fi

  if [[ -d /tmp ]]; then
    printf '%s\n' "/tmp"
    return 0
  fi

  pwd
}

log() {
  printf '==> %s\n' "$*"
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  scripts/runtime-branch.sh sync [--main-ref <ref>] [--runtime-ref <ref>] [--remote <name>] [--push] [--worktree-dir <path>]
  scripts/runtime-branch.sh verify-ref [--main-ref <ref>] [--runtime-ref <ref>]

Commands:
  sync        Rebuild the runtime branch from the allowlist snapshot on <main-ref>.
  verify-ref  Verify that <runtime-ref> contains only allowlisted files and matches
              <main-ref> for .gitignore, install.sh, pyproject.toml, and src/rakkib/**.
EOF
}

runtime_readme() {
  cat <<'EOF'
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
EOF
}

is_allowed_path() {
  case "$1" in
    .gitignore|README.md|install.sh|pyproject.toml|src/rakkib/*) return 0 ;;
    *) return 1 ;;
  esac
}

resolve_ref() {
  local ref="$1"
  local remote="${2:-}"

  if git rev-parse --verify "$ref" >/dev/null 2>&1; then
    printf '%s\n' "$ref"
    return 0
  fi

  if [[ -n "$remote" ]] && git rev-parse --verify "$remote/$ref" >/dev/null 2>&1; then
    printf '%s\n' "$remote/$ref"
    return 0
  fi

  die "unknown git ref: ${ref}"
}

check_required_paths_for_ref() {
  local ref="$1"
  local required_path
  for required_path in .gitignore README.md install.sh pyproject.toml; do
    git cat-file -e "${ref}:${required_path}" 2>/dev/null || die "${ref} is missing ${required_path}"
  done

  git cat-file -e "${ref}:src/rakkib/__init__.py" 2>/dev/null || die "${ref} is missing src/rakkib/**"
}

check_required_paths_for_worktree() {
  local worktree_dir="$1"
  local required_path
  for required_path in .gitignore README.md install.sh pyproject.toml src/rakkib/__init__.py; do
    [[ -e "${worktree_dir}/${required_path}" ]] || die "worktree is missing ${required_path}"
  done
}

check_allowlist_stream() {
  local context="$1"
  local path
  local disallowed=()

  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    if ! is_allowed_path "$path"; then
      disallowed+=("$path")
    fi
  done

  if ((${#disallowed[@]} > 0)); then
    printf 'ERROR: %s contains disallowed paths:\n' "$context" >&2
    printf '  %s\n' "${disallowed[@]}" >&2
    exit 1
  fi
}

check_runtime_readme_for_ref() {
  local ref="$1"
  local expected actual
  expected="$(runtime_readme)"
  actual="$(git show "${ref}:README.md")"
  [[ "$actual" == "$expected" ]] || die "${ref} README.md drifted from the runtime snapshot text"
}

check_runtime_readme_for_worktree() {
  local worktree_dir="$1"
  local expected actual
  expected="$(runtime_readme)"
  actual="$(<"${worktree_dir}/README.md")"
  [[ "$actual" == "$expected" ]] || die "worktree README.md drifted from the runtime snapshot text"
}

verify_ref() {
  local main_ref="$1"
  local runtime_ref="$2"
  local main_source_ref runtime_source_ref

  main_source_ref="$(resolve_ref "$main_ref")"
  runtime_source_ref="$(resolve_ref "$runtime_ref")"

  check_required_paths_for_ref "$runtime_source_ref"
  git ls-tree -r --name-only "$runtime_source_ref" | check_allowlist_stream "$runtime_source_ref"
  check_runtime_readme_for_ref "$runtime_source_ref"

  git diff --quiet "$main_source_ref" "$runtime_source_ref" -- .gitignore install.sh pyproject.toml src/rakkib || \
    die "${runtime_source_ref} drifted from ${main_source_ref} for runtime-managed files"

  log "${runtime_source_ref} matches the runtime allowlist and ${main_source_ref} parity checks"
}

verify_worktree() {
  local worktree_dir="$1"
  local main_ref="$2"

  check_required_paths_for_worktree "$worktree_dir"
  git -C "$worktree_dir" ls-files | check_allowlist_stream "$worktree_dir"
  check_runtime_readme_for_worktree "$worktree_dir"

  git -C "$worktree_dir" diff --quiet "$main_ref" -- .gitignore install.sh pyproject.toml src/rakkib || \
    die "worktree drifted from ${main_ref} for runtime-managed files"

  log "${worktree_dir} matches the runtime allowlist and ${main_ref} parity checks"
}

sync_runtime() {
  local main_ref="$1"
  local runtime_ref="$2"
  local remote="$3"
  local push_changes="$4"
  local worktree_dir="$5"
  local temp_dir=0
  local main_sha main_source_ref runtime_source_ref temp_parent

  if [[ -z "$worktree_dir" ]]; then
    temp_parent="$(pick_temp_parent)"
    worktree_dir="$(mktemp -d "${temp_parent}/runtime-sync.XXXXXX")"
    temp_dir=1
  elif [[ -e "$worktree_dir" ]]; then
    die "worktree dir already exists: ${worktree_dir}"
  fi

  if [[ "$temp_dir" -eq 1 ]]; then
    RUNTIME_BRANCH_CLEANUP_DIR="$worktree_dir"
    cleanup() {
      git worktree remove --force "$RUNTIME_BRANCH_CLEANUP_DIR" >/dev/null 2>&1 || true
      rm -rf "$RUNTIME_BRANCH_CLEANUP_DIR"
    }
    trap cleanup EXIT
  fi

  log "Fetching ${remote}/${main_ref} and ${remote}/${runtime_ref}"
  git fetch "$remote" "$main_ref" "$runtime_ref"

  main_source_ref="$(resolve_ref "$main_ref" "$remote")"
  runtime_source_ref="$(resolve_ref "$runtime_ref" "$remote")"
  main_sha="$(git rev-parse --short "$main_source_ref")"

  log "Creating detached runtime worktree at ${worktree_dir}"
  git worktree add --detach "$worktree_dir" "$runtime_source_ref" >/dev/null

  log "Clearing previous runtime contents"
  shopt -s dotglob nullglob
  local entry
  for entry in "$worktree_dir"/*; do
    [[ "$(basename "$entry")" == ".git" ]] && continue
    rm -rf "$entry"
  done
  shopt -u dotglob nullglob

  log "Copying allowlisted files from ${main_source_ref}"
  git -C "$worktree_dir" checkout "$main_source_ref" -- .gitignore install.sh pyproject.toml src/rakkib
  runtime_readme >"${worktree_dir}/README.md"

  git -C "$worktree_dir" add -A
  verify_worktree "$worktree_dir" "$main_source_ref"

  if git -C "$worktree_dir" diff --cached --quiet; then
    log "${runtime_ref} already matches ${main_source_ref}"
    return 0
  fi

  if [[ "$push_changes" -eq 0 && "$temp_dir" -eq 1 ]]; then
    log "Preview completed in a temporary worktree; rerun with --push or --worktree-dir to keep the result"
    return 0
  fi

  log "Committing runtime sync from ${main_source_ref}@${main_sha}"
  GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-Rakkib Runtime Sync}"
  GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-runtime-sync@users.noreply.github.com}"
  GIT_COMMITTER_NAME="${GIT_COMMITTER_NAME:-$GIT_AUTHOR_NAME}"
  GIT_COMMITTER_EMAIL="${GIT_COMMITTER_EMAIL:-$GIT_AUTHOR_EMAIL}"
  export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL
  git -C "$worktree_dir" commit -m "Sync runtime from ${main_source_ref}@${main_sha}" >/dev/null

  if [[ "$push_changes" -eq 1 ]]; then
    log "Pushing runtime sync to ${remote}/${runtime_ref}"
    git -C "$worktree_dir" push "$remote" HEAD:"refs/heads/${runtime_ref}"
  else
    log "Created detached runtime sync commit in ${worktree_dir}; push it manually or rerun with --push"
  fi
}

main() {
  local command="${1:-}"
  local main_ref="main"
  local runtime_ref="runtime"
  local remote="origin"
  local push_changes=0
  local worktree_dir=""

  [[ -n "$command" ]] || {
    usage
    exit 1
  }
  shift

  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --main-ref)
        [[ "$#" -ge 2 ]] || die "missing value for --main-ref"
        main_ref="$2"
        shift 2
        ;;
      --runtime-ref)
        [[ "$#" -ge 2 ]] || die "missing value for --runtime-ref"
        runtime_ref="$2"
        shift 2
        ;;
      --remote)
        [[ "$#" -ge 2 ]] || die "missing value for --remote"
        remote="$2"
        shift 2
        ;;
      --push)
        push_changes=1
        shift
        ;;
      --worktree-dir)
        [[ "$#" -ge 2 ]] || die "missing value for --worktree-dir"
        worktree_dir="$2"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "unknown argument: $1"
        ;;
    esac
  done

  git rev-parse --show-toplevel >/dev/null 2>&1 || die "run this script inside the Rakkib git repo"

  case "$command" in
    sync)
      sync_runtime "$main_ref" "$runtime_ref" "$remote" "$push_changes" "$worktree_dir"
      ;;
    verify-ref)
      verify_ref "$main_ref" "$runtime_ref"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
