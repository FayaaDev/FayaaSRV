#!/usr/bin/env bash

set -Eeuo pipefail

REPO_URL="${RAKKIB_REPO:-https://github.com/FayaaDev/Rakkib.git}"
BRANCH="${RAKKIB_BRANCH:-runtime}"
UPDATE_MODE="${RAKKIB_UPDATE_MODE:-reset}"
VENV_INSTALL_IN_PROGRESS=0
PLATFORM=""
PYTHON_CMD="${RAKKIB_PYTHON:-}"
MAC_PYTHON_VERSION="${RAKKIB_MAC_PYTHON_VERSION:-3.12.10}"
MAC_PYTHON_SHA256="${RAKKIB_MAC_PYTHON_SHA256:-8373e58da4ea146b3eb1c1f9834f19a319440b6b679b06050b1f9ee3237aa8e4}"

log()  { printf '==> %s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
command_exists() { command -v "$1" >/dev/null 2>&1; }

run_quiet() {
  local label="$1"
  shift

  local log_file
  log_file="$(mktemp "${TMPDIR:-/tmp}/rakkib-install.XXXXXX.log")" \
    || die "Failed to create a temporary log file. Check write access to ${TMPDIR:-/tmp} and rerun."

  if "$@" >"$log_file" 2>&1; then
    rm -f "$log_file"
    return 0
  fi

  printf 'ERROR: %s failed.\n' "$label" >&2
  printf 'Log: %s\n' "$log_file" >&2
  cat "$log_file" >&2
  return 1
}

warn_incomplete_venv() {
  local status=$?
  if [[ "${VENV_INSTALL_IN_PROGRESS:-0}" -eq 1 ]]; then
    warn "venv setup was interrupted; remove the incomplete venv with: rm -rf '${INSTALL_DIR}/.venv' && rerun install.sh"
  fi
  exit "$status"
}

trap warn_incomplete_venv INT TERM ERR

_prompt() {
  local var_name="$1" prompt_text="$2"
  if { true < /dev/tty; } 2>/dev/null; then
    printf '%s' "$prompt_text" > /dev/tty
    IFS= read -r "$var_name" < /dev/tty
  else
    printf '%s' "$prompt_text"
    IFS= read -r "$var_name"
  fi
}

detect_platform() {
  case "$(uname -s 2>/dev/null || true)" in
    Linux) PLATFORM="linux" ;;
    Darwin) PLATFORM="mac" ;;
    *) die "unsupported OS; expected Linux or macOS" ;;
  esac
}

# Pick install directory
SUDO_USER_HOME=""
if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
  if command_exists getent; then
    SUDO_USER_HOME="$(getent passwd "$SUDO_USER" 2>/dev/null | cut -d: -f6 || true)"
  elif [[ -d "/Users/${SUDO_USER}" ]]; then
    SUDO_USER_HOME="/Users/${SUDO_USER}"
  fi
fi

if [[ -z "${RAKKIB_DIR:-}" && -f "pyproject.toml" && -d ".git" ]]; then
  INSTALL_DIR="$(pwd)"
elif [[ -n "${RAKKIB_DIR:-}" ]]; then
  INSTALL_DIR="${RAKKIB_DIR}"
elif [[ "${EUID:-$(id -u)}" -eq 0 && -n "$SUDO_USER_HOME" ]]; then
  INSTALL_DIR="${SUDO_USER_HOME}/Rakkib"
elif [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  INSTALL_DIR="/opt/rakkib"
else
  INSTALL_DIR="${HOME}/Rakkib"
fi

usage() {
  cat <<'USAGE'
Usage: install.sh [--dir <path>] [--repo <url>] [--branch <name>]

Rakkib bootstrapper. Clones or updates the repo, creates a project-local
venv, installs the rakkib CLI into it, and links it onto PATH.

Environment overrides:
  RAKKIB_DIR       target checkout path   (default: $HOME/Rakkib)
  RAKKIB_REPO      git repo URL           (default: https://github.com/FayaaDev/Rakkib.git)
  RAKKIB_BRANCH    git branch             (default: runtime)
  RAKKIB_UPDATE_MODE  reset|skip          (default: reset)
USAGE
}

parse_args() {
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --dir)    [[ "$#" -ge 2 ]] || die "missing value for --dir";    INSTALL_DIR="$2"; shift 2 ;;
      --repo)   [[ "$#" -ge 2 ]] || die "missing value for --repo";   REPO_URL="$2";    shift 2 ;;
      --branch) [[ "$#" -ge 2 ]] || die "missing value for --branch"; BRANCH="$2";      shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) die "unknown argument: $1" ;;
    esac
  done
}

