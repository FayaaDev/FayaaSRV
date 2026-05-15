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
        disabled_values={"mac": "soon"},
        aliases={"linux": ["linux"], "mac": ["mac", "macos"]},
        records=["platform"],
    )


def test_single_select_disables_unavailable_values():
    with patch("rakkib.interview.prompt_select", return_value="linux") as mock_select:
        assert _prompt_single_select(_platform_field(), State({})) == "linux"

    choices = mock_select.call_args.kwargs["choices"]
    mac_choice = next(choice for choice in choices if choice.value == "mac")
    assert mac_choice.title == "mac"
    assert mac_choice.disabled == "soon"


def test_single_select_rejects_disabled_alias_fallback():
    with patch("rakkib.interview.prompt_select", return_value=None), patch(
        "rakkib.interview.prompt_text", side_effect=["macos", "linux"]
    ):
        assert _prompt_single_select(_platform_field(), State({})) == "linux"
