"""End-to-end intent routing tests for the en-US locale.

Each canonical utterance is fired through a real MiniCroft and asserted to
route to the expected intent handler. Coverage spans the level intent
(volume_level, covering max/high/default/low plus the max-boost and reset
idioms), mute/unmute/mute-toggle, and change/less/increase/current volume.
The side effects (mycroft.volume.*, the spoken confirmation) vary by hardware
backend and are ignored so the assertion covers only the intent binding.
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


class TestVolumeIntentsEnUS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.minicroft = get_prototype_minicroft([SKILL_ID])

    @classmethod
    def tearDownClass(cls):
        cls.minicroft.stop()

    def _types(self, text):
        session = Session(f"test-{hash(text)}")
        session.lang = LANG
        session.pipeline = list(PIPELINE)
        session.blacklisted_intents = []
        utterance = Message(
            "recognizer_loop:utterance",
            {"utterances": [text], "lang": LANG},
            {"session": session.serialize(), "source": "A", "destination": "B"},
        )
        # End capture when the handler starts (right after the intent fires)
        # rather than at ovos.utterance.handled: some handlers block on a
        # follow-up get_response or a PHAL volume query, which never resolves in
        # a bare MiniCroft. The intent binding under test is emitted first, so
        # this bounds each case while still capturing what is asserted.
        capture = CaptureSession(
            self.minicroft,
            eof_msgs=["mycroft.skill.handler.start"],
            ignore_messages=_IGNORE,
        )
        capture.capture(utterance, timeout=30)
        return [m.msg_type for m in capture.finish()]

    def _assert_intent(self, text, intent):
        TALLY.assert_routed(text, f"{SKILL_ID}:{intent}", self._types(text))

    # volume_level.intent (merges the former discrete
    # volume.{max,high,default,low}.intent files behind a single {level}
    # slot; see level.{max,high,medium,low,default}.voc for the accepted
    # level words)
    def test_max_volume(self):
        self._assert_intent("max volume", "volume_level.intent")

    def test_set_volume_to_maximum(self):
        self._assert_intent("set volume to maximum", "volume_level.intent")

    def test_high_volume(self):
        self._assert_intent("high volume", "volume_level.intent")

    def test_volume_to_high(self):
        self._assert_intent("volume to high", "volume_level.intent")

    def test_default_volume(self):
        self._assert_intent("default volume", "volume_level.intent")

    def test_low_volume(self):
        self._assert_intent("low volume", "volume_level.intent")

    def test_volume_to_low(self):
        self._assert_intent("volume to low", "volume_level.intent")

    # volume_max_boost.intent (non-slot idioms carried over from
    # the old volume.max.intent -- "crank the volume", "turn it all the way
    # up" -- that don't fit the {level} slot template)
    def test_crank_volume(self):
        self._assert_intent("crank the volume", "volume_max_boost.intent")

    # volume_reset.intent: "reset" and "restore" are verbs, not level names,
    # so they are not in the level vocabularies that volume_level inlines
    def test_reset_the_volume(self):
        self._assert_intent("reset the volume", "volume_reset.intent")

    def test_reset_volume(self):
        self._assert_intent("reset volume", "volume_reset.intent")

    def test_restore_volume_please(self):
        self._assert_intent("restore volume please", "volume_reset.intent")

    # volume_mute.intent
    def test_mute(self):
        self._assert_intent("mute", "volume_mute.intent")

    def test_mute_audio(self):
        self._assert_intent("mute audio", "volume_mute.intent")

    # volume_unmute.intent
    def test_unmute(self):
        self._assert_intent("unmute", "volume_unmute.intent")

    def test_unmute_audio(self):
        self._assert_intent("unmute audio", "volume_unmute.intent")

    # volume_mute_toggle.intent
    def test_toggle_mute(self):
        self._assert_intent("toggle mute", "volume_mute_toggle.intent")

    # change_volume. Include a number so the handler sets the level
    # directly instead of opening a get_response follow-up dialog.
    def test_change_volume_to_level(self):
        self._assert_intent("change volume to 50", "change_volume")

    # less_volume
    def test_volume_decrease(self):
        self._assert_intent("volume decrease", "less_volume")

    # increase_volume
    def test_volume_higher(self):
        self._assert_intent("volume higher", "increase_volume")

    # current_volume
    def test_current_volume(self):
        self._assert_intent("current volume", "current_volume")


if __name__ == "__main__":
    unittest.main()
