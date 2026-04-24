#!/usr/bin/env bash

set -Eeuo pipefail

REPO_URL="${FAYAASRV_REPO:-https://github.com/FayaaDev/FayaaSRV.git}"
BRANCH="${FAYAASRV_BRANCH:-main}"
RUN_DOCTOR=true
DOCTOR_ONLY=false

if [[ -z "${FAYAASRV_DIR:-}" && -f "AGENT_PROTOCOL.md" && -d ".git" ]]; then
    INSTALL_DIR="$(pwd)"
else
    INSTALL_DIR="${FAYAASRV_DIR:-${HOME}/FayaaSRV}"
fi

usage() {
    cat <<'USAGE'
Usage: install.sh [--dir <path>] [--repo <url>] [--branch <name>] [--skip-doctor] [--doctor-only]

Thin FayaaSRV bootstrapper. It verifies basic host support, clones or updates
the installer repo, optionally runs the doctor diagnostic, then prints the
agent prompt. It does not replace the agent-driven installer workflow.

Environment overrides:
  FAYAASRV_DIR       target checkout path, default: $HOME/FayaaSRV
  FAYAASRV_REPO      git repo URL, default: https://github.com/FayaaDev/FayaaSRV.git
  FAYAASRV_BRANCH    git branch, default: main
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
            --skip-doctor)
                RUN_DOCTOR=false
                shift
                ;;
            --doctor-only)
                DOCTOR_ONLY=true
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

run_doctor() {
    local doctor="${INSTALL_DIR}/scripts/fayaasrv-doctor"
    [[ -x "$doctor" ]] || die "doctor script is missing or not executable: ${doctor}"

    log "Running FayaaSRV doctor"
    if "$doctor" --state "${INSTALL_DIR}/.fss-state.yaml"; then
        return 0
    fi

    if [[ "$DOCTOR_ONLY" == true ]]; then
        return 1
    fi

    warn "Doctor reported failures. This can be normal before Step 00 installs Docker; review the report before proceeding."
}

print_agent_prompt() {
    cat <<EOF

FayaaSRV is ready for the agent-driven install flow.

Repo path:
  ${INSTALL_DIR}

Next step:
  cd "${INSTALL_DIR}"
  Start your coding agent from that directory, then paste this prompt:

--- PROMPT START ---
Read README.md and AGENT_PROTOCOL.md first.

Use this repo as the installer.
Ask me the question files in order.
Record answers in .fss-state.yaml.
Do not write outside the repo until Phase 6 (questions/06-confirm.md).
Use the helper-first Linux privilege flow instead of raw sudo for normal step execution.
After confirmation, execute steps/00-prereqs.md through steps/90-verify.md in numeric order, skipping optional restore-test work unless explicitly requested.
Stop on any failed Verify block and fix it before continuing.
--- PROMPT END ---
EOF
}

main() {
    parse_args "$@"
    detect_platform
    ensure_tooling
    prepare_repo

    if [[ "$RUN_DOCTOR" == true ]]; then
        run_doctor
    fi

    if [[ "$DOCTOR_ONLY" == false ]]; then
        print_agent_prompt
    fi
}

main "$@"
