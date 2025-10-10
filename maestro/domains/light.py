from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Light(Entity):
    domain = Domain.LIGHT

    def turn_on(
        self,
        rgb_color: tuple[int, int, int],
        temperature: int,
        brightness_percent: int = 100,
        transition_seconds: int = 0,
    ) -> None:
        self.perform_action(
            "turn_on",
            rgb_color=rgb_color,
            color_temp_kelvin=temperature,
            brightness_pct=brightness_percent,
            transition=transition_seconds,
        )

    def turn_off(self, transition_seconds: int = 0) -> None:
        self.perform_action("turn_off", transition=transition_seconds)

    def toggle(self) -> None:
        self.perform_action("toggle")
