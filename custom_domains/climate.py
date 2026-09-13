from enum import StrEnum, auto
from typing import override

from maestro.domains import Climate, EntityAttribute


class Thermostat(Climate):
    temperature = EntityAttribute(float)

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

    @override
    def set_fan_mode(self, mode: FanMode) -> None:  # type:ignore[override]
        self.perform_action("set_fan_mode", fan_mode=mode)

    @override
    def set_hvac_mode(self, mode: HVACMode) -> None:  # type:ignore[override]
        self.perform_action("set_hvac_mode", hvac_mode=mode)

    @override
    def set_preset_mode(self, mode: PresetMode) -> None:  # type:ignore[override]
        self.perform_action("set_preset_mode", preset_mode=mode)


class BathroomFloor(Climate):
    class HVACMode(StrEnum):
        AUTO = auto()
        HEAT = auto()

    class PresetMode(StrEnum):
        RUN_SCHEDULE = "Run Schedule"
        TEMPORARY_HOLD = "Temporary Hold"
        PERMANENT_HOLD = "Permanent Hold"

    @override
    def set_hvac_mode(self, mode: HVACMode) -> None:  # type:ignore[override]
        self.perform_action("set_hvac_mode", hvac_mode=mode)

    @override
    def set_preset_mode(self, mode: PresetMode) -> None:  # type:ignore[override]
        self.perform_action("set_preset_mode", preset_mode=mode)


class TeslaHVAC(Climate):
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

    @override
    def set_fan_mode(self, mode: FanMode) -> None:  # type:ignore[override]
        self.perform_action("set_fan_mode", fan_mode=mode)

    @override
    def set_hvac_mode(self, mode: HVACMode) -> None:  # type:ignore[override]
        self.perform_action("set_hvac_mode", hvac_mode=mode)

    @override
    def set_preset_mode(self, mode: PresetMode) -> None:  # type:ignore[override]
        self.perform_action("set_preset_mode", preset_mode=mode)
