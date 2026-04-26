# Step 70 — Host Agents

Install host-level services that are not Docker containers.

## Actions

Only run this step if `openclaw` or `hermes` is selected.

Linux:
1. If `openclaw` is selected, ensure `node >= 22.14.0` and `npm` are installed.
2. Keep the installer agent running as the normal admin user. Use `sudo` only for package installation, linger, and any system-level commands that require it.
3. If `openclaw` is selected and Node.js is missing or too old on Ubuntu 24.04, install Node.js 22 LTS with explicit `sudo` commands before continuing.
4. If `openclaw` is selected, verify `node --version` and `npm --version` before installing OpenClaw.
5. If `openclaw` is selected, resolve the admin home with `getent passwd {{ADMIN_USER}} | cut -d: -f6`, then install OpenClaw into that user-scoped prefix as the admin user with `npm install -g --prefix "$ADMIN_HOME/.local" openclaw@latest` or an equivalent user-scoped command.
6. If `openclaw` is selected, verify the real entrypoint exists at `$ADMIN_HOME/.local/bin/openclaw` before writing the unit file.
7. If `openclaw` is selected, render `templates/systemd/claw-gateway.service.tmpl` into `$ADMIN_HOME/.config/systemd/user/openclaw-gateway.service`.
8. If `hermes` is selected, require `authentik` in `foundation_services`, install Hermes with `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash -s -- --skip-setup`, and verify `$ADMIN_HOME/.local/bin/hermes` exists.
9. If `hermes` is selected, render `templates/systemd/hermes-dashboard.service.tmpl` into `$ADMIN_HOME/.config/systemd/user/hermes-dashboard.service`.
10. Run `systemctl --user daemon-reload` for the admin user.
11. Enable linger with `sudo loginctl enable-linger {{ADMIN_USER}}` so the user service survives logout and reboots.
12. Enable and start each selected service.

Mac:
1. If `openclaw` is selected, ensure `node >= 22.14.0` and `npm` are installed.
2. If `openclaw` is selected and Node.js is missing or too old, install Node.js 22 LTS first with Homebrew:
   `brew install node@22`
3. If `openclaw` is selected, verify `node --version` and `npm --version` before installing OpenClaw.
4. If `openclaw` is selected, install OpenClaw into a user-scoped prefix with `npm install -g --prefix "$HOME/.local" openclaw@latest`.
5. If `openclaw` is selected, verify the real entrypoint exists at `~/.local/bin/openclaw` before writing the plist.
6. If `openclaw` is selected, render `templates/launchd/claw-gateway.plist.tmpl` into `~/Library/LaunchAgents/openclaw-gateway.plist`.
7. If `hermes` is selected, require `authentik` in `foundation_services`, install Hermes with `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash -s -- --skip-setup`, and verify `~/.local/bin/hermes` exists.
8. If `hermes` is selected, render `templates/launchd/hermes-dashboard.plist.tmpl` into `~/Library/LaunchAgents/hermes-dashboard.plist`.
9. Load each selected plist with `launchctl bootstrap gui/$(id -u) <plist>`.

## Verify

Linux:
- if OpenClaw is selected: `systemctl --user status openclaw-gateway.service --no-pager`
- if Hermes is selected: `systemctl --user status hermes-dashboard.service --no-pager`

Mac:
- if OpenClaw is selected: `launchctl print gui/$(id -u)/openclaw-gateway`
- if Hermes is selected: `launchctl print gui/$(id -u)/hermes-dashboard`

Both:
- if OpenClaw is selected: `node --version`
- if OpenClaw is selected: `npm --version`
- if OpenClaw is selected: `curl -I http://localhost:{{CLAW_GATEWAY_PORT}}/`

Linux only:
- if OpenClaw is selected: `ADMIN_HOME="$(getent passwd {{ADMIN_USER}} | cut -d: -f6)"; test -x "$ADMIN_HOME/.local/bin/openclaw"`
- if OpenClaw is selected: `ADMIN_HOME="$(getent passwd {{ADMIN_USER}} | cut -d: -f6)"; "$ADMIN_HOME/.local/bin/openclaw" --version`
- if Hermes is selected: `ADMIN_HOME="$(getent passwd {{ADMIN_USER}} | cut -d: -f6)"; test -x "$ADMIN_HOME/.local/bin/hermes"`
- if Hermes is selected: `ADMIN_HOME="$(getent passwd {{ADMIN_USER}} | cut -d: -f6)"; "$ADMIN_HOME/.local/bin/hermes" --version`
- if Hermes is selected: `curl -I http://{{HOST_GATEWAY}}:{{HERMES_DASHBOARD_PORT}}/`

Mac only:
- if OpenClaw is selected: `test -x "$HOME/.local/bin/openclaw"`
- if OpenClaw is selected: `"$HOME/.local/bin/openclaw" --version`
- if Hermes is selected: `test -x "$HOME/.local/bin/hermes"`
- if Hermes is selected: `"$HOME/.local/bin/hermes" --version`
- if Hermes is selected: `curl -I http://127.0.0.1:{{HERMES_DASHBOARD_PORT}}/`
