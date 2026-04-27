# Step 72 — Host Customization

Install user-scoped host customizations that are not Docker containers, network services, or public routes.

## Actions

Only run this step if `host_addons` contains `vergo_terminal`.

General rules:
1. Keep the installer running as the normal admin user.
2. Use repo-local VErgo assets from `templates/vergo/` and `files/vergo/`; do not run `VErgo/terminal.sh` and do not download shell templates from GitHub.
3. Back up existing managed dotfiles before replacement only when the candidate content differs.
4. Use a timestamped backup directory named `~/.backup-vergo/<YYYYmmddHHMMSS>/`.
5. Do not force the login shell to `zsh`; print `chsh -s <zsh_path>` guidance if the current shell is different.

Managed files for `vergo_terminal`:
- `~/.zshrc`
- `~/.zshenv`
- `~/.p10k.zsh`
- on Mac only: `~/.wezterm.lua`

Recommended replacement procedure for each managed file:
1. Resolve the candidate source file from the repo.
2. If the target does not exist, install the candidate with mode `0644`.
3. If the target exists and has identical content, leave it unchanged and do not create a backup.
4. If the target exists and differs, copy it into the backup directory preserving metadata, then replace it with the candidate and mode `0644`.

Linux actions for `vergo_terminal`:
1. Ensure `apt-get` exists; stop on non-Ubuntu-style Linux in this first implementation.
2. Install required packages with explicit sudo after confirmation: `zsh`, `git`, `curl`, `eza`, `zoxide`, and `fzf`.
3. Install or update Zi:
   - if `~/.zi/bin/.git` exists, run `git -C ~/.zi/bin pull --ff-only`
   - otherwise clone `https://github.com/z-shell/zi.git` into `~/.zi/bin`
4. Install missing Meslo Nerd Font files into `~/.local/share/fonts` from `https://github.com/romkatv/powerlevel10k-media/raw/master/`:
   - `MesloLGS NF Regular.ttf`
   - `MesloLGS NF Bold.ttf`
   - `MesloLGS NF Italic.ttf`
   - `MesloLGS NF Bold Italic.ttf`
5. Run `fc-cache -f ~/.local/share/fonts` when `fc-cache` is available.
6. Install these repo-local files:
   - `templates/vergo/zshrc.ubuntu.zsh.tmpl` -> `~/.zshrc`
   - `templates/vergo/zshenv.ubuntu.zsh.tmpl` -> `~/.zshenv`
   - `files/vergo/.p10k.zsh` -> `~/.p10k.zsh`
7. Warn if the current login shell is not the installed `zsh` path and provide the exact `chsh -s <zsh_path>` command.

Mac actions for `vergo_terminal`:
1. Ensure Homebrew is available; if it is missing, stop and ask the user before installing Homebrew.
2. Install required packages with Homebrew: `zsh`, `git`, `curl`, `eza`, `zoxide`, `fzf`.
3. Install WezTerm with Homebrew cask: `wezterm`.
4. Install or update Zi:
   - if `~/.zi/bin/.git` exists, run `git -C ~/.zi/bin pull --ff-only`
   - otherwise clone `https://github.com/z-shell/zi.git` into `~/.zi/bin`
5. Install missing Meslo Nerd Font files into `~/Library/Fonts` from `https://github.com/romkatv/powerlevel10k-media/raw/master/`:
   - `MesloLGS NF Regular.ttf`
   - `MesloLGS NF Bold.ttf`
   - `MesloLGS NF Italic.ttf`
   - `MesloLGS NF Bold Italic.ttf`
6. Install these repo-local files:
   - `templates/vergo/zshrc.mac.zsh.tmpl` -> `~/.zshrc`
   - `templates/vergo/zshenv.mac.zsh.tmpl` -> `~/.zshenv`
   - `files/vergo/.p10k.zsh` -> `~/.p10k.zsh`
   - `files/vergo/.wezterm.lua` -> `~/.wezterm.lua`
7. Warn if the current login shell is not the installed `zsh` path and provide the exact `chsh -s <zsh_path>` command.

## Verify

Both:
- `command -v zsh`
- `command -v eza`
- `command -v zoxide`
- `command -v fzf`
- `test -d ~/.zi/bin`
- `test -f ~/.zshrc`
- `test -f ~/.zshenv`
- `test -f ~/.p10k.zsh`
- `zsh -i -c exit`

Linux only:
- `test -f "$HOME/.local/share/fonts/MesloLGS NF Regular.ttf"`

Mac only:
- `test -f "$HOME/Library/Fonts/MesloLGS NF Regular.ttf"`
- `test -f ~/.wezterm.lua`
