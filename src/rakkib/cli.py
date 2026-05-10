"""Rakkib CLI entrypoint.

Commands: init, pull, update, doctor, status, add, restart, uninstall, privileged, auth, web
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from rakkib.docker import DockerError, docker_run, is_docker_permission_error
from rakkib.doctor import (
    attempt_fix_cloudflared,
    attempt_fix_docker,
    check_disk,
    check_ram,
    docker_access_commands,
    docker_access_user,
    ensure_prereqs,
    process_owners_for_ports,
    prepare_docker_access,
    run_checks,
    summary_text,
    to_json,
)
from rakkib.interview import run_interview
from rakkib.secrets import token_urlsafe
from rakkib.service_catalog import caddy_enabled, cloudflare_enabled, deployed_service_urls
from rakkib.services_cli import (
    apply_planned_subdomains as _apply_planned_subdomains,
    apply_service_selection as _apply_service_selection,
    build_add_choices as _build_add_choices,
    build_restart_choices as _build_restart_choices,
    deployed_service_lists as _deployed_service_lists,
    installed_service_ids as _installed_service_ids,
    persist_deployed_selection as _persist_deployed_selection,
    print_deployed_urls as _print_deployed_urls,
    prompt_service_subdomains as _prompt_service_subdomains,
    restart_order as _restart_order,
    selected_service_lists as _selected_service_lists,
    summarize_service_diff as _summarize_service_diff,
    validate_selection_dependencies as _validate_service_dependencies,
)
from rakkib.state import State
from rakkib.steps import STEP_MODULES, VerificationResult, load_service_registry, selected_service_defs
from rakkib.steps import postgres as postgres_step
from rakkib.steps import services as services_step
from rakkib.steps.cloudflare import _cloudflared_bin, _show_qr
from rakkib.tui import progress_spinner, prompt_checkbox, prompt_confirm
from rakkib.util import checkout_dir as _checkout_dir, detect_lan_ip as _detect_lan_ip, resolve_user, web_url as _web_url

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _render_doctor_table(checks: list, title: str) -> "Table":
    from rich.table import Table
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("Status", style="bold", width=6)
    table.add_column("Check", style="dim", width=20)
    table.add_column("Blocking", width=8)
    table.add_column("Message")
    for check in checks:
        status_style = {
            "ok": "[green]ok[/green]",
            "warn": "[yellow]warn[/yellow]",
            "fail": "[red]fail[/red]",
        }.get(check.status, check.status)
        table.add_row(status_style, check.name, "yes" if check.blocking else "no", check.message)
    return table


def _resolve_admin_user(state: State, explicit: str | None = None) -> str:
    user = resolve_user(state, explicit=explicit, require=True)
    if user:
        return user
    console.print("[red]Admin user is required; pass --admin-user or record admin_user in state.[/red]")
    raise click.Abort()


def _run_steps(state: State, repo_dir: Path) -> bool:
    """Execute setup steps in order. Return True if all pass."""
    all_steps = STEP_MODULES + [("verify", "rakkib.steps.verify")]
    verify_cache: dict[str, VerificationResult] = {}

    for step_name, module_path in all_steps:
        if step_name == "caddy" and not caddy_enabled(state):
            console.print("[dim]Skipping caddy — exposure mode is internal.[/dim]")
            continue
        if step_name == "cloudflare" and not cloudflare_enabled(state):
            console.print("[dim]Skipping cloudflare — exposure mode is internal.[/dim]")
            continue
        console.print(f"[bold green]Step {step_name}[/bold green]")
        try:
            module = __import__(module_path, fromlist=["run", "verify"])
            run_fn = getattr(module, "run", None)
            verify_fn = getattr(module, "verify", None)

            if run_fn is None:
                console.print(f"[yellow]  Step {step_name} module has no run() — skipping[/yellow]")
                continue

            if step_name == "verify":
                # Pass cached results so verify.run() can skip re-running each step verify.
                state.set("_step_verify_cache", {k: {"ok": v.ok, "step": v.step, "message": v.message} for k, v in verify_cache.items()})

            run_fn(state)

            if step_name == "verify":
                # verify.run() already ran _collect_verifications and printed the summary;
                # calling verify_fn again would triple-run each step's verify().
                break

            if verify_fn is not None:
                result = verify_fn(state)
                verify_cache[step_name] = result
                if not result.ok:
                    console.print(f"[bold red]  Step {step_name} verify failed:[/bold red] {result.message}")
                    if result.log_path:
                        console.print(f"[dim]  Log: {result.log_path}[/dim]")
                    return False
                console.print(f"[dim]  Step {step_name} verify passed[/dim]")
            else:
                console.print(f"[dim]  Step {step_name} has no verify() — skipping check[/dim]")

        except Exception as exc:
            console.print(f"[bold red]  Step {step_name} failed:[/bold red] {exc}")
            return False

    console.print("[bold green]All steps completed successfully.[/bold green]")
    _print_deployed_urls(state)
    return True


def _run_pre_service_steps(state: State) -> bool:
    """Run setup steps needed before deploying one selected service."""
    for step_name, module_path in STEP_MODULES:
        if step_name == "services":
            break
        if step_name == "caddy" and not caddy_enabled(state):
            console.print("[dim]Skipping caddy — exposure mode is internal.[/dim]")
            continue
        if step_name == "cloudflare" and not cloudflare_enabled(state):
            console.print("[dim]Skipping cloudflare — exposure mode is internal.[/dim]")
            continue

        console.print(f"[bold green]Step {step_name}[/bold green]")
        try:
            module = __import__(module_path, fromlist=["run", "verify"])
            run_fn = getattr(module, "run", None)
            verify_fn = getattr(module, "verify", None)
            if run_fn is not None:
                run_fn(state)
            if verify_fn is not None:
                result = verify_fn(state)
                if not result.ok:
                    console.print(f"[bold red]  Step {step_name} verify failed:[/bold red] {result.message}")
                    return False
                console.print(f"[dim]  Step {step_name} verify passed[/dim]")
        except Exception as exc:
            console.print(f"[bold red]  Step {step_name} failed:[/bold red] {exc}")
            return False

    return True


def _select_service_for_deploy(state: State, registry: dict[str, Any], service: str) -> dict[str, Any] | None:
    by_id = {svc["id"]: svc for svc in registry["services"]}
    svc = by_id.get(service)
    if svc is None:
        console.print(f"[bold red]Error:[/bold red] Unknown service '{service}'.")
        return None
    if svc.get("state_bucket") == "always":
        console.print(f"[bold red]Error:[/bold red] '{service}' is an always-installed service; use full `rakkib pull`.")
        return None

    selected_ids = _installed_service_ids(state)
    selected_ids.add(service)
    dependency_errors = _validate_service_dependencies(selected_ids, registry)
    if dependency_errors:
        console.print("[bold red]Error:[/bold red] Invalid service selection:")
        for error in dependency_errors:
            console.print(f"  - {error}")
        return None

    _apply_service_selection(state, registry, selected_ids)
    services_step._generate_missing_secrets(state)
    return svc


def _run_service_pull(state: State, state_path: Path, service: str) -> bool:
    registry = services_step._load_registry()
    svc = _select_service_for_deploy(state, registry, service)
    if svc is None:
        return False

    state.save(state_path)
    if not _run_pre_service_steps(state):
        return False

    console.print(f"[bold green]Step services:{service}[/bold green]")
    try:
        services_step.run_single_service(state, service)
    except Exception as exc:
        console.print(f"[bold red]  Service {service} failed:[/bold red] {exc}")
        return False

    _persist_deployed_selection(state)
    state.save(state_path)
    _print_deployed_urls(state, [service])
    console.print(f"[bold green]Service {service} deployed successfully.[/bold green]")
    return True


def _sync_services_to_state_selection(state: State, state_path: Path) -> bool:
    registry = services_step._load_registry()
    desired_foundation, desired_selected = _selected_service_lists(state)
    desired_ids = set(desired_foundation)
    desired_ids.update(desired_selected)

    previous_foundation, previous_selected = _deployed_service_lists(state)
    previous_ids = set(previous_foundation)
    previous_ids.update(previous_selected)

    dependency_errors = _validate_service_dependencies(desired_ids, registry)
    if dependency_errors:
        console.print("[bold red]Error:[/bold red] Invalid service selection:")
        for error in dependency_errors:
            console.print(f"  - {error}")
        return False

    with progress_spinner("Applying service changes..."):
        previous_state = State({
            "foundation_services": previous_foundation,
            "selected_services": previous_selected,
        })
        removal_order = [
            svc["id"]
            for svc in reversed(selected_service_defs(previous_state, registry))
            if svc["id"] in (previous_ids - desired_ids)
        ]
        for svc_id in removal_order:
            services_step.remove_single_service(state, svc_id)

        _apply_service_selection(state, registry, desired_ids)
        services_step._generate_missing_secrets(state)
        postgres_step.run(state)

        added = sorted(desired_ids - previous_ids)
        if added:
            for svc_id in added:
                services_step.run_single_service(state, svc_id)
        else:
            data_root = state.data_root
            if caddy_enabled(state):
                services_step._reload_caddy(data_root)
            services_step.sync_shared_artifacts(
                state, services_step._repo_dir(), data_root, registry
            )

    _persist_deployed_selection(state)
    state.save(state_path)
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version=__import__("rakkib").__version__, prog_name="rakkib")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Rakkib — personal server installer."""
    ctx.ensure_object(dict)
    if "repo_dir" not in ctx.obj:
        ctx.obj["repo_dir"] = Path(__file__).resolve().parent


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Gather configuration via interview and save to .fss-state.yaml.

    Run `rakkib pull` afterwards to install everything.
    """
    console.print("[bold green]Rakkib init[/bold green]")

    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    state = run_interview(state, questions_dir=repo_dir / "data" / "questions")
    state.save(state_path)
    console.print("[bold green]Interview complete. State saved to .fss-state.yaml[/bold green]")

    if state.is_confirmed():
        console.print("[dim]Run [bold]rakkib pull[/bold] to install.[/dim]")
    else:
        console.print("[yellow]State is not confirmed — run `rakkib init` again to complete the interview.[/yellow]")


@cli.command()
@click.option("--service", "service", help="Deploy only one registry service and skip the full services pass.")
@click.pass_context
def pull(ctx: click.Context, service: str | None) -> None:
    """Install prerequisites and run all setup steps.

    Requires a confirmed state from `rakkib init`.
    """
    console.print("[bold green]Rakkib pull[/bold green]")

    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    if not state.is_confirmed():
        console.print(
            "[bold red]State is not confirmed.[/bold red] "
            "Run [bold]rakkib init[/bold] first."
        )
        return

    if not ensure_prereqs(state, console=console, cloudflared_bin=_cloudflared_bin()):
        return

    if service:
        ok = _run_service_pull(state, state_path, service)
    else:
        ok = _run_steps(state, repo_dir)
    if not ok:
        ctx.exit(1)

    if not service:
        _persist_deployed_selection(state)
        state.save(state_path)


@cli.command()
@click.pass_context
def update(ctx: click.Context) -> None:
    """Pull the latest installed CLI code from origin/runtime."""
    repo_dir = _checkout_dir(ctx.obj["repo_dir"])
    if not (repo_dir / ".git").exists():
        console.print(
            f"[bold red]Error:[/bold red] {repo_dir} is not a git checkout. "
            "Reinstall Rakkib with `bash install.sh` or the curl installer first."
        )
        ctx.exit(1)

    console.print("[bold green]Rakkib update[/bold green]")
    commands = [
        ["git", "fetch", "origin", "runtime"],
        ["git", "rev-parse", "--verify", "runtime"],
    ]

    try:
        for command in commands:
            result = subprocess.run(command, cwd=repo_dir, capture_output=True, text=True)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode,
                    command,
                    output=result.stdout,
                    stderr=result.stderr,
                )

        branch_exists = True
    except subprocess.CalledProcessError as exc:
        if exc.cmd == ["git", "rev-parse", "--verify", "runtime"]:
            branch_exists = False
        else:
            detail = (exc.stderr or exc.output or "unknown git error").strip()
            console.print(f"[bold red]Update failed:[/bold red] {detail}")
            console.print("[yellow]Local checkout changes may need to be resolved manually before updating.[/yellow]")
            ctx.exit(1)

    switch_command = ["git", "switch", "runtime"] if branch_exists else ["git", "switch", "-c", "runtime", "origin/runtime"]
    pull_command = ["git", "pull", "--ff-only", "origin", "runtime"]

    try:
        for command in (switch_command, pull_command):
            result = subprocess.run(command, cwd=repo_dir, capture_output=True, text=True)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode,
                    command,
                    output=result.stdout,
                    stderr=result.stderr,
                )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.output or "unknown git error").strip()
        console.print(f"[bold red]Update failed:[/bold red] {detail}")
        console.print("[yellow]Local checkout changes may need to be resolved manually before updating.[/yellow]")
        ctx.exit(1)

    console.print("[green]Updated to the latest origin/runtime code.[/green]")


@cli.command()
@click.option("--json", "json_output", is_flag=True, help="Emit JSON output")
@click.option("--interactive", is_flag=True, help="Interactive mode with auto-fix prompts")
@click.pass_context
def doctor(ctx: click.Context, json_output: bool, interactive: bool) -> None:
    """Run host diagnostics."""
    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    checks = run_checks(state)

    if json_output:
        click.echo(to_json(checks))
    else:
        if interactive:
            from rich.panel import Panel

            console.print(_render_doctor_table(checks, "Rakkib Doctor"))

            # Interactive fixes for blocking failures
            for check in checks:
                if check.blocking and check.status == "fail":
                    console.print(
                        Panel(
                            f"[bold red]{check.name}[/bold red]: {check.message}",
                            title="Blocking Failure",
                        )
                    )
                    fix_result = None
                    if check.name == "docker":
                        answer = click.prompt("Attempt to fix docker?", type=click.Choice(["y", "n"]), default="n", show_default=False)
                        if answer == "y":
                            fix_result = attempt_fix_docker()
                    elif check.name == "cloudflared_cli":
                        answer = click.prompt("Attempt to fix cloudflared?", type=click.Choice(["y", "n"]), default="n", show_default=False)
                        if answer == "y":
                            fix_result = attempt_fix_cloudflared()
                    elif check.name == "public_ports":
                        owners = process_owners_for_ports()
                        console.print("[bold yellow]Port ownership:[/bold yellow]")
                        for port, info in owners.items():
                            console.print(f"  {port}: {info}")
                    else:
                        console.print(f"[dim]No auto-fix available for {check.name}.[/dim]")

                    if fix_result:
                        console.print(f"[bold cyan]Fix result:[/bold cyan] {fix_result}")

            # Re-run checks after fixes
            console.print("\n[bold green]Re-running checks...[/bold green]")
            checks = run_checks(state)
            console.print(_render_doctor_table(checks, "Updated Results"))
        else:
            for check in checks:
                click.echo(f"[{check.status}] {check.name}: {check.message}")
            click.echo(summary_text(checks))

    fail_count = sum(1 for c in checks if c.status == "fail")
    if fail_count > 0:
        ctx.exit(1)


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Print deployment status and resume point."""
    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    if not state.is_confirmed():
        console.print(
            "[yellow]No confirmed deployment state found. Run `rakkib init` to start.[/yellow]"
        )
        return

    domain = state.get("domain", "") or ""
    data_root = state.get("data_root", "/srv") or "/srv"

    console.print(f"\n[bold]Domain:[/bold] [cyan]{domain or '—'}[/cyan]")

    # System checks
    console.rule("[bold]System[/bold]")
    _icons = {"ok": "[green]✓[/green]", "warn": "[yellow]⚠[/yellow]", "fail": "[red]✗[/red]"}
    _colors = {"ok": "green", "warn": "yellow", "fail": "red"}
    for chk in (check_ram(), check_disk(data_root)):
        icon = _icons.get(chk.status, "?")
        color = _colors.get(chk.status, "white")
        console.print(f"  {icon}  [{color}]{chk.name.upper()}[/{color}]  {chk.message}")

    # Installed services
    console.rule("[bold]Installed Services[/bold]")
    registry = services_step._load_registry()
    foundation_ids = set(state.get("foundation_services", []) or [])
    selected_ids = set(state.get("selected_services", []) or [])
    installed_ids = foundation_ids | selected_ids
    urls = {row["service"]: row["url"] for row in deployed_service_urls(state, registry, installed_ids)}

    for svc in registry["services"]:
        svc_id = svc["id"]
        bucket = svc.get("state_bucket", "")
        if svc_id == "caddy" and not caddy_enabled(state):
            continue
        if svc_id == "cloudflared" and not cloudflare_enabled(state):
            continue
        if bucket != "always" and svc_id not in installed_ids:
            continue
        if svc_id in urls:
            console.print(f"  [cyan]{svc_id}[/cyan]  {urls[svc_id]}")
        else:
            console.print(f"  [cyan]{svc_id}[/cyan]")

    # Available services
    console.rule("[bold]Available Services[/bold]")
    available = [
        svc for svc in registry["services"]
        if svc.get("state_bucket") in ("foundation_services", "selected_services")
        and svc["id"] not in installed_ids
    ]
    if available:
        for svc in available:
            console.print(f"  [dim]{svc['id']}[/dim]")
    else:
        console.print("  [dim]All available services are installed.[/dim]")
    console.print()


