from enum import StrEnum, auto

from maestro.domains.entity import Entity, EntityAttribute
from maestro.integrations.home_assistant.types import Domain


class Climate(Entity):
    domain = Domain.CLIMATE

    hvac_modes = EntityAttribute(str)
    min_temp = EntityAttribute(int)
    max_temp = EntityAttribute(int)
    preset_modes = EntityAttribute(list)
    current_temperature = EntityAttribute(int)
    temperature = EntityAttribute(int)
    preset_mode = EntityAttribute(str)

    def turn_on(self) -> None:
        self.perform_action("turn_on")

    def turn_off(self) -> None:
        self.perform_action("turn_off")

    def toggle(self) -> None:
        self.perform_action("toggle")

    def set_temp_target(self, target_temp: int) -> None:
        self.perform_action("set_temperature", target_temp=target_temp)

    def set_temp_range(self, target_low: int, target_high: int) -> None:
        self.perform_action(
            "set_temperature",
            target_temp_low=target_low,
            target_temp_high=target_high,
        )


class ThermostatClimate(Climate):
    class HVACMode(StrEnum):
        OFF = auto()
        COOL = auto()
        HEAT = auto()

    class FanMode(StrEnum):
        ON = auto()
        AUTO = auto()
        DIFFUSE = auto()

    class PresetMode(StrEnum):
        NONE = auto()
        AWAY = auto()
        HOLD = auto()

    current_humidity = EntityAttribute(int)
    fan_modes = EntityAttribute(list)
    fan_mode = EntityAttribute(str)
    hvac_action = EntityAttribute(str)
    permanent_hold = EntityAttribute(bool)

    def set_fan_mode(self, mode: FanMode) -> None:
        self.perform_action("set_fan_mode", mode=mode)

    def set_hvac_mode(self, mode: HVACMode) -> None:
        self.perform_action("set_hvac_mode", mode=mode)

    def set_preset_mode(self, mode: PresetMode) -> None:
        self.perform_action("set_preset_mode", mode=mode)


class HeatedFloorClimate(Climate):
    class HVACMode(StrEnum):
        AUTO = auto()
        HEAT = auto()

    class PresetMode(StrEnum):
        RUN_SCHEDULE = "Run Schedule"
        TEMPORARY_HOLD = "Temporary Hold"
        PERMANENT_HOLD = "Permanent Hold"

    hvac_action = EntityAttribute(str)

    def set_hvac_mode(self, mode: HVACMode) -> None:
        self.perform_action("set_hvac_mode", mode=mode)

    def set_preset_mode(self, mode: PresetMode) -> None:
        self.perform_action("set_preset_mode", mode=mode)


class TeslaClimate(Climate):
    class HVACMode(StrEnum):
        OFF = auto()
        HEAT_COOL = auto()

    class FanMode(StrEnum):
        OFF = auto()
        BIOWEAPON = auto()

    class PresetMode(StrEnum):
        NORMAL = auto()
        DEFROST = auto()
        KEEP = auto()
        DOG = auto()
        CAMP = auto()

    fan_modes = EntityAttribute(list)
    fan_mode = EntityAttribute(str)

    def set_fan_mode(self, mode: FanMode) -> None:
        self.perform_action("set_fan_mode", mode=mode)

    def set_hvac_mode(self, mode: HVACMode) -> None:
        self.perform_action("set_hvac_mode", mode=mode)

    def set_preset_mode(self, mode: PresetMode) -> None:
        self.perform_action("set_preset_mode", mode=mode)
