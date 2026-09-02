"""Regression test for a live crash: "set volume to 50" (or any change_volume
match with no extractable number in the initial utterance) opens a
get_response follow-up; if that follow-up expires or is cancelled,
get_response returns None and the handler used to feed it straight into
extract_number(normalizer.normalize(None)), which raised
"TypeError: expected string or bytes-like object, got 'NoneType'" deep inside
the utterance normalizer's tokenizer regex.
"""
import unittest
from os.path import dirname
from unittest.mock import MagicMock

from ovos_bus_client.message import Message
from ovos_utils.messagebus import FakeBus

from ovos_skill_volume import VolumeSkill


class TestChangeVolumeNoneResponse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_id = "ovos-skill-volume.openvoiceos"
        cls.path = dirname(dirname(dirname(__file__)))

    def _make_skill(self):
        bus = FakeBus()
        skill = VolumeSkill()
        skill._startup(bus, self.skill_id)
        skill.get_response = MagicMock(return_value=None)
        skill.speak_dialog = MagicMock()
        return skill

    def test_none_response_does_not_crash(self):
        skill = self._make_skill()
        message = Message(
            "change_volume.intent",
            {"utterance": "change the volume"},
            {"lang": "en-US"},
        )
        # must not raise TypeError: expected string or bytes-like object
        skill.handle_change_volume_intent(message)
        skill.speak_dialog.assert_called_once_with("error.get.volume")