@cli.command()
@click.option("--yes", is_flag=True, help="Apply service changes without the confirmation prompt.")
@click.option("--service", "service_option", help="Add one registry service without the checkbox prompt.")
@click.argument("service", required=False)
@click.pass_context
def add(ctx: click.Context, service: str | None, service_option: str | None, yes: bool) -> None:
    """Sync deployed services against the registry."""
    console.print("[bold green]Rakkib add[/bold green]")

    if service and service_option and service != service_option:
        console.print(
            "[bold red]Error:[/bold red] Provide the service either as an argument "
            "or with --service, not both."
        )
        sys.exit(1)
    service = service_option or service

    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    registry = services_step._load_registry()
    old_selected = set(state.get("foundation_services", []) or [])
    old_selected.update(state.get("selected_services", []) or [])

    if service:
        by_id = {svc["id"]: svc for svc in registry["services"]}
        if service not in by_id:
            console.print(f"[bold red]Error:[/bold red] Unknown service '{service}'.")
            sys.exit(1)
        selected_ids = set(old_selected)
        if by_id[service].get("state_bucket") != "always":
            selected_ids.add(service)
    else:
        selected = prompt_checkbox(
            "Select services to keep installed:",
            choices=_build_add_choices(state, registry),
        )
        selected_ids = set(selected)

    dependency_errors = _validate_service_dependencies(selected_ids, registry)
    if dependency_errors:
        console.print("[bold red]Error:[/bold red] Invalid service selection:")
        for error in dependency_errors:
            console.print(f"  - {error}")
        sys.exit(1)

    added = sorted(selected_ids - old_selected)
    removed = sorted(old_selected - selected_ids)
    planned_subdomains: dict[str, str] | None = None

    if added and not yes:
        try:
            planned_state = State(state.to_dict())
            _apply_service_selection(planned_state, registry, selected_ids)
            _prompt_service_subdomains(planned_state, registry, set(added))
            planned_subdomains = dict(planned_state.get("subdomains", {}) or {})
        except ValueError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

    if added or removed:
        _summarize_service_diff(added, removed)
        if not yes and not prompt_confirm("Apply these service changes?", default=False):
            console.print("[yellow]Aborted.[/yellow]")
            return
        if yes:
            console.print("[dim]Confirmation skipped because --yes was provided.[/dim]")
    else:
        console.print("[yellow]No selection changes; refreshing selected services.[/yellow]")

    with progress_spinner("Applying service changes..."):
        previous_state = State({
            "foundation_services": list(state.get("foundation_services", []) or []),
            "selected_services": list(state.get("selected_services", []) or []),
        })
        removal_order = [
            svc["id"]
            for svc in reversed(selected_service_defs(previous_state, registry))
            if svc["id"] in removed
        ]
        for svc_id in removal_order:
            services_step.remove_single_service(state, svc_id)

        _apply_service_selection(state, registry, selected_ids)
        if planned_subdomains is not None:
            _apply_planned_subdomains(state, registry, planned_subdomains)
        services_step._generate_missing_secrets(state)
        state.save(state_path)

        postgres_step.run(state)
        if service:
            services_step.run_single_service(state, service)
        elif added:
            for svc_id in added:
                services_step.run_single_service(state, svc_id)
        else:
            # Removals-only or no changes — reload caddy to apply route changes and sync
            data_root = state.data_root
            if caddy_enabled(state):
                services_step._reload_caddy(data_root)
            services_step.sync_shared_artifacts(
                state, services_step._repo_dir(), data_root, services_step._load_registry()
            )
        _persist_deployed_selection(state)
        state.save(state_path)

    console.print("[bold green]Service selection synced successfully.[/bold green]")
    deployed_ids: list[str] | None = None
    if service:
        deployed_ids = [service]
    elif added:
        deployed_ids = list(added)
    if deployed_ids:
        _print_deployed_urls(state, deployed_ids)


