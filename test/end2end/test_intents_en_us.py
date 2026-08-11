"""End-to-end intent routing tests for the en-US locale.

Each canonical utterance is fired through a real MiniCroft and asserted to
route to the expected intent handler. Coverage spans the padatious level intents
(max/high/default/low/mute/unmute/mute-toggle) and the adapt intents
(change/less/increase/current volume). The side effects (mycroft.volume.*, the
spoken confirmation) vary by hardware backend and are ignored so the assertion
covers only the intent binding.
"""
import unittest

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-volume.openvoiceos"
LANG = "en-US"

_PIPELINE = [
    "ovos-adapt-pipeline-plugin-high",
    "ovos-padatious-pipeline-plugin-high",
    "ovos-padacioso-pipeline-plugin-high",
    "ovos-adapt-pipeline-plugin-medium",
    "ovos-padacioso-pipeline-plugin-medium",
    "ovos-adapt-pipeline-plugin-low",
]

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
        cls.minicroft = get_minicroft([SKILL_ID])

    @classmethod
    def tearDownClass(cls):
        cls.minicroft.stop()

    def _types(self, text):
        session = Session(f"test-{hash(text)}")
        session.lang = LANG
        session.pipeline = list(_PIPELINE)
        # blacklisted_intents defaults to None on a fresh Session, which crashes
        # the padacioso pipeline (NoneType membership test) - force an empty list.
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
        # OVOS-INTENT-2: the per-skill dispatch topic no longer carries the
        # ".intent" suffix present in the intent file/label (same migration
        # already applied in ovos-skill-camera#63 / ovos-skill-parrot#119).
        intent = intent.removesuffix(".intent")
        self.assertIn(f"{SKILL_ID}:{intent}", self._types(text))

    # padatious: volume.max.intent
    def test_max_volume(self):
        self._assert_intent("max volume", "volume.max.intent")

    def test_set_volume_to_maximum(self):
        self._assert_intent("set volume to maximum", "volume.max.intent")

    # padatious: volume.high.intent
    def test_high_volume(self):
        self._assert_intent("high volume", "volume.high.intent")

    def test_volume_to_high(self):
        self._assert_intent("volume to high", "volume.high.intent")

    # padatious: volume.default.intent
    def test_default_volume(self):
        self._assert_intent("default volume", "volume.default.intent")

    def test_reset_volume(self):
        self._assert_intent("reset volume", "volume.default.intent")

    # padatious: volume.low.intent
    def test_low_volume(self):
        self._assert_intent("low volume", "volume.low.intent")

    def test_volume_to_low(self):
        self._assert_intent("volume to low", "volume.low.intent")

    # padatious: volume.mute.intent
    def test_mute(self):
        self._assert_intent("mute", "volume.mute.intent")

    def test_mute_audio(self):
        self._assert_intent("mute audio", "volume.mute.intent")

    # padatious: volume.unmute.intent
    def test_unmute(self):
        self._assert_intent("unmute", "volume.unmute.intent")

    def test_unmute_audio(self):
        self._assert_intent("unmute audio", "volume.unmute.intent")

    # padatious: volume.mute.toggle.intent
    def test_toggle_mute(self):
        self._assert_intent("toggle mute", "volume.mute.toggle.intent")

    # adapt: change_volume. Include a number so the handler sets the level
    # directly instead of opening a get_response follow-up dialog.
    def test_change_volume_to_level(self):
        self._assert_intent("change volume to 50", "change_volume")

    # adapt: less_volume
    def test_volume_decrease(self):
        self._assert_intent("volume decrease", "less_volume")

    # adapt: increase_volume
    def test_volume_higher(self):
        self._assert_intent("volume higher", "increase_volume")

    # adapt: current_volume
    def test_current_volume(self):
        self._assert_intent("current volume", "current_volume")


if __name__ == "__main__":
    unittest.main()
