from maestro.integrations import StateChangeEvent
from maestro.triggers import cron_trigger, state_change_trigger

from custom_domains.sonos_speaker import SonosSpeaker
from registry import media_player

MAIN_SPEAKERS: list[SonosSpeaker] = [
    media_player.living_room,
    media_player.craft_room,
    media_player.front_room,
]
ALL_SPEAKERS: list[SonosSpeaker] = [
    *MAIN_SPEAKERS,
    media_player.portable,
    media_player.basement,
    media_player.office,
]


@cron_trigger(hour=3)
def reset_speakers() -> None:
    for speaker in ALL_SPEAKERS:
        speaker.pause()
        speaker.unmute()

    for speaker in MAIN_SPEAKERS:
        speaker.set_volume(0.4)

    media_player.portable.set_volume(0.2)
    media_player.basement.set_volume(0.3)
    media_player.office.set_volume(0.35)


@state_change_trigger(*MAIN_SPEAKERS, to_state="playing")
def group_speakers(state_change: StateChangeEvent) -> None:
    target = state_change.entity_id.resolve_entity()
    if not isinstance(target, SonosSpeaker):
        raise TypeError

    if all(speaker.id in target.group_members for speaker in MAIN_SPEAKERS):
        return

    target.join(MAIN_SPEAKERS)
