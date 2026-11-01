"""Tests for theme selector sync and theme application"""

from maestro.domains import UNAVAILABLE
from maestro.integrations import Domain
from maestro.testing import MaestroTest
from maestro.triggers import MaestroEvent

from registry import input_select

from .. import themes


def test_startup_syncs_theme_options(mt: MaestroTest) -> None:
    """Test that startup populates the theme selector with every known theme"""
    mt.trigger_maestro_event(MaestroEvent.STARTUP)

    mt.assert_action_called(
        Domain.INPUT_SELECT,
        "set_options",
        entity_id=input_select.theme_selector.id,
        options=list(themes.Theme),
    )


def test_selection_reloads_and_applies_theme(mt: MaestroTest) -> None:
    """Test that selecting a theme reloads themes and sets it as the dark backend theme"""
    mt.trigger_state_change(input_select.theme_selector, new=themes.Theme.DEFAULT)

    mt.assert_action_called(Domain.FRONTEND, "reload_themes")
    mt.assert_action_called(Domain.FRONTEND, "set_theme", name=themes.Theme.DEFAULT, mode="dark")


def test_unavailable_selection_is_ignored(mt: MaestroTest) -> None:
    """Test that an unavailable selector state doesn't touch themes"""
    mt.trigger_state_change(input_select.theme_selector, new=UNAVAILABLE)

    mt.assert_action_not_called(Domain.FRONTEND, "reload_themes")
    mt.assert_action_not_called(Domain.FRONTEND, "set_theme")
