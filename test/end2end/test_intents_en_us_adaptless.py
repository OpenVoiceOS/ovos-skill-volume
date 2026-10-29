"""Change, less, increase and current volume route with no Adapt stage.

The m2v prototype pipeline builds its intents from the skill's ``.intent``
files alone, so a route here shows that the intent files carry the match.
"""
import unittest

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession
from ovoscope.routing import PIPELINE, TALLY, get_prototype_minicroft

SKILL_ID = "ovos-skill-volume.openvoiceos"
LANG = "en-US"

_IGNORE = [
    "speak",
    "ovos.utterance.speak",
    "mycroft.audio.play_sound",
    "mycroft.volume.set",
    "mycroft.volume.get",
    "mycroft.volume.increase",
    "mycroft.volume.decrease",
    "mycroft.volume.mute",
    "mycroft.volume.unmute",
    "mycroft.volume.mute.toggle",
]


class TestVolumeIntentsAdaptless(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.minicroft = get_prototype_minicroft([SKILL_ID])

    @classmethod
    def tearDownClass(cls):
        cls.minicroft.stop()

    def _types(self, text):
        session = Session(f"test-adaptless-{hash(text)}")
        session.lang = LANG
        session.pipeline = list(PIPELINE)
        session.blacklisted_intents = []
        utterance = Message(
            "recognizer_loop:utterance",
            {"utterances": [text], "lang": LANG},
            {"session": session.serialize(), "source": "A", "destination": "B"},
        )
        capture = CaptureSession(
            self.minicroft,
            eof_msgs=["mycroft.skill.handler.start"],
            ignore_messages=_IGNORE,
        )
        capture.capture(utterance, timeout=30)
        return [m.msg_type for m in capture.finish()]

    def _assert_intent(self, text, intent):
        TALLY.assert_routed(text, f"{SKILL_ID}:{intent}", self._types(text))

    def test_increase_volume_up(self):
        self._assert_intent("volume up", "increase_volume")

    def test_increase_volume_verbose(self):
        self._assert_intent("increase the volume", "increase_volume")

    def test_less_volume_down(self):
        self._assert_intent("volume down", "less_volume")

    def test_change_volume_to_level(self):
        self._assert_intent("set the volume to 50", "change_volume")

    def test_current_volume_query(self):
        self._assert_intent("what is the current volume", "current_volume")

    def test_volume_up_does_not_match_less_or_current(self):
        types = self._types("volume up")
        TALLY.assert_routed("volume up", f"{SKILL_ID}:increase_volume", types)
        self.assertNotIn(f"{SKILL_ID}:less_volume", types)
        self.assertNotIn(f"{SKILL_ID}:current_volume", types)

    def test_turn_up_the_volume(self):
        self._assert_intent("turn up the volume", "increase_volume")

    def test_turn_the_volume_up(self):
        self._assert_intent("turn the volume up", "increase_volume")

    def test_turn_down_the_volume(self):
        self._assert_intent("turn down the volume", "less_volume")

    def test_set_the_volume_to_max(self):
        self._assert_intent("set the volume to max", "volume_level")

    def test_set_the_volume_to_high(self):
        self._assert_intent("set the volume to high", "volume_level")

    def test_set_the_volume_to_low(self):
        self._assert_intent("set the volume to low", "volume_level")

    def test_set_the_volume_to_normal(self):
        self._assert_intent("set the volume to normal", "volume_level")

    def test_change_volume_to_level_percent(self):
        self._assert_intent("set the volume to 50 percent", "change_volume")


if __name__ == "__main__":
    unittest.main()
