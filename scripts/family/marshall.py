from maestro.triggers import cron_trigger

from registry import switch


@cron_trigger(hour=22)
def bedtime() -> None:
    switch.master_sound_machine.turn_on()