@cli.command(name="sync-services")
@click.pass_context
def sync_services(ctx: click.Context) -> None:
    """Apply the current saved service selection without re-running full setup."""
    console.print("[bold green]Rakkib sync-services[/bold green]")

    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    if not _sync_services_to_state_selection(state, state_path):
        ctx.exit(1)

    console.print("[bold green]Service selection synced successfully.[/bold green]")
    _print_deployed_urls(state)


@cli.command()
@click.argument("service")
@click.pass_context
def smoke(ctx: click.Context, service: str) -> None:
    """Fetch a deployed service URL and verify its registry smoke marker."""
    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    result = services_step.smoke_check(state, service)
    if result.ok:
        console.print(f"[green]✓[/green] {result.message}")
        return

    console.print(f"[bold red]✗[/bold red] {result.message}")
    ctx.exit(1)


@cli.command()
@click.argument("service")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def remove(ctx: click.Context, service: str, yes: bool) -> None:
    """Remove a single service (containers, rendered files, data dirs).

    This is a non-interactive alternative to deselecting a service via `rakkib add`.
    """
    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    registry = load_service_registry()
    by_id = {svc["id"]: svc for svc in registry["services"]}
    if service not in by_id:
        console.print(f"[bold red]Error:[/bold red] Unknown service '{service}'.")
        ctx.exit(1)
    if by_id[service].get("state_bucket") == "always":
        console.print(
            f"[bold red]Error:[/bold red] '{service}' is an always-installed service and cannot be removed."
        )
        ctx.exit(1)

    selected = set(state.get("selected_services", []) or [])
    foundation = set(state.get("foundation_services", []) or [])
    if service not in selected and service not in foundation:
        console.print(f"[yellow]{service} is not selected; attempting cleanup anyway.[/yellow]")

    if not yes and not prompt_confirm(f"Remove '{service}' and delete its data?", default=False):
        console.print("[yellow]Aborted.[/yellow]")
        return
    if yes:
        console.print("[dim]Confirmation skipped because --yes was provided.[/dim]")

    services_step.remove_single_service(state, service)

    # Update state selection so a later `rakkib pull` won't re-add it.
    if service in selected:
        selected.remove(service)
        state.set("selected_services", sorted(selected))
    if service in foundation:
        foundation.remove(service)
        state.set("foundation_services", sorted(foundation))
    _persist_deployed_selection(state)
    state.save(state_path)

    data_root = state.data_root
    services_step._reload_caddy(data_root)
    services_step.sync_shared_artifacts(state, services_step._repo_dir(), data_root, registry)

    console.print(f"[bold green]Removed {service}.[/bold green]")


