# VErgo Terminal → Rakkib Fit Assessment

## Context

VErgo is being integrated into Rakkib as a terminal-only host addon. It is not a Docker service, not a public route, and not part of the always-installed core.

## What VErgo Terminal Is

VErgo Terminal is a user-scoped terminal bootstrap for macOS and Ubuntu-style Linux systems. It installs or configures:

- `zsh`
- `zi`
- `powerlevel10k`
- `zsh-autosuggestions`
- `fast-syntax-highlighting`
- `zsh-completions`
- `eza`
- `zoxide`
- `fzf`
- Meslo Nerd Fonts
- `~/.zshrc`
- `~/.zshenv`
- `~/.p10k.zsh`
- macOS-only `wezterm` and `~/.wezterm.lua`

It preserves guarded optional integrations when present, such as `nvm`, `bun`, Docker completions, Android SDK paths, and OpenClaw completions.

## Explicitly Excluded

- macOS window-manager setup
- desktop status bars or border tools
- login item registration
- Accessibility permission flows
- OpenCode slash-command packaging
- personal workstation paths or wrappers

## Difficulty Rating

**Medium-low technically, low-medium conceptually.**

The mechanical work is small because Rakkib is documentation-driven and VErgo already has platform-specific templates. The main conceptual change is adding a host-addon category for user-environment customization.

## Best Rakkib Model

Use a dedicated top-level state key:

```yaml
host_addons:
  - vergo_terminal
```

Do not add VErgo Terminal to `registry.yaml`. `registry.yaml` is a service catalog, and VErgo Terminal has no image, port, subdomain, Caddy route, or service health endpoint.

## Required Rakkib Touchpoints

| File | Change |
|---|---|
| `questions/03-services.md` | Add optional host-addon selection for `VErgo Terminal` |
| `AGENT_PROTOCOL.md` | Add `host_addons` state and `steps/72-host-customization.md` to execution order |
| `lib/idempotency.md` | Add user-dotfile backup-and-replace semantics |
| `lib/placeholders.md` | Add host-addon summary placeholder for generated machine docs |
| `templates/vergo/` | Store Rakkib-managed zsh templates |
| `files/vergo/` | Store Rakkib-managed static terminal files |
| `steps/72-host-customization.md` | Install packages, fonts, Zi, and managed dotfiles |
| `steps/90-verify.md` | Add selected-host-addon verification |
| `README.md` | Document VErgo Terminal as an optional host addon |

## Recommended Idempotency Policy

Use full re-render with backup:

- Compare candidate content before replacing.
- If unchanged, do nothing and create no backup.
- If changed, back up existing files to `~/.backup-vergo/<timestamp>/` before replacing.
- Do not merge shell rc files in the first implementation; merging dotfiles is harder to reason about and less reproducible.

## Verification

Terminal verification should include:

- `command -v zsh`
- `command -v eza`
- `command -v zoxide`
- `command -v fzf`
- `test -d ~/.zi/bin`
- `test -f ~/.zshrc`
- `test -f ~/.zshenv`
- `test -f ~/.p10k.zsh`
- `zsh -i -c exit`

Linux font verification:

- `test -f "$HOME/.local/share/fonts/MesloLGS NF Regular.ttf"`

Mac verification:

- `test -f "$HOME/Library/Fonts/MesloLGS NF Regular.ttf"`
- `test -f ~/.wezterm.lua`

## Bottom Line

The best fit is Plan 1's host-addon model, trimmed to `vergo_terminal` only.

This keeps Rakkib's service model clean while still giving users an opt-in, reproducible terminal setup that follows the installer flow and verification contract.
