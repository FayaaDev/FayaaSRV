"""Tests for schema parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from rakkib.schema import FieldDef, QuestionSchema, load_all_schemas

QUESTIONS_DIR = Path(__file__).resolve().parent.parent / "src" / "rakkib" / "data" / "questions"


def test_load_all_schemas_finds_all_six():
    schemas = load_all_schemas(QUESTIONS_DIR)
    phases = [s.phase for s in schemas]
    assert phases == [1, 2, 3, 4, 5, 6]


def test_phase_1_platform_field():
    schema = QuestionSchema.from_file(QUESTIONS_DIR / "01-platform.md")
    assert schema.phase == 1
    assert schema.schema_version == 1

    field_map = {f.id: f for f in schema.fields}

    # Derived host field: arch
    arch = field_map["arch"]
    assert arch.type == "derived"
    assert arch.source == "host"
    assert arch.detect["command"] == "uname -m"
    assert arch.detect["normalize"]["x86_64"] == "amd64"
    assert arch.records == ["arch"]

    # Platform is detected by the interview/web runtime, not prompted.
    platform = field_map["platform"]
    assert platform.type == "derived"
    assert platform.source == "host"
    assert platform.records == ["platform"]

    # Docker confirm
    docker = field_map["docker_installed"]
    assert docker.type == "confirm"
    assert docker.prompt == "Is Docker already installed and running on this machine? [Y/n]"
    assert docker.default is True
    assert docker.accepted_inputs["y"] is True
    assert docker.accepted_inputs["n"] is False

    # Host gateway derived
    gw = field_map["host_gateway"]
    assert gw.type == "derived"
    assert gw.value["linux"] == "172.18.0.1"
    assert gw.value["mac"] == "host.docker.internal"


def test_phase_2_identity_fields():
    schema = QuestionSchema.from_file(QUESTIONS_DIR / "02-identity.md")
    assert schema.phase == 2

    field_map = {f.id: f for f in schema.fields}

    server_name = field_map["server_name"]
    assert server_name.type == "text"
    assert server_name.validate["pattern"] == r"^[a-z0-9-]+$"
    assert server_name.validate["message"] == "Use lowercase letters, numbers, and hyphens only."

    domain = field_map["domain"]
    assert domain.type == "text"
    assert domain.when == "exposure_mode == cloudflare"
    assert domain.validate["pattern"] == r"^(?!https?://).+\..+$"

    exposure = field_map["exposure_mode"]
    assert exposure.type == "single_select"
    assert exposure.canonical_values == ["internal", "cloudflare"]

    internal_domain = field_map["internal_domain"]
    assert internal_domain.type == "derived"
    assert internal_domain.when == "exposure_mode == internal"
    assert internal_domain.value == "localhost"

    zone = field_map["zone_in_cloudflare"]
    assert zone.when == "exposure_mode == cloudflare"

    admin_user = field_map["admin_user"]
    assert admin_user.type == "derived"
    assert admin_user.detect["linux"][0] == "python3"

    lan_ip = field_map["lan_ip"]
    assert lan_ip.type == "derived"
    assert lan_ip.source == "host"
    assert lan_ip.detect["linux"] == "hostname -I"
    assert lan_ip.normalize == "first_non_loopback_ipv4"

    data_root = field_map["data_root"]
    assert data_root.derive_from == "platform"
    assert data_root.value["linux"] == "/srv"

    backup_dir = field_map["backup_dir"]
    assert backup_dir.template == "{{data_root}}/backups"
    assert backup_dir.derive_from == "data_root"


def test_phase_3_service_catalog_and_rules():
    schema = QuestionSchema.from_file(QUESTIONS_DIR / "03-services.md")
    assert schema.phase == 3

    assert "foundation_bundle" in schema.service_catalog
    assert len(schema.service_catalog["foundation_bundle"]) == 4
    assert schema.service_catalog["foundation_bundle"][0]["slug"] == "nocodb"
    assert [item["slug"] for item in schema.service_catalog["optional_services"]] == [
        "n8n",
        "immich",
        "transfer",
        "jellyfin",
        "plex",
        "openclaw",
        "hermes-agent",
        "claude",
        "codex",
        "anse",
        "filebrowser",
        "webdav",
        "pingvin-share",
        "it-tools",
        "cyberchef",
        "drawio",
        "excalidraw",
        "homer",
        "dozzle",
        "grafana",
        "homarr",
        "glance",
        "dashy",
        "beszel",
        "glances",
        "freshrss",
        "openbooks",
        "actual-budget",
        "wallos",
        "rsshub",
        "vaultwarden",
        "adguard",
        "gladys-assistant",
        "whoogle",
        "forgejo",
        "privatebin",
        "stirling-pdf",
        "mealie",
        "dailytxt",
        "esphome",
        "notemark",
        "memos",
        "gitea",
        "whoami",
        "pairdrop",
        "moodist",
        "cheshire-cat-ai",
        "flowise",
        "serge",
        "chatpad",
        "lobe-chat",
        "open-webui",
        "ollama-cpu",
        "ollama-amd",
        "ollama-nvidia",
        "autoheal",
        "watchtower",
        "matter-server",
    ]

    assert schema.rules == []

    field_map = {f.id: f for f in schema.fields}
    foundation = field_map["foundation_services"]
    assert foundation.type == "multi_select"
    assert foundation.selection_mode == "deselect_from_default"
    assert foundation.numeric_aliases["1"] == "nocodb"

    optional = field_map["optional_services"]
    assert optional.type == "multi_select"
    assert optional.selection_mode == "add_to_empty"
    assert optional.records == ["selected_services"]
    assert optional.numeric_aliases["10"] == "openclaw"
    assert optional.numeric_aliases["16"] == "excalidraw"

    subdomain = field_map["service_subdomain"]
    assert subdomain.type == "text"
    assert subdomain.repeat_for == "selected_service_slugs"


def test_phase_4_cloudflare_execution_paths():
    schema = QuestionSchema.from_file(QUESTIONS_DIR / "04-cloudflare.md")
    assert schema.phase == 4

    field_map = {f.id: f for f in schema.fields}

    defaults = field_map["cloudflare_defaults"]
    assert defaults.type == "derived"
    assert defaults.when == "exposure_mode == cloudflare"
    assert defaults.value["cloudflare.auth_method"] == "browser_login"
    assert defaults.value["cloudflare.tunnel_strategy"] == "new"


def test_phase_5_secrets_and_execution_generated():
    schema = QuestionSchema.from_file(QUESTIONS_DIR / "05-secrets.md")
    assert schema.phase == 5

    assert len(schema.execution_generated_only) == 1
    assert schema.execution_generated_only[0]["key"] == "IMMICH_VERSION"

    field_map = {f.id: f for f in schema.fields}
    secrets_mode = field_map["secrets_mode"]
    assert secrets_mode.type == "confirm"
    assert secrets_mode.accepted_inputs["y"] == "generate"
    assert secrets_mode.accepted_inputs["n"] == "manual"
    assert secrets_mode.records == ["secrets.mode"]

    manual = field_map["manual_secret_values"]
    assert manual.type == "secret_group"
    assert manual.when == "secrets.mode == manual"
    assert len(manual.entries) > 0
    assert manual.entries[0]["key"] == "POSTGRES_PASSWORD"

    n8n = field_map["n8n_mode"]
    assert n8n.type == "single_select"
    assert n8n.when == "n8n in selected_services"
    assert n8n.aliases["migrate"] == ["migrate", "restore", "restoring"]


def test_phase_6_summary_and_confirm():
    schema = QuestionSchema.from_file(QUESTIONS_DIR / "06-confirm.md")
    assert schema.phase == 6

    field_map = {f.id: f for f in schema.fields}

    summary = field_map["deployment_summary"]
    assert summary.type == "summary"
    assert "server_name" in summary.summary_fields

    confirmed = field_map["confirmed"]
    assert confirmed.type == "confirm"
    assert confirmed.prompt == "Proceed with deployment using the above configuration? [Y/n]"
    assert confirmed.default is True
    assert confirmed.records == ["confirmed"]


def test_question_schema_from_text():
    text = """