@cli.command()
@click.argument("service", required=False)
@click.option("--all", "restart_all", is_flag=True, help="Restart all services in dependency order")
@click.pass_context
def restart(ctx: click.Context, service: str | None, restart_all: bool) -> None:
    """Restart one or all deployed services.

    \b
    rakkib restart caddy          # restart a single service
    rakkib restart --all          # restart all services in dependency order
    """
    if service and restart_all:
        console.print("[yellow]Use either a service name or --all, not both.[/yellow]")
        ctx.exit(1)

    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)

    if restart_all:
        console.print("[bold green]Restarting all services...[/bold green]")
        try:
            restarted = services_step.restart_all(state)
        except subprocess.CalledProcessError as exc:
            console.print(f"[bold red]Restart failed:[/bold red] {exc}")
            sys.exit(1)
        for svc_id in restarted:
            console.print(f"  [green]✓[/green] {svc_id}")
        console.print(f"[bold green]Done.[/bold green] {len(restarted)} service(s) restarted.")
    elif service:
        console.print(f"[bold green]Restarting {service}...[/bold green]")
        try:
            services_step.restart_service(state, service)
        except ValueError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)
        except subprocess.CalledProcessError as exc:
            console.print(f"[bold red]Restart failed:[/bold red] {exc}")
            sys.exit(1)
        console.print(f"[green]✓[/green] {service} restarted.")
    else:
        registry = load_service_registry()
        choices = _build_restart_choices(state, registry)
        if not choices:
            console.print("[yellow]No deployed services found to restart.[/yellow]")
            ctx.exit(1)

        selected = prompt_checkbox(
            "Select deployed services to restart:",
            choices=choices,
        )
        if not selected:
            console.print("[yellow]No services selected.[/yellow]")
            return

        restart_ids = _restart_order(registry, set(selected))
        console.print("[bold green]Restarting selected services...[/bold green]")
        for svc_id in restart_ids:
            try:
                services_step.restart_service(state, svc_id)
            except ValueError as exc:
                console.print(f"[bold red]Error:[/bold red] {exc}")
                sys.exit(1)
            except subprocess.CalledProcessError as exc:
                console.print(f"[bold red]Restart failed:[/bold red] {exc}")
                sys.exit(1)
            console.print(f"  [green]✓[/green] {svc_id}")
        console.print(f"[bold green]Done.[/bold green] {len(restart_ids)} service(s) restarted.")


