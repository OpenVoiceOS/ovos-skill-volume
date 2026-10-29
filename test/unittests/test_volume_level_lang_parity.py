"""Regression tests for the volume_level lang-parity migration.

volume_level.intent's level word is an inline ``<level>`` reference to
level.voc (baked into the template as a literal alternation, no slot at
all), so a bare digit structurally cannot match this intent -- a numeric
utterance like "imposta il volume a 40" falls through to
change_volume.intent instead. This closes both regressions the live gate
caught on the previous {level}-slot design: a genuine numeric amount
could be captured by volume_level's own slot and silently fail to
resolve any level voc (no percent ever set), and a plain level word like
"medio"/"maximaal" could lose the classification race to
change_volume.intent's near-identical {level}-slot template for
amounts.

Bare level words (it-IT "Grida", de-DE "Standardlautstärke", nl-NL
"standaardvolume") are literal-only volume_level.intent training lines
with no slot either; handle_set_volume_level resolves the level by
voc_match'ing the whole utterance, not any slot.

These tests exercise handle_set_volume_level and
handle_change_volume_intent directly against a FakeBus, asserting the
actual "mycroft.volume.set" percent emitted -- the layer where the bug
actually lived, since intent-routing alone (asserted by the end2end
golden-utterance suite) does not prove the handler resolved the correct
percent.
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
        skill.get_response = MagicMock(return_value=None)
        return skill

    def _percent_set(self, skill):
        for call in skill.bus.emit.call_args_list:
            emitted = call.args[0]
            if emitted.msg_type == "mycroft.volume.set":
                return emitted.data["percent"]
        return None

    def _set_level(self, skill, lang, utterance):
        message = Message("volume_level.intent", {"utterance": utterance}, {"lang": lang})
        skill.handle_set_volume_level(message)
        return self._percent_set(skill)

    def _change_volume(self, skill, lang, utterance):
        message = Message("change_volume.intent", {"utterance": utterance}, {"lang": lang})
        skill.handle_change_volume_intent(message)
        return self._percent_set(skill)

    # bare level words: literal-only training lines, no slot at all
    def test_bare_word_it_grida_resolves_high(self):
        skill = self._make_skill()
        self.assertEqual(self._set_level(skill, "it-IT", "Grida"), 0.9)

    def test_bare_word_it_urla_resolves_high(self):
        skill = self._make_skill()
        self.assertEqual(self._set_level(skill, "it-IT", "Urla"), 0.9)

    def test_bare_word_it_sussurra_resolves_low(self):
        skill = self._make_skill()
        self.assertEqual(self._set_level(skill, "it-IT", "Sussurra"), 0.3)

    def test_bare_word_de_standardlautstaerke_resolves_default(self):
        skill = self._make_skill()
        self.assertEqual(self._set_level(skill, "de-DE", "Standardlautstärke"), 0.7)

    def test_bare_word_nl_standaardvolume_resolves_default(self):
        skill = self._make_skill()
        self.assertEqual(self._set_level(skill, "nl-NL", "standaardvolume"), 0.7)

    # plain level-word utterances that used to lose the classification race
    # to change_volume.intent's {level} slot (now moot: change_volume is
    # exercised directly here, volume_level never even sees these through
    # its own {level} slot anymore since it no longer has one)
    def test_slot_it_medio_resolves_default(self):
        skill = self._make_skill()
        self.assertEqual(
            self._set_level(skill, "it-IT", "Imposta il volume a medio"), 0.7
        )

    def test_slot_nl_maximaal_resolves_max(self):
        skill = self._make_skill()
        self.assertEqual(
            self._set_level(skill, "nl-NL", "zet het volume op maximaal"), 1.0
        )

    # previously-passing multi-word parity across locales, still holds
    def test_multiword_parity_across_locales(self):
        cases = [
            ("es-ES", "volumen alto", 0.9),
            ("es-ES", "volumen bajo", 0.3),
            ("es-ES", "volumen máximo", 1.0),
            ("es-ES", "volumen medio", 0.7),
            ("de-DE", "Lautstärke hoch", 0.9),
            ("de-DE", "Lautstärke niedrig", 0.3),
            ("de-DE", "Lautstärke auf maximum", 1.0),
            ("de-DE", "Lautstärke auf mittel stellen", 0.7),
            ("it-IT", "Metti il volume alto", 0.9),
            ("it-IT", "Metti il volume basso", 0.3),
            ("it-IT", "Volume massimo", 1.0),
            ("pt-BR", "volume alto", 0.9),
            ("pt-BR", "volume baixo", 0.3),
            ("pt-BR", "volume máximo", 1.0),
            ("pt-BR", "volume médio", 0.7),
        ]
        for lang, utterance, expected in cases:
            with self.subTest(lang=lang, utterance=utterance):
                skill = self._make_skill()
                self.assertEqual(self._set_level(skill, lang, utterance), expected)

    # THE regression the live gate rejected: a numeric amount must never be
    # captured by volume_level (no slot to capture it into in the first
    # place) and must resolve through change_volume instead
    def test_numeric_amount_routes_through_change_volume(self):
        cases = [
            ("it-IT", "imposta il volume a 40"),
            ("nl-NL", "zet het volume op 40"),
            ("de-DE", "stelle die Lautstärke auf 40"),
            ("en-US", "set volume to 40"),
        ]
        for lang, utterance in cases:
            for _trial in range(3):
                with self.subTest(lang=lang, utterance=utterance):
                    skill = self._make_skill()
                    self.assertEqual(self._change_volume(skill, lang, utterance), 0.4)
