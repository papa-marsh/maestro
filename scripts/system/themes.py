from enum import StrEnum

from maestro.domains import UNAVAILABLE, UNKNOWN
from maestro.integrations import Domain, StateChangeEvent
from maestro.triggers import (
    HassEvent,
    MaestroEvent,
    hass_trigger,
    maestro_trigger,
    state_change_trigger,
)
from maestro.utils import log

from registry import input_select


# Must mirror the top-level theme names in the HA config's themes/themes.yaml.
# When a theme is added, renamed, or removed there, update this enum to match.
class Theme(StrEnum):
    DEFAULT = "Default"


@maestro_trigger(MaestroEvent.STARTUP)
@hass_trigger(HassEvent.STARTUP)
def sync_theme_options() -> None:
    input_select.theme_selector.set_options(list(Theme))


@state_change_trigger(input_select.theme_selector)
def apply_selected_theme(state_change: StateChangeEvent) -> None:
    theme = state_change.new.state
    if theme in (UNAVAILABLE, UNKNOWN):
        return

    hass_client = input_select.theme_selector.state_manager.hass_client
    hass_client.perform_action(Domain.FRONTEND, "reload_themes")
    hass_client.perform_action(Domain.FRONTEND, "set_theme", name=theme, mode="dark")
    log.info("Theme applied", theme=theme)