@cli.command()
@click.confirmation_option(prompt="Remove the rakkib CLI shim and PATH entries?")
def uninstall() -> None:
    """Remove the user-scoped rakkib command shim and managed PATH blocks."""
    target = Path.home() / ".local" / "bin" / "rakkib"
    if target.is_symlink():
        target.unlink()
        console.print(f"[green]Removed rakkib CLI shim at {target}[/green]")
    elif target.exists():
        console.print(f"[yellow]{target} exists but is not a symlink; not removed[/yellow]")
    else:
        console.print(f"[yellow]No rakkib CLI shim found at {target}[/yellow]")

    marker = "# Added by Rakkib: user-local bin on PATH"
    profiles = [
        Path.home() / ".bashrc",
        Path.home() / ".zshrc",
        Path.home() / ".profile",
    ]
    removed_any = False
    for profile in profiles:
        if not profile.exists():
            continue
        content = profile.read_text()
        if marker not in content:
            continue
        lines = content.splitlines()
        new_lines: list[str] = []
        skipping = False
        for line in lines:
            if line == marker:
                skipping = True
                continue
            if skipping and line == "esac":
                skipping = False
                continue
            if skipping:
                continue
            new_lines.append(line)
        # Preserve single trailing newline
        profile.write_text("\n".join(new_lines).rstrip() + "\n")
        console.print(f"[green]Removed managed PATH block from {profile}[/green]")
        removed_any = True

    if not removed_any:
        console.print("[yellow]No managed PATH block found in shell profiles[/yellow]")

    console.print(
        "\n[bold]Rakkib CLI shim uninstall is complete.[/bold]\n"
        "If this terminal still resolves rakkib, refresh your shell command cache or open a new terminal:\n"
        "  hash -r"
    )