confirm_root() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    if [[ ! -t 0 ]]; then
      warn "running Rakkib as root in non-interactive mode; continuing because stdin is not a terminal."
      return
    fi
    local answer
    [[ -e /dev/tty ]] && printf 'WARNING: You are running Rakkib as root.\n' > /dev/tty
    _prompt answer 'Are you sure you want to continue? (y/N) ' || exit 1
    case "$answer" in y|Y) ;; *) exit 1 ;; esac
  fi
}

ensure_tooling() {
  command_exists curl || die "curl is required. Install curl and rerun."
  if ! git_usable && [[ "${PLATFORM:-}" != "mac" ]]; then
    die "git is required. Install git and rerun."
  fi
  if [[ "${PLATFORM:-}" == "mac" ]] && ! git_usable; then
    command_exists tar || die "tar is required to download Rakkib without git. Install tar and rerun."
  fi
}

git_path() {
  command -v git 2>/dev/null || true
}

git_usable() {
  local path
  path="$(git_path)"
  [[ -n "$path" ]] || return 1

  if [[ "${PLATFORM:-}" == "mac" && "$path" == "/usr/bin/git" ]]; then
    command_exists xcode-select || return 1
    xcode-select -p >/dev/null 2>&1 || return 1
  fi

  return 0
}

# Block until all dpkg/apt lock files are free.
# On fresh Ubuntu 24.04, unattended-upgrades holds these at first boot.
# flock is always present (util-linux), so this is safe on bare metal.
wait_for_apt_locks() {
  local lock_files=(
    /var/lib/dpkg/lock-frontend
    /var/lib/dpkg/lock
    /var/lib/apt/lists/lock
    /var/cache/apt/archives/lock
  )
  local waited=0
  while true; do
    local busy=0
    for f in "${lock_files[@]}"; do
      if [[ -e "$f" ]] && ! sudo flock -n "$f" true 2>/dev/null; then
        busy=1
        break
      fi
    done
    [[ $busy -eq 0 ]] && return 0
    if [[ $waited -eq 0 ]]; then
      log "Ubuntu automatic updates are running; waiting for apt/dpkg to become available..."
    fi
    sleep 5
    waited=$((waited + 5))
    [[ $waited -ge 900 ]] && die "Timed out after 15 min waiting for apt/dpkg locks. Ubuntu automatic updates or another package manager is still running. Wait for it to finish and rerun install.sh; if it is stuck, run 'sudo systemctl stop unattended-upgrades' and rerun."
  done
}

apt_get() {
  local timeout="${RAKKIB_APT_LOCK_TIMEOUT:-900}"
  sudo env \
    DEBIAN_FRONTEND=noninteractive \
    APT_LISTCHANGES_FRONTEND=none \
    NEEDRESTART_MODE=a \
    NEEDRESTART_SUSPEND=1 \
    UCF_FORCE_CONFFOLD=1 \
    apt-get -o "DPkg::Lock::Timeout=${timeout}" "$@"
}

python_has_venv() {
  local candidate="$1"
  [[ -n "$candidate" ]] || return 1
  "$candidate" -c "import venv, ensurepip" >/dev/null 2>&1
}

select_python_cmd() {
  local candidates=()
  [[ -n "${RAKKIB_PYTHON:-}" ]] && candidates+=("${RAKKIB_PYTHON}")
  if command_exists python3; then
    candidates+=("$(command -v python3)")
  fi
  if [[ "${PLATFORM:-}" == "mac" ]]; then
    local major_minor="${MAC_PYTHON_VERSION%.*}"
    candidates+=(
      "/Library/Frameworks/Python.framework/Versions/${major_minor}/bin/python3"
      "/Library/Frameworks/Python.framework/Versions/Current/bin/python3"
    )
  fi

  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -x "$candidate" ]] && python_has_venv "$candidate"; then
      PYTHON_CMD="$candidate"
      return 0
    fi
  done
  return 1
}

mac_python_pkg_url() {
  printf 'https://www.python.org/ftp/python/%s/python-%s-macos11.pkg\n' "$MAC_PYTHON_VERSION" "$MAC_PYTHON_VERSION"
}