## AgentSchema
```yaml
schema_version: 1
phase: 99
fields:
  - id: test
    type: text
    prompt: Hello
```
"""
    schema = QuestionSchema.from_text(text)
    assert schema.phase == 99
    assert len(schema.fields) == 1
    assert schema.fields[0].id == "test"


def test_question_schema_missing_block_raises():
    with pytest.raises(ValueError, match="No AgentSchema block found"):
        QuestionSchema.from_text("# Just markdown\nNo schema here.")


def test_question_schema_non_dict_yaml_raises():
    text = "## AgentSchema\n```yaml\n- not a dict\n```\n"
    with pytest.raises(ValueError, match="AgentSchema block is not a YAML mapping"):
        QuestionSchema.from_text(text)


def test_question_schema_field_not_dict_raises():
    text = """
## AgentSchema
```yaml
schema_version: 1
phase: 1
fields:
  - not a dict
```
"""
    with pytest.raises(ValueError, match="Each field must be a YAML mapping"):
        QuestionSchema.from_text(text)


def test_question_schema_unknown_field_keys_ignored():
    text = """
## AgentSchema
```yaml
schema_version: 1
phase: 1
fields:
  - id: test
    type: text
    unknown_key: should_be_ignored
```
"""
    schema = QuestionSchema.from_text(text)
    assert schema.fields[0].id == "test"
    assert schema.fields[0].type == "text"
    assert not hasattr(schema.fields[0], "unknown_key")


def test_question_schema_case_insensitive_block():
    text = """
## agentschema
```yaml
schema_version: 1
phase: 42
fields: []
```
"""
    schema = QuestionSchema.from_text(text)
    assert schema.phase == 42


def test_load_all_schemas_empty_directory(tmp_path):
    schemas = load_all_schemas(tmp_path)
    assert schemas == []


def test_load_all_schemas_skips_files_without_schema(tmp_path):
    (tmp_path / "no_schema.md").write_text("# Just markdown\nNo schema here.")
    schemas = load_all_schemas(tmp_path)
    assert schemas == []


def test_load_all_schemas_malformed_yaml_raises(tmp_path):
    (tmp_path / "bad_yaml.md").write_text("## AgentSchema\n```yaml\n[ unclosed\n```\n")
    import yaml

    with pytest.raises(yaml.YAMLError):
        load_all_schemas(tmp_path)