@cli.command()
@click.pass_context
def auth(ctx: click.Context) -> None:
    """Validate sudo and prepare Docker access when needed."""
    if os.geteuid() == 0:
        console.print("[green]Already running as root; no sudo validation needed.[/green]")
        return

    if shutil.which("sudo") is None:
        console.print("[red]sudo is required for privileged setup actions on Linux.[/red]")
        ctx.exit(1)

    console.print("[dim]Validating sudo for this terminal. Rakkib will not store your password.[/dim]")
    result = subprocess.run(["sudo", "-v"], capture_output=True, text=True)
    if result.returncode != 0:
        console.print("[red]Sudo validation failed. Run `sudo -v` in your terminal first.[/red]")
        ctx.exit(1)
    console.print("[green]Sudo is ready for this terminal according to your system sudo policy.[/green]")

    if shutil.which("docker") is None:
        return

    repo_dir = ctx.obj["repo_dir"]
    state_path = repo_dir / ".fss-state.yaml"
    state = State.load(state_path)
    user = docker_access_user(state)
    try:
        docker_run(["info"])
        console.print("[green]Docker is already usable by this shell.[/green]")
        return
    except DockerError as exc:
        if not is_docker_permission_error(exc.stderr or str(exc)):
            console.print(f"[yellow]Docker is installed but not usable yet:[/yellow] {exc}")
            return

    message = prepare_docker_access(user, validate_sudo=False)
    console.print(f"[dim]{message}[/dim]")
    if not message.startswith("Docker access was prepared"):
        console.print("[dim]Manual fallback:[/dim]")
        console.print(f"[dim]{docker_access_commands(user)}[/dim]")
        ctx.exit(1)
    console.print(
        "[green]Docker access is prepared.[/green] "
        "Open a new shell or run `newgrp docker`, then run `docker info` and `rakkib pull`."
    )


