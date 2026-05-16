#!/usr/bin/env bash

set -Eeuo pipefail

CLEANUP_DIR=""
PUBLIC_DIR_RESULT=""

log() {
  printf '==> %s\n' "$*" >&2
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  scripts/publish-runtime-repo.sh sync [--source-ref <ref>] [--public-repo <url>] [--public-branch <branch>] [--public-dir <path>] [--push]
  scripts/publish-runtime-repo.sh verify [--source-ref <ref>] --public-dir <path>

Commands:
  sync    Export the runtime allowlist from the private dev repo into the public runtime repo.
  verify  Verify a public runtime checkout contains only allowlisted files and matches <source-ref>.
EOF
}

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

is_allowed_path() {
  case "$1" in
    .gitignore|README.md|LICENSE|install.sh|pyproject.toml|src/rakkib/*) return 0 ;;
    *) return 1 ;;
  esac
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

check_source_paths() {
  local source_commit="$1"
  local required_path
  for required_path in .gitignore LICENSE install.sh pyproject.toml docs/public/README.md src/rakkib/__init__.py; do
    git cat-file -e "${source_commit}:${required_path}" 2>/dev/null || die "${source_commit} is missing ${required_path}"
  done
}

create_snapshot() {
  local source_commit="$1"
  local snapshot_dir="$2"

  mkdir -p "$snapshot_dir"
  git archive "$source_commit" .gitignore LICENSE install.sh pyproject.toml src/rakkib | tar -x -C "$snapshot_dir"
  git show "${source_commit}:docs/public/README.md" >"${snapshot_dir}/README.md"
}

check_required_public_paths() {
  local public_dir="$1"
  local required_path
  for required_path in .gitignore README.md LICENSE install.sh pyproject.toml src/rakkib/__init__.py; do
    [[ -e "${public_dir}/${required_path}" ]] || die "${public_dir} is missing ${required_path}"
  done
}

verify_public_dir() {
  local public_dir="$1"
  local snapshot_dir="$2"

  check_required_public_paths "$public_dir"
  git -C "$public_dir" ls-files | check_allowlist_stream "$public_dir"

  cmp -s "${snapshot_dir}/.gitignore" "${public_dir}/.gitignore" || die ".gitignore drifted from the source snapshot"
  cmp -s "${snapshot_dir}/README.md" "${public_dir}/README.md" || die "README.md drifted from docs/public/README.md"
  cmp -s "${snapshot_dir}/LICENSE" "${public_dir}/LICENSE" || die "LICENSE drifted from the source snapshot"
  cmp -s "${snapshot_dir}/install.sh" "${public_dir}/install.sh" || die "install.sh drifted from the source snapshot"
  cmp -s "${snapshot_dir}/pyproject.toml" "${public_dir}/pyproject.toml" || die "pyproject.toml drifted from the source snapshot"
  diff -qr "${snapshot_dir}/src/rakkib" "${public_dir}/src/rakkib" >/dev/null || die "src/rakkib drifted from the source snapshot"
}

clear_public_dir() {
  local public_dir="$1"
  local entry

  shopt -s dotglob nullglob
  for entry in "$public_dir"/*; do
    [[ "$(basename "$entry")" == ".git" ]] && continue
    rm -rf "$entry"
  done
  shopt -u dotglob nullglob
}

public_repo_url_from_remote() {
  local public_repo="$1"
  if [[ -n "$public_repo" ]]; then
    printf '%s\n' "$public_repo"
    return 0
  fi

  git remote get-url public 2>/dev/null || die "missing public remote; pass --public-repo <url> or add a 'public' git remote"
}

prepare_public_checkout() {
  local public_repo="$1"
  local public_branch="$2"
  local public_dir="$3"
  local temp_parent fetch_ok=1

  if [[ -z "$public_dir" ]]; then
    temp_parent="$(pick_temp_parent)"
    CLEANUP_DIR="$(mktemp -d "${temp_parent}/rakkib-public-sync.XXXXXX")"
    trap 'rm -rf "$CLEANUP_DIR"' EXIT
    public_dir="${CLEANUP_DIR}/repo"
    git clone "$public_repo" "$public_dir" >/dev/null 2>&1 || die "failed to clone public runtime repo: ${public_repo}"
  elif [[ -d "${public_dir}/.git" ]]; then
    :
  elif [[ ! -e "$public_dir" ]]; then
    git clone "$public_repo" "$public_dir" >/dev/null 2>&1 || die "failed to clone public runtime repo: ${public_repo}"
  else
    die "public dir exists but is not a git checkout: ${public_dir}"
  fi

  if [[ -n "$(git -C "$public_dir" status --porcelain 2>/dev/null)" ]]; then
    die "public checkout has local changes: ${public_dir}"
  fi

  if git -C "$public_dir" remote get-url origin >/dev/null 2>&1; then
    git -C "$public_dir" remote set-url origin "$public_repo"
  else
    git -C "$public_dir" remote add origin "$public_repo"
  fi

  if git -C "$public_dir" fetch origin "$public_branch" >/dev/null 2>&1; then
    fetch_ok=0
  fi

  if git -C "$public_dir" show-ref --verify --quiet "refs/remotes/origin/${public_branch}"; then
    git -C "$public_dir" switch -C "$public_branch" "origin/${public_branch}" >/dev/null
  elif git -C "$public_dir" rev-parse --verify HEAD >/dev/null 2>&1; then
    git -C "$public_dir" switch -C "$public_branch" >/dev/null
  else
    git -C "$public_dir" switch --orphan "$public_branch" >/dev/null
  fi

  if [[ "$fetch_ok" -ne 0 ]]; then
    log "Public branch ${public_branch} does not exist yet; creating it"
  fi

  PUBLIC_DIR_RESULT="$public_dir"
}

sync_public_repo() {
  local source_ref="$1"
  local public_repo="$2"
  local public_branch="$3"
  local public_dir="$4"
  local push_changes="$5"
  local source_commit short_sha snapshot_dir

  source_commit="$(git rev-parse "${source_ref}^{commit}")"
  short_sha="$(git rev-parse --short "$source_commit")"
  check_source_paths "$source_commit"

  snapshot_dir="$(mktemp -d "$(pick_temp_parent)/rakkib-runtime-snapshot.XXXXXX")"
  create_snapshot "$source_commit" "$snapshot_dir"

  public_repo="$(public_repo_url_from_remote "$public_repo")"
  prepare_public_checkout "$public_repo" "$public_branch" "$public_dir"
  public_dir="$PUBLIC_DIR_RESULT"

  log "Publishing runtime snapshot from ${source_commit}@${short_sha}"
  clear_public_dir "$public_dir"
  cp -a "${snapshot_dir}/." "$public_dir/"

  git -C "$public_dir" add -A
  verify_public_dir "$public_dir" "$snapshot_dir"

  if git -C "$public_dir" diff --cached --quiet; then
    log "Public runtime repo already matches ${short_sha}"
    return 0
  fi

  GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-Rakkib Public Runtime Sync}"
  GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-runtime-sync@users.noreply.github.com}"
  GIT_COMMITTER_NAME="${GIT_COMMITTER_NAME:-$GIT_AUTHOR_NAME}"
  GIT_COMMITTER_EMAIL="${GIT_COMMITTER_EMAIL:-$GIT_AUTHOR_EMAIL}"
  export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL

  git -C "$public_dir" commit -m "Publish runtime from ${short_sha}" -m "Source: FayaaDev/rakkib-dev@${source_commit}" >/dev/null

  if [[ "$push_changes" -eq 1 ]]; then
    log "Pushing public runtime repo to ${public_branch}"
    git -C "$public_dir" push -u origin "$public_branch"
  else
    log "Created public runtime commit in ${public_dir}; rerun with --push to publish"
  fi
}

verify_command() {
  local source_ref="$1"
  local public_dir="$2"
  local source_commit snapshot_dir

  [[ -n "$public_dir" ]] || die "verify requires --public-dir <path>"
  [[ -d "${public_dir}/.git" ]] || die "public dir is not a git checkout: ${public_dir}"

  source_commit="$(git rev-parse "${source_ref}^{commit}")"
  check_source_paths "$source_commit"
  snapshot_dir="$(mktemp -d "$(pick_temp_parent)/rakkib-runtime-snapshot.XXXXXX")"
  create_snapshot "$source_commit" "$snapshot_dir"
  verify_public_dir "$public_dir" "$snapshot_dir"
  log "${public_dir} matches ${source_commit} runtime allowlist"
}

main() {
  local command="${1:-}"
  local source_ref="main"
  local public_repo="${RAKKIB_PUBLIC_REPO:-}"
  local public_branch="main"
  local public_dir=""
  local push_changes=0

  [[ -n "$command" ]] || {
    usage
    exit 1
  }
  shift

  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --source-ref)
        [[ "$#" -ge 2 ]] || die "missing value for --source-ref"
        source_ref="$2"
        shift 2
        ;;
      --public-repo)
        [[ "$#" -ge 2 ]] || die "missing value for --public-repo"
        public_repo="$2"
        shift 2
        ;;
      --public-branch)
        [[ "$#" -ge 2 ]] || die "missing value for --public-branch"
        public_branch="$2"
        shift 2
        ;;
      --public-dir)
        [[ "$#" -ge 2 ]] || die "missing value for --public-dir"
        public_dir="$2"
        shift 2
        ;;
      --push)
        push_changes=1
        shift
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

  git rev-parse --show-toplevel >/dev/null 2>&1 || die "run this script inside the private Rakkib dev repo"

  case "$command" in
    sync)
      sync_public_repo "$source_ref" "$public_repo" "$public_branch" "$public_dir" "$push_changes"
      ;;
    verify)
      verify_command "$source_ref" "$public_dir"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
