#!/usr/bin/env bash

set -Eeuo pipefail

REPO_URL="${RAKKIB_REPO:-https://github.com/FayaaDev/Rakkib.git}"
BRANCH="${RAKKIB_BRANCH:-main}"

if [[ -z "${RAKKIB_DIR:-}" && -f "AGENT_PROTOCOL.md" && -d ".git" ]]; then
    INSTALL_DIR="$(pwd)"
else
    INSTALL_DIR="${RAKKIB_DIR:-${HOME}/Rakkib}"
fi

WRAPPER_ARGS=()

usage() {
    cat <<'USAGE'
Usage: install.sh [--dir <path>] [--repo <url>] [--branch <name>]
                  [--skip-doctor] [--doctor-only]
                  [--agent <auto|opencode|claude|codex|none>] [--no-agent] [--print-prompt]

Thin Rakkib remote bootstrapper. It verifies basic host support, clones or
updates the installer repo, then hands off to the repo-local ./rakkib wrapper.
The wrapper handles doctor, scoped privilege helper setup, and agent launch.

Environment overrides:
  RAKKIB_DIR       target checkout path, default: $HOME/Rakkib
  RAKKIB_REPO      git repo URL, default: https://github.com/FayaaDev/Rakkib.git
  RAKKIB_BRANCH    git branch, default: main
  RAKKIB_AGENT     agent to launch, default: auto
USAGE
}

log() {
    printf '==> %s\n' "$*"
}

warn() {
    printf 'WARNING: %s\n' "$*" >&2
}

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

parse_args() {
    while [[ "$#" -gt 0 ]]; do
        case "$1" in
            --dir)
                [[ "$#" -ge 2 ]] || die "missing value for --dir"
                INSTALL_DIR="$2"
                shift 2
                ;;
            --repo)
                [[ "$#" -ge 2 ]] || die "missing value for --repo"
                REPO_URL="$2"
                shift 2
                ;;
            --branch)
                [[ "$#" -ge 2 ]] || die "missing value for --branch"
                BRANCH="$2"
                shift 2
                ;;
            --skip-doctor|--doctor-only|--no-agent|--print-prompt)
                WRAPPER_ARGS+=("$1")
                shift
                ;;
            --agent)
                [[ "$#" -ge 2 ]] || die "missing value for --agent"
                WRAPPER_ARGS+=("$1" "$2")
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
}

detect_platform() {
    local kernel arch normalized_arch
    kernel="$(uname -s 2>/dev/null || true)"
    arch="$(uname -m 2>/dev/null || true)"

    case "$kernel" in
        Linux|Darwin) ;;
        *) die "unsupported OS: ${kernel:-unknown}; expected Linux or Mac" ;;
    esac

    case "$arch" in
        x86_64|amd64) normalized_arch="amd64" ;;
        aarch64|arm64) normalized_arch="arm64" ;;
        *) die "unsupported architecture: ${arch:-unknown}; expected amd64 or arm64" ;;
    esac

    log "Detected ${kernel}/${normalized_arch}"
}

ensure_tooling() {
    command_exists git || die "git is required. Install git, then rerun this bootstrapper."
    command_exists curl || warn "curl is not installed; install it before Cloudflare and download-heavy steps."
}

is_empty_dir() {
    local dir="$1"
    [[ -d "$dir" ]] || return 1
    [[ -z "$(ls -A "$dir" 2>/dev/null)" ]]
}

repo_has_local_changes() {
    [[ -n "$(git -C "$INSTALL_DIR" status --porcelain 2>/dev/null)" ]]
}

prepare_repo() {
    if [[ -d "${INSTALL_DIR}/.git" ]]; then
        log "Using existing checkout: ${INSTALL_DIR}"
        if repo_has_local_changes; then
            warn "Existing checkout has local changes; skipping automatic update."
            return 0
        fi

        log "Updating existing checkout from origin/${BRANCH}"
        git -C "$INSTALL_DIR" fetch origin "$BRANCH"
        if git -C "$INSTALL_DIR" show-ref --verify --quiet "refs/heads/${BRANCH}"; then
            git -C "$INSTALL_DIR" checkout "$BRANCH"
        else
            git -C "$INSTALL_DIR" checkout -B "$BRANCH" "origin/${BRANCH}"
        fi
        git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
        return 0
    fi

    if [[ -e "$INSTALL_DIR" ]] && ! is_empty_dir "$INSTALL_DIR"; then
        die "target path exists and is not an empty git checkout: ${INSTALL_DIR}"
    fi

    mkdir -p "$(dirname "$INSTALL_DIR")"
    log "Cloning ${REPO_URL} into ${INSTALL_DIR}"
    git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
}

handoff_to_wrapper() {
    local wrapper="${INSTALL_DIR}/rakkib"
    [[ -x "$wrapper" ]] || die "Rakkib wrapper is missing or not executable: ${wrapper}"

    log "Handing off to ${wrapper}"
    cd "$INSTALL_DIR"

    if [[ -r /dev/tty ]]; then
        exec "$wrapper" "${WRAPPER_ARGS[@]}" < /dev/tty
    fi

    exec "$wrapper" "${WRAPPER_ARGS[@]}"
}

main() {
    parse_args "$@"
    detect_platform
    ensure_tooling
    prepare_repo
    handoff_to_wrapper
}

main "$@"
