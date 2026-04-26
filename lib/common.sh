#!/usr/bin/env bash

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

shell_quote() {
  printf '%q' "$1"
}

state_value() {
  local state_file="$1"
  local key="$2"
  [[ -f "$state_file" ]] || return 1
  awk -F: -v wanted="$key" '
    $1 == wanted {
      value=$0
      sub("^[^:]*:", "", value)
      sub("^[[:space:]]*", "", value)
      sub("[[:space:]]*$", "", value)
      gsub(/^"|"$/, "", value)
      print value
      exit
    }
  ' "$state_file"
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
