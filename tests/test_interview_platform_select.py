from unittest.mock import patch

from rakkib.interview import _prompt_single_select
from rakkib.schema import FieldDef
from rakkib.state import State


def _platform_field() -> FieldDef:
    return FieldDef(
        id="platform",
        type="single_select",
        prompt="Platform?",
        canonical_values=["linux", "mac"],
        display_labels={"linux": "Linux (Ubuntu 24.04)", "mac": "macOS"},
        disabled_values={"mac": "soon"},
        aliases={"linux": ["linux"], "mac": ["mac", "macos"]},
        records=["platform"],
    )


def test_single_select_disables_unavailable_values():
    with patch("rakkib.interview.prompt_select", return_value="linux") as mock_select:
        assert _prompt_single_select(_platform_field(), State({})) == "linux"

    choices = mock_select.call_args.kwargs["choices"]
    linux_choice = next(choice for choice in choices if choice.value == "linux")
    mac_choice = next(choice for choice in choices if choice.value == "mac")
    assert linux_choice.title == "Linux (Ubuntu 24.04)"
    assert mac_choice.title == "macOS"
    assert mac_choice.disabled == "soon"


def test_single_select_rejects_disabled_alias_fallback():
    with (
        patch("rakkib.interview.prompt_select", return_value=None),
        patch("rakkib.interview.prompt_text", side_effect=["macos", "linux"]),
    ):
        assert _prompt_single_select(_platform_field(), State({})) == "linux"
