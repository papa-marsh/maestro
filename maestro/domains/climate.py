from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Climate(Entity):
    domain = Domain.CLIMATE

    def turn_on(self) -> None:
        self.perform_action("turn_on")

    def turn_off(self) -> None:
        self.perform_action("turn_off")

    def toggle(self) -> None:
        self.perform_action("toggle")

    def set_fan_mode(self, mode: str) -> None:
        self.perform_action("set_fan_mode", fan_mode=mode)

    def set_hvac_mode(self, mode: str) -> None:
        self.perform_action("set_hvac_mode", hvac_mode=mode)

    def set_preset_mode(self, mode: str) -> None:
        self.perform_action("set_preset_mode", preset_mode=mode)

    def set_temperature(self, target_temp: int) -> None:
        self.perform_action("set_temperature", target_temp=target_temp)

    def set_temp_range(self, target_low: int, target_high: int) -> None:
        self.perform_action(
            "set_temperature",
            target_temp_low=target_low,
            target_temp_high=target_high,
        )
