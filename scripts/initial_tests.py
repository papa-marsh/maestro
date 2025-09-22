from structlog.stdlib import get_logger

from maestro.integrations import FiredEvent, StateChangeEvent
from maestro.registry import person, switch
from maestro.triggers import cron_trigger, state_change_trigger
from maestro.triggers.event_fired import event_fired_trigger

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


@cron_trigger("* * * * *")
def cron_test() -> None:
    log.info("HEREEEEEEEE")


@event_fired_trigger("test_event")
def event_test_1() -> None:
    log.info("EVENT TEST 1")


@event_fired_trigger("test_event", user=person.marshall)
def event_test_2(event: FiredEvent) -> None:
    log.info("EVENT TEST 2")
    log.info(str(event.data))


@event_fired_trigger("test_event", user="hfjhs8293rjofwei")
def event_test_3(event: FiredEvent) -> None:
    log.info("EVENT TEST 3")
    log.info(str(event.data))