@cli.command()
@click.option("--lan", is_flag=True, help="Bind to 0.0.0.0 and print a LAN URL.")
@click.option("--host", default="127.0.0.1", show_default=True, help="Host interface to bind.")
@click.option("--port", default=8080, show_default=True, type=int, help="TCP port to bind.")
@click.option("--token", "startup_token", default="", help="Explicit setup token to require.")
@click.option("--no-token", is_flag=True, help="Disable token auth for this web session.")
@click.option("--no-open", is_flag=True, help="Do not attempt to open a browser automatically.")
@click.pass_context
def web(ctx: click.Context, lan: bool, host: str, port: int, startup_token: str, no_token: bool, no_open: bool) -> None:
    """Run the local browser UI and token bootstrap server."""
    import uvicorn

    from rakkib.web import WebRuntimeConfig, create_app

    bind_host = host
    if lan and host == "127.0.0.1":
        bind_host = "0.0.0.0"

    if no_token and startup_token:
        console.print("[bold red]Error:[/bold red] Use either --token or --no-token, not both.")
        raise click.Abort()

    token_auth_enabled = not no_token
    if token_auth_enabled:
        startup_token = startup_token or token_urlsafe(24)
    else:
        startup_token = ""

    config = WebRuntimeConfig(
        host=bind_host,
        port=port,
        repo_dir=ctx.obj["repo_dir"],
        token_auth_enabled=token_auth_enabled,
        startup_token=startup_token or None,
    )
    app = create_app(config)

    local_url = _web_url("127.0.0.1" if bind_host == "0.0.0.0" else bind_host, port, startup_token or None)
    lan_ip = _detect_lan_ip() if bind_host == "0.0.0.0" else None
    lan_url = _web_url(lan_ip, port, startup_token or None) if lan_ip else None

    console.print("[bold green]Rakkib web[/bold green]")
    console.print(f"[dim]Bind:[/dim] {bind_host}:{port}")
    console.print(f"[dim]Local:[/dim] {local_url}")
    if lan_url:
        console.print(f"[dim]LAN:[/dim] {lan_url}")
    elif lan and not lan_ip:
        console.print("[yellow]LAN mode is enabled, but the primary LAN IP could not be detected automatically.[/yellow]")

    if token_auth_enabled:
        console.print("[dim]Token auth:[/dim] required")
    else:
        console.print("[yellow]Token auth is disabled because --no-token was provided explicitly.[/yellow]")

    qr_url = lan_url or local_url
    console.print(f"\n[dim]Scan to open:[/dim] {qr_url}\n")
    _show_qr(qr_url)

    if not no_open:
        try:
            webbrowser.open(local_url)
        except Exception:
            console.print("[dim]Browser auto-open was skipped because no local browser handler was available.[/dim]")

    uvicorn.run(app, host=bind_host, port=port, log_level="info")


