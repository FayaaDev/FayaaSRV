# Step 70 — Host Agents

Install host-level services that are not Docker containers.

## Actions

Only run this step if `openclaw` is selected.

Linux:
1. Ensure `node >= 22.14.0` and `npm` are installed.
2. Keep the installer agent running as the normal admin user. Use `sudo` only for package installation, linger, and any system-level commands that require it.
3. If Node.js is missing or too old on Ubuntu 24.04, install Node.js 22 LTS with explicit `sudo` commands before continuing.
4. Verify `node --version` and `npm --version` before installing OpenClaw.
5. Resolve the admin home with `getent passwd {{ADMIN_USER}} | cut -d: -f6`, then install OpenClaw into that user-scoped prefix as the admin user with `npm install -g --prefix "$ADMIN_HOME/.local" openclaw@latest` or an equivalent user-scoped command.
6. Verify the real entrypoint exists at `$ADMIN_HOME/.local/bin/openclaw` before writing the unit file.
7. Render `templates/systemd/claw-gateway.service.tmpl` into `$ADMIN_HOME/.config/systemd/user/openclaw-gateway.service`.
8. Run `systemctl --user daemon-reload` for the admin user.
9. Enable linger with `sudo loginctl enable-linger {{ADMIN_USER}}` so the user service survives logout and reboots.
10. Enable and start the service.

Mac:
1. Ensure `node >= 22.14.0` and `npm` are installed.
2. If Node.js is missing or too old, install Node.js 22 LTS first with Homebrew:
   `brew install node@22`
3. Verify `node --version` and `npm --version` before installing OpenClaw.
4. Install OpenClaw into a user-scoped prefix with `npm install -g --prefix "$HOME/.local" openclaw@latest`.
5. Verify the real entrypoint exists at `~/.local/bin/openclaw` before writing the plist.
6. Render `templates/launchd/claw-gateway.plist.tmpl` into `~/Library/LaunchAgents/openclaw-gateway.plist`.
7. Load it with `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/openclaw-gateway.plist`.

## Verify

Linux:
- `systemctl --user status openclaw-gateway.service --no-pager`

Mac:
- `launchctl print gui/$(id -u)/openclaw-gateway`

Both:
- `node --version`
- `npm --version`
- `ADMIN_HOME="$(getent passwd {{ADMIN_USER}} | cut -d: -f6)"; test -x "$ADMIN_HOME/.local/bin/openclaw"`
- `ADMIN_HOME="$(getent passwd {{ADMIN_USER}} | cut -d: -f6)"; "$ADMIN_HOME/.local/bin/openclaw" --version`
- `curl -I http://localhost:{{CLAW_GATEWAY_PORT}}/`
