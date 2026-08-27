from maestro.triggers import cron_trigger

from registry import switch


@cron_trigger(hour=21, minute=30)
def bedtime() -> None:
    switch.master_sound_machine.turn_on()
