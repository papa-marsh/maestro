from maestro.triggers import event_fired_trigger
from maestro.utils import local_now

from registry import switch
from scripts.common.event_type import EventType


@event_fired_trigger(EventType.OLIVIA_ASLEEP)
def sound_machines_on() -> None:
    switch.olivias_sound_machine.turn_on()


@event_fired_trigger(EventType.OLIVIA_AWAKE)
def sound_machines_off() -> None:
    switch.olivias_sound_machine.turn_off()

    if 6 <= local_now().hour < 8:
        switch.master_sound_machine.turn_off()
