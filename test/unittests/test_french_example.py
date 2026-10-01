"""A complete localized example must still set the requested volume."""
from pathlib import Path
from unittest.mock import Mock

from ovos_bus_client.message import Message
from ovos_skill_volume import VolumeSkill


class FrenchVolumeHarness(VolumeSkill):
    @property
    def lang(self):
        return "fr-FR"

    def __del__(self):
        pass


def test_french_example_sets_fifty_percent_without_an_entity():
    skill = FrenchVolumeHarness.__new__(FrenchVolumeHarness)
    skill._bus = Mock()
    skill.speak_dialog = Mock()
    skill.get_response = Mock(side_effect=AssertionError("number already supplied"))
    utterance = "mets le volume à cinquante"
    locale = Path(__file__).parents[2] / "locale/fr-FR/change_volume.intent"
    assert utterance in locale.read_text().splitlines()
    skill.handle_change_volume_intent(Message("change_volume.intent", {"utterance": utterance}))
    sent = skill._bus.emit.call_args.args[0]
    assert sent.msg_type == "mycroft.volume.set"
    assert sent.data == {"percent": 0.5}