sha256_file() {
  local path="$1"
  if [[ "${PLATFORM:-}" == "mac" ]] && command_exists shasum; then
    shasum -a 256 "$path" | awk '{print $1}'
  elif command_exists sha256sum; then
    sha256sum "$path" | awk '{print $1}'
  elif command_exists shasum; then
    shasum -a 256 "$path" | awk '{print $1}'
  else
    die "Cannot verify download checksum because neither sha256sum nor shasum is available."
  fi
}

verify_sha256() {
  local path="$1" expected="$2" actual
  actual="$(sha256_file "$path")"
  [[ "$actual" == "$expected" ]] || die "Checksum mismatch for ${path}. Expected ${expected}, got ${actual}. Delete the file and rerun."
}

install_python_macos_pkg() {
  local pkg url
  pkg="$(mktemp "${TMPDIR:-/tmp}/rakkib-python.XXXXXX.pkg")" \
    || die "Failed to create a temporary Python package path. Check write access to ${TMPDIR:-/tmp} and rerun."
  url="$(mac_python_pkg_url)"

  log "Downloading Python ${MAC_PYTHON_VERSION} for macOS..."
  run_quiet "Downloading Python ${MAC_PYTHON_VERSION}" curl -fsSL -o "$pkg" "$url" \
    || die "Failed to download Python from ${url}. Check network access and rerun."
  verify_sha256 "$pkg" "$MAC_PYTHON_SHA256"

  log "Installing Python ${MAC_PYTHON_VERSION} via macOS installer..."
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    run_quiet "Installing Python ${MAC_PYTHON_VERSION}" installer -pkg "$pkg" -target / \
      || die "Python installer failed. Open the installer log above, resolve the macOS installer error, and rerun."
  else
    run_quiet "Installing Python ${MAC_PYTHON_VERSION}" sudo installer -pkg "$pkg" -target / \
      || die "Python installer failed. Re-run from an admin account or install Python from python.org, then rerun."
  fi
  rm -f "$pkg"
}

ensure_python_macos() {
  if command_exists brew; then
    log "Installing Python via existing Homebrew..."
    run_quiet "Installing Python via Homebrew" brew install python \
      || warn "Homebrew Python install failed; falling back to Python.org installer."
    select_python_cmd && return 0
  fi

  install_python_macos_pkg
  select_python_cmd || die "Python ${MAC_PYTHON_VERSION} installed, but venv/ensurepip is still unavailable. Open a new terminal and rerun."
}

