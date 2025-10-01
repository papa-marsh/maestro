from structlog.stdlib import get_logger

from maestro.integrations import StateChangeEvent
from maestro.registry import switch
from maestro.triggers import cron_trigger, state_change_trigger

log = get_logger()


@cron_trigger(hour=17)
def ellie_bedtime_prep() -> None:
    switch.ellies_sound_machine.turn_on()


@cron_trigger(hour=7)
def ellie_wakeup() -> None:
    switch.ellies_sound_machine.turn_off()


@state_change_trigger(switch.ellies_sound_machine)
def toggle_butterfly_light(state_change: StateChangeEvent) -> None:
    if state_change.new.state == "off":
        switch.butterfly_night_light.turn_on()
    else:
        switch.butterfly_night_light.turn_off()
