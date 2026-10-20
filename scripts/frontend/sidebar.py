from maestro.triggers import (
    HassEvent,
    MaestroEvent,
    cron_trigger,
    hass_trigger,
    maestro_trigger,
    state_change_trigger,
)
from maestro.utils import local_now

from registry import maestro, sun


@hass_trigger(HassEvent.STARTUP)
@maestro_trigger(MaestroEvent.STARTUP)
@state_change_trigger(sun.sun)
@cron_trigger(hour=0)
def set_sidebar_text() -> None:
    today = local_now().strftime("%A")

    if sun.sun.is_above_horizon:
        sun_action = "sets"
        sun_time = sun.sun.next_setting.strftime("%-I:%M %p")
    else:
        sun_action = "rises"
        sun_time = sun.sun.next_rising.strftime("%-I:%M %p")

    sidebar_text = f"""
        <li>Happy {today}!</li>
        <li>The sun {sun_action} at {sun_time}.</li>
    """

    maestro.cast_sidebar_text.state_manager.post_hass_entity(
        entity_id=maestro.cast_sidebar_text.id,
        state=sidebar_text,
        attributes={},
    )