# Install python3 + python3-venv via the system package manager.
ensure_python3_and_venv() {
  if select_python_cmd; then
    return 0
  fi

  if command_exists apt-get; then
    local need_python need_venv
    need_python=0; need_venv=0
    command_exists python3 || need_python=1
    python3 -c "import venv, ensurepip" 2>/dev/null || need_venv=1
    local pkgs=()
    [[ $need_python -eq 1 ]] && pkgs+=(python3)
    if [[ $need_venv -eq 1 ]]; then
      local pyver
      pyver=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "")
      pkgs+=(python3-venv)
      [[ -n "$pyver" ]] && pkgs+=("python${pyver}-venv")
    fi
    wait_for_apt_locks
    log "Refreshing apt index..."
    run_quiet "Refreshing apt index" apt_get update -qq -o Acquire::Retries=3 \
      || warn "apt-get update failed; continuing with existing index."
    log "Installing ${pkgs[*]} via apt-get..."
    wait_for_apt_locks
    run_quiet "Installing ${pkgs[*]} via apt-get" apt_get install -y -qq --no-install-recommends "${pkgs[@]}" \
      || die "Failed to install ${pkgs[*]}. Run 'sudo apt-get update && sudo apt-get install --no-install-recommends ${pkgs[*]}' and rerun install.sh."
  elif command_exists dnf; then
    local pkgs=()
    command_exists python3 || pkgs+=(python3)
    # venv ships with python3 on Fedora/RHEL
    [[ ${#pkgs[@]} -gt 0 ]] && sudo dnf install -y "${pkgs[@]}"
  elif command_exists pacman; then
    command_exists python3 || sudo pacman -Sy --noconfirm python
  elif [[ "${PLATFORM:-}" == "mac" ]]; then
    ensure_python_macos
  elif command_exists brew; then
    brew install python
  else
    die "Could not find a package manager. Install python3 (with venv module) manually and rerun."
  fi

  select_python_cmd || die "python3-venv unavailable (including ensurepip). Install it manually and rerun."
}

is_empty_dir() {
  [[ -d "$1" ]] || return 1
  [[ -z "$(ls -A "$1" 2>/dev/null)" ]]
}

repo_has_local_changes() {
  [[ -n "$(git -C "$INSTALL_DIR" status --porcelain 2>/dev/null)" ]]
}

repo_local_changes() {
  git -C "$INSTALL_DIR" status --short 2>/dev/null || true
}

discard_repo_local_changes() {
  git -C "$INSTALL_DIR" reset --hard HEAD
  git -C "$INSTALL_DIR" clean -fd
}

repo_archive_url() {
  local repo="$REPO_URL" path owner name
  case "$repo" in
    https://github.com/*/*.git) path="${repo#https://github.com/}"; path="${path%.git}" ;;
    https://github.com/*/*) path="${repo#https://github.com/}"; path="${path%.git}" ;;
    git@github.com:*/*.git) path="${repo#git@github.com:}"; path="${path%.git}" ;;
    *) die "git is missing and RAKKIB_REPO is not a supported GitHub URL: ${REPO_URL}" ;;
  esac
  owner="${path%%/*}"
  name="${path#*/}"
  [[ -n "$owner" && -n "$name" ]] \
    || die "Could not derive GitHub archive URL from RAKKIB_REPO=${REPO_URL}"
  printf 'https://codeload.github.com/%s/%s/tar.gz/refs/heads/%s\n' "$owner" "$name" "$BRANCH"
}

repo_is_archive_checkout() {
  [[ -f "${INSTALL_DIR}/.rakkib-archive-install" && -f "${INSTALL_DIR}/pyproject.toml" ]]
}

replace_dir_from_archive_source() {
  local source_dir="$1" backup=""
  mkdir -p "$(dirname "$INSTALL_DIR")"
  if [[ -e "$INSTALL_DIR" ]]; then
    backup="${INSTALL_DIR}.previous.$$"
    mv "$INSTALL_DIR" "$backup" || die "Failed to move existing ${INSTALL_DIR} aside for update."
  fi
  mkdir -p "$INSTALL_DIR" || die "Failed to create ${INSTALL_DIR}."
  if cp -R "${source_dir}/." "$INSTALL_DIR/"; then
    rm -rf "$backup"
  else
    rm -rf "$INSTALL_DIR"
    [[ -n "$backup" && -e "$backup" ]] && mv "$backup" "$INSTALL_DIR"
    die "Failed to copy downloaded Rakkib archive into ${INSTALL_DIR}."
  fi
}

prepare_repo_archive() {
  local archive tmpdir extracted entries url
  if [[ -e "$INSTALL_DIR" ]] && ! is_empty_dir "$INSTALL_DIR"; then
    if repo_is_archive_checkout; then
      case "$UPDATE_MODE" in
        reset) ;;
        skip)
          warn "Using existing archive checkout because RAKKIB_UPDATE_MODE=skip."
          return 0
          ;;
        *) die "invalid RAKKIB_UPDATE_MODE '${UPDATE_MODE}'. Use 'reset' or 'skip'." ;;
      esac
    else
      die "target path exists and is not an empty Rakkib archive checkout: ${INSTALL_DIR}"
    fi
  fi

  command_exists tar || die "tar is required to download Rakkib without git. Install tar and rerun."
  archive="$(mktemp "${TMPDIR:-/tmp}/rakkib-source.XXXXXX.tar.gz")" \
    || die "Failed to create a temporary archive path. Check write access to ${TMPDIR:-/tmp} and rerun."
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/rakkib-source.XXXXXX")" \
    || die "Failed to create a temporary extraction directory. Check write access to ${TMPDIR:-/tmp} and rerun."
  url="$(repo_archive_url)"

  log "Downloading ${REPO_URL} branch ${BRANCH} without git"
  run_quiet "Downloading ${REPO_URL} archive" curl -fsSL -o "$archive" "$url" \
    || die "Failed to download ${url}. Check network access and branch name, then rerun."
  run_quiet "Extracting ${REPO_URL} archive" tar -xzf "$archive" -C "$tmpdir" \
    || die "Failed to extract downloaded Rakkib archive. Delete ${archive} and rerun."

  entries=("$tmpdir"/*)
  extracted="${entries[0]:-}"
  [[ -d "$extracted" && -f "$extracted/pyproject.toml" ]] \
    || die "Downloaded archive did not contain a Rakkib checkout."
  replace_dir_from_archive_source "$extracted"
  {
    printf 'repo=%s\n' "$REPO_URL"
    printf 'branch=%s\n' "$BRANCH"
  } > "${INSTALL_DIR}/.rakkib-archive-install"
  rm -rf "$archive" "$tmpdir"
}

prepare_repo() {
  if [[ -d "${INSTALL_DIR}/.git" ]]; then
    git_usable || die "Existing git checkout at ${INSTALL_DIR} requires usable git for updates. Install Git/Xcode Command Line Tools or set RAKKIB_DIR to a new path."
    log "Using existing checkout: ${INSTALL_DIR}"
    if repo_has_local_changes; then
      case "$UPDATE_MODE" in
        reset)
          warn "Existing checkout has local changes; discarding them before update because RAKKIB_UPDATE_MODE=reset."
          repo_local_changes >&2
          discard_repo_local_changes
          ;;
        skip)
          warn "Existing checkout has local changes; skipping automatic update because RAKKIB_UPDATE_MODE=skip."
          warn "Set RAKKIB_UPDATE_MODE=reset to discard checkout changes and pull the latest code."
          repo_local_changes >&2
          return 0
          ;;
        *)
          die "invalid RAKKIB_UPDATE_MODE '${UPDATE_MODE}'. Use 'reset' or 'skip'."
          ;;
      esac
    fi
    log "Updating from origin/${BRANCH}"
    run_quiet "Fetching origin/${BRANCH}" git -C "$INSTALL_DIR" fetch origin "$BRANCH" \
      || die "Failed to fetch origin/${BRANCH}. Check git access and rerun install.sh."
    if git -C "$INSTALL_DIR" show-ref --verify --quiet "refs/heads/${BRANCH}"; then
      run_quiet "Switching to ${BRANCH}" git -C "$INSTALL_DIR" switch "$BRANCH" \
        || die "Failed to switch to branch ${BRANCH}. Resolve the checkout state and rerun install.sh."
    else
      run_quiet "Creating branch ${BRANCH}" git -C "$INSTALL_DIR" switch -c "$BRANCH" "origin/${BRANCH}" \
        || die "Failed to create local branch ${BRANCH} from origin/${BRANCH}. Check the repository state and rerun install.sh."
    fi
    case "$UPDATE_MODE" in
      reset)
        run_quiet "Resetting ${BRANCH} to origin/${BRANCH}" git -C "$INSTALL_DIR" reset --hard "origin/${BRANCH}" \
          || die "Failed to reset ${BRANCH} to origin/${BRANCH}. Resolve the checkout state and rerun install.sh."
        ;;
      skip)
        run_quiet "Pulling origin/${BRANCH}" git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH" \
          || die "Failed to fast-forward ${BRANCH} from origin/${BRANCH}. Resolve the checkout state and rerun install.sh."
        ;;
      *)
        die "invalid RAKKIB_UPDATE_MODE '${UPDATE_MODE}'. Use 'reset' or 'skip'."
        ;;
    esac
    return 0
  fi

  if ! git_usable; then
    if [[ "${PLATFORM:-}" == "mac" ]]; then
      prepare_repo_archive
      return 0
    fi
    die "git is required. Install git and rerun."
  fi

  if [[ -e "$INSTALL_DIR" ]] && ! is_empty_dir "$INSTALL_DIR"; then
    die "target path exists and is not an empty git checkout: ${INSTALL_DIR}"
  fi

  mkdir -p "$(dirname "$INSTALL_DIR")"
  log "Cloning ${REPO_URL} into ${INSTALL_DIR}"
  run_quiet "Cloning ${REPO_URL}" git clone --depth 1 --single-branch --no-tags --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" \
    || die "Failed to clone ${REPO_URL}. Check git access and rerun install.sh."
}

ensure_venv_install() {
  local venv_dir="${INSTALL_DIR}/.venv"
  local bin_dir="${HOME}/.local/bin"
  local target="${bin_dir}/rakkib"
  VENV_INSTALL_IN_PROGRESS=1

  if [[ ! -d "$venv_dir" ]]; then
    log "Creating venv at ${venv_dir}"
    run_quiet "Creating venv at ${venv_dir}" "$PYTHON_CMD" -m venv "$venv_dir" \
      || run_quiet "Creating venv at ${venv_dir} without pip" "$PYTHON_CMD" -m venv --without-pip "$venv_dir" \
      || die "Failed to create venv at ${venv_dir}. Install python3-venv and rerun."
  fi

  if [[ ! -x "${venv_dir}/bin/pip" ]]; then
    log "pip absent from venv; bootstrapping via get-pip.py..."
    command_exists curl || die "curl is required to bootstrap pip. Install curl and rerun."
    run_quiet "Bootstrapping pip in ${venv_dir}" bash -lc 'curl -fsSL https://bootstrap.pypa.io/get-pip.py | "$1"' -- "${venv_dir}/bin/python" \
      || die "Failed to bootstrap pip. Check network and rerun."
  fi

  log "Installing rakkib into venv..."
  run_quiet "Installing rakkib into venv" "${venv_dir}/bin/pip" install -q -e "${INSTALL_DIR}" \
    || die "pip install failed. Check the error above and rerun."

  mkdir -p "$bin_dir"
  # Overwrite symlink if it points elsewhere (e.g. stale pipx path)
  if [[ -L "$target" || ! -e "$target" ]]; then
    ln -sf "${venv_dir}/bin/rakkib" "$target"
    log "Linked ${target} -> ${venv_dir}/bin/rakkib"
  else
    warn "${target} exists and is not a symlink; skipping link creation."
  fi
  VENV_INSTALL_IN_PROGRESS=0
}

ensure_shell_path() {
  local marker="# Added by Rakkib: user-local bin on PATH"
  local files=()
  if [[ "${PLATFORM:-}" == "mac" ]]; then
    files=("${HOME}/.zshrc" "${HOME}/.zprofile" "${HOME}/.profile")
  else
    [[ -f "${HOME}/.bashrc"  ]] && files+=("${HOME}/.bashrc")
    [[ -f "${HOME}/.zshrc"   ]] && files+=("${HOME}/.zshrc")
    [[ -f "${HOME}/.profile" ]] && files+=("${HOME}/.profile")
    [[ ${#files[@]} -eq 0 ]] && files=("${HOME}/.bashrc")
  fi

  for profile in "${files[@]}"; do
    grep -Fq "$marker" "$profile" 2>/dev/null && continue
    touch "$profile"
    {
      printf '\n%s\n' "$marker"
      printf '%s\n' 'case ":$PATH:" in'
      printf '%s\n' '  *":$HOME/.local/bin:"*) ;;'
      printf '%s\n' '  *) export PATH="$HOME/.local/bin:$PATH" ;;'
      printf '%s\n' 'esac'
    } >> "$profile"
    log "Added ~/.local/bin to PATH in ${profile}"
  done
}

print_next_steps() {
  if [[ "${PLATFORM:-}" == "mac" ]]; then
    cat <<EOF

Rakkib is installed.

Repo:  ${INSTALL_DIR}
Venv:  ${INSTALL_DIR}/.venv

Next step:
  rakkib web

If rakkib is not on PATH yet, run one of:
  source ~/.zshrc   |   source ~/.zprofile   |   source ~/.profile

Or run directly:
  ${HOME}/.local/bin/rakkib web

For local service testing on macOS, install and start Docker Desktop first.
Verify it with 'docker info'. Rakkib does not use Linux docker-group repair on macOS.

To uninstall:
  rakkib uninstall --yes

EOF
    return
  fi

  cat <<EOF

Rakkib is installed.

Repo:  ${INSTALL_DIR}
Venv:  ${INSTALL_DIR}/.venv

Next steps:
  rakkib init
  rakkib pull

If rakkib is not on PATH yet, run one of:
  source ~/.bashrc   |   source ~/.zshrc   |   source ~/.profile

Or run directly:
  ${HOME}/.local/bin/rakkib init

If Docker access needs repair for a non-root user, run 'rakkib auth'.
After it succeeds, open a new shell or run 'newgrp docker', then rerun 'rakkib pull'.

To uninstall:
  rakkib uninstall --yes

EOF
}

main() {
  parse_args "$@"
  detect_platform
  confirm_root
  ensure_tooling
  ensure_python3_and_venv
  prepare_repo
  ensure_venv_install
  ensure_shell_path
  print_next_steps
}

if [[ "${RAKKIB_INSTALL_TEST_MODE:-0}" != "1" ]]; then
  main "$@"
fi
