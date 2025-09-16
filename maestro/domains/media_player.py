from maestro.domains.entity import Entity, EntityAttribute
from maestro.integrations.home_assistant.types import Domain


class MediaPlayer(Entity):
    domain = Domain.MEDIA_PLAYER

    def turn_on(self) -> None:
        self.perform_action("turn_on")

    def turn_off(self) -> None:
        self.perform_action("turn_off")

    def toggle(self) -> None:
        self.perform_action("toggle")

    def media_play(self) -> None:
        self.perform_action("media_play")

    def media_pause(self) -> None:
        self.perform_action("media_pause")

    def media_stop(self) -> None:
        self.perform_action("media_stop")

    def media_next_track(self) -> None:
        self.perform_action("media_next_track")

    def media_previous_track(self) -> None:
        self.perform_action("media_previous_track")