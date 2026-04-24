# Question File 04 — Cloudflare

**Phase 4 of 6. No writes outside the repo occur during this phase.**

---

## Instructions for the Agent

Ask the questions below in order. Record the answers into `.fss-state.yaml` under the `cloudflare:` section.

This phase only determines the intended Cloudflare setup. It does not create the tunnel yet. Tunnel login, tunnel creation, DNS routing, and credentials placement happen later in `steps/40-cloudflare.md`.

---

## Questions to Ask

### Q1 — Zone Ownership

Ask: "Is your base domain already managed in Cloudflare in the same account you will use for this server? (y/n)"

Accepted answers: `y` or `n`. Normalize to boolean.

If `n`, the agent must explain that the domain is not yet in a Cloudflare state this installer can manage for DNS and tunnel routing.

The agent must then help the user choose the right Cloudflare zone setup before continuing:

- Recommend Cloudflare primary setup (full) in most cases. This is the standard option where Cloudflare becomes the authoritative DNS provider for the whole domain.
- Explain that CNAME setup (partial) is only available on Business or Enterprise plans and only proxies specific hostnames while primary DNS stays elsewhere.
- Use Cloudflare's zone setup docs as the source of truth:
  - overview: `https://developers.cloudflare.com/dns/zone-setups/`
  - primary setup (full): `https://developers.cloudflare.com/dns/zone-setups/full-setup/`
  - CNAME setup (partial): `https://developers.cloudflare.com/dns/zone-setups/partial-setup/`
- Tell the user that Free and Pro plans should use primary setup (full).
- Ask the user to finish adding the domain to the intended Cloudflare account and reach an active zone state before relying on public DNS routing and HTTPS verification.

If the user wants to continue before doing that, the agent may continue the interview and local-only setup, but it must clearly state that `steps/40-cloudflare.md` and public verification in `steps/90-verify.md` cannot fully pass until the domain is managed in Cloudflare.

### Q2 — Tunnel Strategy

Ask: "Will you create a new Cloudflare tunnel for this server, or reuse an existing one? (new/existing)"

Accepted answers:
- `new`
- `existing`

### Q3 — Tunnel Name

Ask: "What tunnel name should be used? [default: <server_name>]"

If the user gives an empty answer, use `server_name` from `.fss-state.yaml`.

Validation: non-empty.

### Q4 — SSH Hostname

Ask: "What subdomain should route to SSH over Cloudflare? [default: ssh]"

If the user gives an empty answer, use `ssh`.

Validation: lowercase letters, numbers, and hyphens only.

Record this as the SSH subdomain only, not the full hostname.

### Q5 — Existing Tunnel Details

Only ask this if Q2 was `existing`.

Ask: "Do you already know the existing tunnel UUID? (y/n)"

Accepted answers: `y` or `n`.

If `y`, ask:
- "Existing tunnel UUID?"

If `n`, record that the UUID must be gathered during `steps/40-cloudflare.md` before rendering `config.yml`.

Regardless of whether the tunnel is new or existing, the final credentials file location must always be normalized during `steps/40-cloudflare.md` to:

- host path: `{{DATA_ROOT}}/data/cloudflared/<tunnel_uuid>.json`
- container path: `/home/nonroot/.cloudflared/<tunnel_uuid>.json`

---

## Record in .fss-state.yaml

```yaml
cloudflare:
  zone_in_cloudflare: true
  tunnel_strategy: new      # or: existing
  tunnel_name: myserver
  ssh_subdomain: ssh
  tunnel_uuid: null
  tunnel_creds_host_path: null
  tunnel_creds_container_path: null
```

If the user provided the UUID, record it and derive the two credentials paths immediately. Otherwise leave them as `null` until `steps/40-cloudflare.md`.
