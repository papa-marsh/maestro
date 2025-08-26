from maestro.domains.entity import Domain, Entity


class Switch(Entity):
    domain = Domain.SWITCH

    def turn_on(self) -> None:
        self.perform_action("turn_on")

    def turn_off(self) -> None:
        self.perform_action("turn_off")

    def toggle(self) -> None:
        self.perform_action("toggle")
