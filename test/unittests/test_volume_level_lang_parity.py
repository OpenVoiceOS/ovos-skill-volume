"""Regression tests for the volume_level lang-parity migration.

Bare level words (it-IT "Grida", de-DE "Standardlautstärke", nl-NL
"standaardvolume") match volume_level.intent as literal-only training
lines with no {level} slot at all -- handle_set_volume_level used to
resolve the level exclusively from message.data["level"], so these
routed correctly but silently spoke "volume.level.unknown" instead of
setting the level. Separately, it-IT/nl-NL's pre-existing
change_volume.intent trains an almost identical template with the same
{level} slot name for numeric amounts, so plain adjective/noun level
words like "medio"/"maximaal" could be captured by change_volume
instead of volume_level.

These tests exercise handle_set_volume_level (and, for the numeric
regression check, handle_change_volume_intent) directly against a
FakeBus, asserting the actual "mycroft.volume.set" percent emitted --
the layer where the bug actually lived, since intent-routing alone
(asserted by the end2end golden-utterance suite) does not prove the
handler resolved the correct level.
"""
import unittest
from unittest.mock import MagicMock

from ovos_bus_client.message import Message
from ovos_utils.messagebus import FakeBus

from ovos_skill_volume import VolumeSkill


class TestVolumeLevelLangParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_id = "ovos-skill-volume.openvoiceos"

    def _make_skill(self):
        bus = FakeBus()
        skill = VolumeSkill()
        skill._startup(bus, self.skill_id)
        skill.bus.emit = MagicMock()
        skill.speak_dialog = MagicMock()
        return skill

    def _set_percent(self, skill, lang, data):
        message = Message("volume_level.intent", data, {"lang": lang})
        skill.handle_set_volume_level(message)
        for call in skill.bus.emit.call_args_list:
            emitted = call.args[0]
            if emitted.msg_type == "mycroft.volume.set":
                return emitted.data["percent"]
        return None

    # bare level words: no {level} slot, must resolve from the whole utterance
    def test_bare_word_it_grida_resolves_high(self):
        skill = self._make_skill()
        percent = self._set_percent(skill, "it-IT", {"utterance": "Grida"})
        self.assertEqual(percent, 0.9)

    def test_bare_word_it_urla_resolves_high(self):
        skill = self._make_skill()
        percent = self._set_percent(skill, "it-IT", {"utterance": "Urla"})
        self.assertEqual(percent, 0.9)

    def test_bare_word_it_sussurra_resolves_low(self):
        skill = self._make_skill()
        percent = self._set_percent(skill, "it-IT", {"utterance": "Sussurra"})
        self.assertEqual(percent, 0.3)

    def test_bare_word_de_standardlautstaerke_resolves_default(self):
        skill = self._make_skill()
        percent = self._set_percent(skill, "de-DE", {"utterance": "Standardlautstärke"})
        self.assertEqual(percent, 0.7)

    def test_bare_word_nl_standaardvolume_resolves_default(self):
        skill = self._make_skill()
        percent = self._set_percent(skill, "nl-NL", {"utterance": "standaardvolume"})
        self.assertEqual(percent, 0.7)

    # {level}-slot words that used to lose the classification race to
    # change_volume.intent (same slot name, near-identical template)
    def test_slot_it_medio_resolves_default(self):
        skill = self._make_skill()
        percent = self._set_percent(
            skill, "it-IT",
            {"level": "medio", "utterance": "Imposta il volume a medio"},
        )
        self.assertEqual(percent, 0.7)

    def test_slot_nl_maximaal_resolves_max(self):
        skill = self._make_skill()
        percent = self._set_percent(
            skill, "nl-NL",
            {"level": "maximaal", "utterance": "zet het volume op maximaal"},
        )
        self.assertEqual(percent, 1.0)

    # previously-passing multi-word parity across locales, still holds
    def test_multiword_parity_across_locales(self):
        cases = [
            ("es-ES", "alto", "volumen alto", 0.9),
            ("es-ES", "bajo", "volumen bajo", 0.3),
            ("es-ES", "máximo", "volumen máximo", 1.0),
            ("es-ES", "medio", "volumen medio", 0.7),
            ("de-DE", "hoch", "Lautstärke hoch", 0.9),
            ("de-DE", "niedrig", "Lautstärke niedrig", 0.3),
            ("de-DE", "maximum", "Lautstärke auf maximum", 1.0),
            ("de-DE", "mittel", "Lautstärke auf mittel stellen", 0.7),
            ("it-IT", "alto", "Metti il volume alto", 0.9),
            ("it-IT", "basso", "Metti il volume basso", 0.3),
            ("it-IT", "massimo", "Volume massimo", 1.0),
            ("pt-BR", "alto", "volume alto", 0.9),
            ("pt-BR", "baixo", "volume baixo", 0.3),
            ("pt-BR", "máximo", "volume máximo", 1.0),
            ("pt-BR", "médio", "volume médio", 0.7),
        ]
        for lang, level, utterance, expected in cases:
            with self.subTest(lang=lang, level=level):
                skill = self._make_skill()
                percent = self._set_percent(
                    skill, lang, {"level": level, "utterance": utterance}
                )
                self.assertEqual(percent, expected)

    # change_volume.blacklist must not affect genuinely numeric amounts
    def test_change_volume_numeric_amount_still_works(self):
        skill = self._make_skill()
        message = Message(
            "change_volume.intent",
            {"utterance": "set volume to 40"},
            {"lang": "en-US"},
        )
        skill.handle_change_volume_intent(message)
        percent = None
        for call in skill.bus.emit.call_args_list:
            emitted = call.args[0]
            if emitted.msg_type == "mycroft.volume.set":
                percent = emitted.data["percent"]
        self.assertEqual(percent, 0.4)