@cli.group()
@click.pass_context
def privileged(ctx: click.Context) -> None:
    """Root-only helper actions."""
    if os.geteuid() != 0:
        console.print("[bold red]Error:[/bold red] This helper must be run with sudo or from a root shell.")
        ctx.exit(1)


@privileged.command(name="check")
def privileged_check() -> None:
    """Verify the helper is running as root."""
    console.print("[green]Privileged helper is running as root.[/green]")


@privileged.command(name="ensure-layout")
@click.option("--state", "state_path", type=click.Path(path_type=Path), default=".fss-state.yaml")
@click.option("--data-root", type=str, default="")
@click.option("--admin-user", type=str, default="")
@click.pass_context
def privileged_ensure_layout(
    ctx: click.Context, state_path: Path, data_root: str, admin_user: str
) -> None:
    """Create the base Rakkib data directories."""
    state = State.load(state_path)
    if not data_root:
        data_root = str(state.data_root)
    user = _resolve_admin_user(state, admin_user)

    console.print(f"[bold green]Creating Rakkib layout under {data_root}[/bold green]")
    root = Path(data_root)
    # These dirs are admin-owned by design; recurse into them safely.
    admin_dirs = [
        root / "docker",
        root / "apps" / "static",
        root / "backups",
        root / "MDs",
        root / "logs",
    ]
    # These dirs must be created but NOT recursed — data/ contains service-managed UIDs.
    top_only = [root, root / "apps", root / "data"]

    for p in admin_dirs + top_only:
        p.mkdir(parents=True, exist_ok=True)

    for p in top_only:
        shutil.chown(p, user=user, group=None)

    for p in admin_dirs:
        shutil.chown(p, user=user, group=None)
        for dirpath, dirs, files in os.walk(p):
            for d in dirs:
                shutil.chown(os.path.join(dirpath, d), user=user, group=None)
            for f in files:
                shutil.chown(os.path.join(dirpath, f), user=user, group=None)

    console.print(f"[green]Layout created and owned by {user}.[/green]")


@privileged.command(name="fix-repo-owner")
@click.option("--state", "state_path", type=click.Path(path_type=Path), default=".fss-state.yaml")
@click.option("--admin-user", type=str, default="")
@click.option("--repo-dir", type=click.Path(path_type=Path), default="")
@click.pass_context
def privileged_fix_repo_owner(
    ctx: click.Context, state_path: Path, admin_user: str, repo_dir: Path
) -> None:
    """Assign the repo back to the admin user."""
    state = State.load(state_path)
    user = _resolve_admin_user(state, admin_user)
    if not repo_dir:
        repo_dir = ctx.obj["repo_dir"]
    if not repo_dir.exists():
        console.print(f"[red]Repo directory does not exist: {repo_dir}[/red]")
        ctx.exit(1)

    console.print(f"[bold green]Assigning {repo_dir} to {user}[/bold green]")
    for root, dirs, files in os.walk(repo_dir):
        for d in dirs:
            shutil.chown(os.path.join(root, d), user=user, group=None)
        for f in files:
            shutil.chown(os.path.join(root, f), user=user, group=None)
    shutil.chown(repo_dir, user=user, group=None)
    console.print(f"[green]Repo ownership updated to {user}.[/green]")
if __name__ == "__main__":
    cli()
