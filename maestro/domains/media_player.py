from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class MediaPlayer(Entity):
    domain = Domain.MEDIA_PLAYER
    allow_set_state = False

    def turn_on(self) -> None:
        self.perform_action("turn_on")

    def turn_off(self) -> None:
        self.perform_action("turn_off")

    def toggle(self) -> None:
        self.perform_action("toggle")

    def play(
        self,
        content_id: str | None = None,
        content_type: str = "music",
        enqueue: bool = False,
    ) -> None:
        if content_id is None:
            self.perform_action("media_play")
            return
        self.perform_action(
            "play_media",
            media_content_id=content_id,
            media_content_type=content_type,
            enqueue=enqueue,
        )

    def pause(self) -> None:
        self.perform_action("media_pause")

    def next(self) -> None:
        self.perform_action("media_next_track")

    def previous(self) -> None:
        self.perform_action("media_previous_track")

    def set_repeat(self, repeat: bool) -> None:
        self.perform_action("repeat_set", repeat=repeat)

    def set_shuffle(self, shuffle: bool) -> None:
        self.perform_action("shuffle_set", shuffle=shuffle)

    def select_source(self, source: str) -> None:
        self.perform_action("select_source", source=source)

    def volume_up(self) -> None:
        self.perform_action("volume_up")

    def volume_down(self) -> None:
        self.perform_action("volume_down")

    def set_volume(self, volume: float) -> None:
        if not (0 <= volume <= 1):
            raise ValueError

    def mute(self) -> None:
        self.perform_action("volume_mute", is_volume_muted=True)

    def unmute(self) -> None:
        self.perform_action("volume_mute", is_volume_muted=False)
