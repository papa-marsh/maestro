from maestro.domains.entity import Entity, EntityAttribute
from maestro.integrations.home_assistant.types import Domain


class Light(Entity):
    domain = Domain.LIGHT

    min_color_temp_kelvin = EntityAttribute(int)
    max_color_temp_kelvin = EntityAttribute(int)
    min_mireds = EntityAttribute(int)
    max_mireds = EntityAttribute(int)
    supported_color_modes = EntityAttribute(list)
    color_mode = EntityAttribute(str)
    brightness = EntityAttribute(int)
    color_temp_kelvin = EntityAttribute(int)
    color_temp = EntityAttribute(int)
    hs_color = EntityAttribute(list)
    rgb_color = EntityAttribute(list)
    xy_color = EntityAttribute(list)

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
