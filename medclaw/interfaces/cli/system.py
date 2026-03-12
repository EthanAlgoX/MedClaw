"""System inspection and configuration CLI."""

from __future__ import annotations

from pathlib import Path

import typer

from medclaw.application import build_provider_list_response, build_provider_response, build_workspace_response
from medclaw.config.loader import ensure_workspace, load_config, save_config
from medclaw.config.schema import ProviderConfig
from medclaw.interfaces.cli.common import (
    build_config_response_model,
    build_provider_summaries,
    build_workspace_summary_model,
    choose_replacement_default,
    console,
    emit_config_response,
    ensure_model_compatible_with_provider,
    ensure_provider_has_api_key,
    ensure_runtime_supported_provider,
    ensure_supported_provider_name,
    load_provider_config,
    load_provider_summary,
    normalize_default_model_for_provider,
    write_json,
)

system_app = typer.Typer(help="System inspection and configuration")


@system_app.command("workspace")
def system_workspace(
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Show workspace paths and layout."""
    workspace_summary = build_workspace_summary_model()
    if as_json:
        write_json(build_workspace_response(workspace_summary))
        return

    console.print("[bold]Workspace:[/bold]")
    console.print(f"path: {workspace_summary.path}")
    console.print(f"exists: {workspace_summary.exists}")
    console.print(f"skills: {workspace_summary.skills_path}")
    console.print(f"memory: {workspace_summary.memory_path}")
    console.print(f"reports: {workspace_summary.reports_path}")
    console.print(f"research: {workspace_summary.research_path}")
    console.print(f"collections: {workspace_summary.collections_path}")


@system_app.command("providers")
def system_providers(
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Show configured providers and default selection."""
    config = load_config()
    providers = build_provider_summaries(config)
    if as_json:
        write_json(build_provider_list_response(providers, default_provider=config.agents.defaults.provider))
        return

    console.print("[bold]Providers:[/bold]")
    for provider in providers:
        status = "configured" if provider.configured else "not-configured"
        suffix = " default" if provider.is_default else ""
        console.print(f"  - {provider.name}: {status}{suffix}")
        console.print(f"      api key: {'set' if provider.has_api_key else 'missing'}")
        if provider.base_url:
            console.print(f"      base url: {provider.base_url}")
        if provider.organization:
            console.print(f"      organization: {provider.organization}")


@system_app.command("config")
def system_config(
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Show configuration summary."""
    config = load_config()
    response = build_config_response_model(config)
    if as_json:
        write_json(response)
        return

    console.print("[bold]Config:[/bold]")
    console.print(f"config path: {response.item.config_path}")
    console.print(f"default provider: {response.item.default_provider}")
    console.print(f"default model: {response.item.default_model}")
    console.print(f"temperature: {response.item.temperature}")
    console.print(f"max tokens: {response.item.max_tokens}")
    console.print(f"workspace: {response.item.workspace.path}")


@system_app.command("model-set")
def system_model_set(
    model: str,
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Update the default model."""
    config = load_config()
    ensure_model_compatible_with_provider(config.agents.defaults.provider, model)
    config.agents.defaults.model = model
    save_config(config)
    emit_config_response(config, as_json=as_json)


@system_app.command("temperature-set")
def system_temperature_set(
    temperature: float,
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Update the default sampling temperature."""
    if temperature < 0 or temperature > 2:
        console.print("[red]Error:[/red] Temperature must be between 0 and 2.")
        raise typer.Exit(1)

    config = load_config()
    config.agents.defaults.temperature = temperature
    save_config(config)
    emit_config_response(config, as_json=as_json)


@system_app.command("max-tokens-set")
def system_max_tokens_set(
    max_tokens: int,
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Update the default max tokens."""
    if max_tokens <= 0:
        console.print("[red]Error:[/red] Max tokens must be greater than 0.")
        raise typer.Exit(1)

    config = load_config()
    config.agents.defaults.maxTokens = max_tokens
    save_config(config)
    emit_config_response(config, as_json=as_json)


@system_app.command("workspace-set")
def system_workspace_set(
    path: Path,
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Update the configured workspace path."""
    workspace_path = path.expanduser()
    config = load_config()
    config.workspace.path = workspace_path
    save_config(config)
    ensure_workspace(workspace_path)
    emit_config_response(config, as_json=as_json)


@system_app.command("provider-show")
def system_provider_show(
    name: str,
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Show one provider configuration."""
    provider = load_provider_summary(load_config(), name)
    if as_json:
        write_json(build_provider_response(provider))
        return

    status = "configured" if provider.configured else "not-configured"
    suffix = " default" if provider.is_default else ""
    console.print(f"[bold]Provider:[/bold] {provider.name}")
    console.print(f"status: {status}{suffix}")
    console.print(f"api key: {'set' if provider.has_api_key else 'missing'}")
    if provider.base_url:
        console.print(f"base url: {provider.base_url}")
    if provider.organization:
        console.print(f"organization: {provider.organization}")


@system_app.command("provider-set")
def system_provider_set(
    name: str,
    api_key: str | None = typer.Option(None, "--api-key", help="Provider API key."),
    base_url: str | None = typer.Option(None, "--base-url", help="Provider base URL."),
    organization: str | None = typer.Option(None, "--organization", help="Provider organization."),
    make_default: bool = typer.Option(False, "--default", help="Make this the default provider."),
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Create or update one provider configuration."""
    ensure_supported_provider_name(name)

    config = load_config()
    current = getattr(config.providers, name, None) or ProviderConfig()
    updated = ProviderConfig(
        apiKey=api_key if api_key is not None else current.apiKey,
        baseUrl=base_url if base_url is not None else current.baseUrl,
        organization=organization if organization is not None else current.organization,
    )
    setattr(config.providers, name, updated)
    if make_default:
        ensure_runtime_supported_provider(name)
        ensure_provider_has_api_key(name, updated)
        config.agents.defaults.provider = name
        normalize_default_model_for_provider(config, name)
    save_config(config)

    provider = load_provider_summary(config, name)
    if as_json:
        write_json(build_provider_response(provider))
        return

    console.print(f"[green]Updated provider:[/green] {provider.name}")
    console.print(f"default: {provider.is_default}")
    console.print(f"api key: {'set' if provider.has_api_key else 'missing'}")
    if provider.base_url:
        console.print(f"base url: {provider.base_url}")
    if provider.organization:
        console.print(f"organization: {provider.organization}")


@system_app.command("provider-default")
def system_provider_default(
    name: str,
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Make a configured provider the default selection."""
    config = load_config()
    provider_config = load_provider_config(config, name)
    ensure_runtime_supported_provider(name)
    ensure_provider_has_api_key(name, provider_config)
    config.agents.defaults.provider = name
    reset_model = normalize_default_model_for_provider(config, name)
    save_config(config)

    provider = load_provider_summary(config, name)
    if as_json:
        write_json(build_provider_response(provider))
        return

    console.print(f"[green]Default provider set:[/green] {provider.name}")
    console.print(f"api key: {'set' if provider.has_api_key else 'missing'}")
    if reset_model is not None:
        console.print(f"model reset to: {reset_model}")


@system_app.command("provider-unset")
def system_provider_unset(
    name: str,
    as_json: bool = typer.Option(False, "--json", help="Output structured JSON."),
):
    """Remove one provider configuration."""
    config = load_config()
    ensure_supported_provider_name(name)
    current_default = config.agents.defaults.provider
    replacement_default = choose_replacement_default(config, removed_provider=name)
    if current_default == name and replacement_default is None:
        console.print(
            f"[red]Error:[/red] Cannot unset default provider '{name}' without another configured provider with an API key."
        )
        raise typer.Exit(1)

    setattr(config.providers, name, None)
    if current_default == name and replacement_default is not None:
        config.agents.defaults.provider = replacement_default
    save_config(config)

    provider = load_provider_summary(config, name)
    if as_json:
        write_json(build_provider_response(provider))
        return

    console.print(f"[green]Removed provider:[/green] {name}")
    if current_default == name and replacement_default is not None:
        console.print(f"default switched to: {replacement_default}")
