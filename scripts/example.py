from maestro.domains import Switch
from maestro.integrations import StateChangeEvent
from maestro.triggers import state_change_trigger


@state_change_trigger("binary_sensor.front_door")
def front_door_automation(state_change: StateChangeEvent):
    if state_change.new_state == "on":
        entryway_light = Switch("switch.entryway_light")
        entryway_light.turn_on()
