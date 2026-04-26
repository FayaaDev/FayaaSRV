# VErgo Terminal Integration Plan

## Goal

Integrate VErgo into Rakkib as an optional, Rakkib-native host addon for terminal setup only.

VErgo Terminal must preserve Rakkib's interview -> state -> render -> verify flow and must not be treated as a Docker service, public route, or normal app service.

## Product Shape

Implement one optional host addon:

```yaml
host_addons:
  - vergo_terminal
```

`vergo_terminal` supports Linux and Mac.

## User Outcome

If `vergo_terminal` is selected, users get:

- `zsh`
- `zi`
- `powerlevel10k`
- `zsh-autosuggestions`
- `fast-syntax-highlighting`
- `zsh-completions`
- `eza`
- `zoxide`
- `fzf`
- Meslo Nerd Font files
- managed `~/.zshrc`
- managed `~/.zshenv`
- managed `~/.p10k.zsh`
- guarded optional integrations when present, such as `bun`, `nvm`, Docker completions, Android SDK paths, and `openclaw` completions

Mac users additionally get:

- `wezterm`
- managed `~/.wezterm.lua`

## Explicitly Out Of Scope

- macOS window-manager setup
- desktop status bars or border tools
- macOS login item registration
- macOS Accessibility permission flow
- desktop/window-manager configuration under `~/.config`
- the current remote `curl` VErgo installer path
- `VErgo/opencode/command/power10k.md`
- personal hardcoded workstation paths or wrappers

## Design Principles

1. Keep VErgo opt-in.
2. Represent VErgo as a host addon, not a service.
3. Use repo-local shell assets instead of downloading raw VErgo templates during install.
4. Preserve Rakkib idempotency rules.
5. Back up user-owned dotfiles before replacing them.
6. Keep platform-specific behavior explicit.
7. Avoid changing the user's login shell automatically.

## Rakkib Changes

### Interview

Extend `questions/03-services.md` with an optional host-addon section:

```text
Optional Host Addons:
  [ ] 10 VErgo Terminal - zsh, prompt, completions, CLI UX
```

Warn that VErgo Terminal modifies the admin user's shell dotfiles and backs up existing files before replacement.

### State

Record selected host addons separately from selected services:

```yaml
host_addons:
  - vergo_terminal
```

Do not create subdomains for host addons.

### Assets

Use Rakkib-managed terminal assets:

- `templates/vergo/zshrc.mac.zsh.tmpl`
- `templates/vergo/zshrc.ubuntu.zsh.tmpl`
- `templates/vergo/zshenv.mac.zsh.tmpl`
- `templates/vergo/zshenv.ubuntu.zsh.tmpl`
- `files/vergo/.p10k.zsh`
- `files/vergo/.wezterm.lua`

### Steps

Add a dedicated post-confirmation step:

- `steps/72-host-customization.md`

Execution order:

1. `steps/70-host-agents.md`
2. `steps/72-host-customization.md`
3. `steps/80-backups.md`

## Step Design

`steps/72-host-customization.md` only runs when `host_addons` contains `vergo_terminal`.

Linux actions:

1. Ensure `apt-get` exists.
2. Install `zsh`, `git`, `curl`, `eza`, `zoxide`, and `fzf`.
3. Install or update `zi` into `~/.zi/bin`.
4. Install missing Meslo Nerd Font files into `~/.local/share/fonts`.
5. Render or copy the Ubuntu shell files into place.
6. Back up changed existing dotfiles to `~/.backup-vergo/<timestamp>/`.
7. Warn if the current login shell is not `zsh`; do not force `chsh`.

Mac actions:

1. Ensure Homebrew exists; stop and ask before installing it if missing.
2. Install `zsh`, `git`, `curl`, `eza`, `zoxide`, `fzf`, and `wezterm`.
3. Install or update `zi` into `~/.zi/bin`.
4. Install missing Meslo Nerd Font files into `~/Library/Fonts`.
5. Render or copy the macOS shell files into place.
6. Install `~/.wezterm.lua`.
7. Back up changed existing dotfiles to `~/.backup-vergo/<timestamp>/`.
8. Warn if the current login shell is not `zsh`; do not force `chsh`.

## Idempotency Rules

- Compare candidate content before replacing files.
- Do not create backups when target content is unchanged.
- Back up changed existing files under `~/.backup-vergo/<timestamp>/` before replacing them.
- If `~/.zi/bin/.git` exists, update with `git pull --ff-only`; otherwise clone fresh.
- Download Meslo font files only when missing.

## Verification

Verify `vergo_terminal`:

- `command -v zsh`
- `command -v eza`
- `command -v zoxide`
- `command -v fzf`
- `test -f ~/.zshrc`
- `test -f ~/.zshenv`
- `test -f ~/.p10k.zsh`
- `test -d ~/.zi/bin`
- `zsh -i -c exit`

Linux only:

- `test -f "$HOME/.local/share/fonts/MesloLGS NF Regular.ttf"`

Mac only:

- `test -f "$HOME/Library/Fonts/MesloLGS NF Regular.ttf"`
- `test -f ~/.wezterm.lua`

## Acceptance Criteria

The terminal-only integration is complete when:

1. Users can opt into VErgo Terminal during the Rakkib interview.
2. Linux and Mac terminal setup is installed without using remote VErgo bootstrap scripts.
3. Existing user files are backed up before replacement.
4. Rerunning Rakkib does not duplicate backups or unnecessarily rewrite managed VErgo assets.
5. Final verify passes for `vergo_terminal` when selected.
6. No personal-path assumptions remain in installed shell files.
