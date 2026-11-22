from maestro.domains import MediaPlayer
from maestro.integrations import Domain
from maestro.testing import MaestroTest

from custom_domains.sonos_speaker import SonosSpeaker
from registry import media_player

from .. import media

test_speaker = media_player.living_room


def test_speaker_config() -> None:
    # Speaker lists are unchanged and main speakers subclass SonosSpeaker
    assert len(media.MAIN_SPEAKERS) == 3
    assert len(media.ALL_SPEAKERS) == 6
    for speaker in media.MAIN_SPEAKERS:
        assert isinstance(speaker, SonosSpeaker)


def test_reset_speakers(mt: MaestroTest) -> None:
    # All speakers are paused, unmuted, and have volume set to default
    media.reset_speakers()
    for speaker in media.ALL_SPEAKERS:
        mt.assert_action_called(Domain.MEDIA_PLAYER, "media_pause", speaker.id)
        mt.assert_action_called(
            Domain.MEDIA_PLAYER,
            "volume_mute",
            speaker.id,
            is_volume_muted=False,
        )
    for speaker in media.ALL_SPEAKERS:
        mt.assert_action_called(Domain.MEDIA_PLAYER, "volume_set", speaker.id)


def test_group_speakers(mt: MaestroTest) -> None:
    main_speaker_ids = [speaker.id for speaker in media.MAIN_SPEAKERS]
    # Nothing happens if all speakers are grouped
    mt.trigger_state_change(
        test_speaker,
        new="playing",
        new_attributes={"group_members": main_speaker_ids},
    )
    mt.assert_action_not_called(Domain.MEDIA_PLAYER, "join")

    # Speakers group to target if none are grouped
    mt.trigger_state_change(
        test_speaker,
        new="playing",
        new_attributes={"group_members": []},
    )
    mt.assert_action_called(Domain.MEDIA_PLAYER, "join", test_speaker.id)

    # Speakers group to target if some are grouped
    mt.trigger_state_change(
        test_speaker,
        new="playing",
        new_attributes={"group_members": main_speaker_ids[1:]},
    )
    mt.assert_action_called(Domain.MEDIA_PLAYER, "join", test_speaker.id)
