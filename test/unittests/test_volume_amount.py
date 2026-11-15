"""The amount is the number the user said, in every locale."""
from unittest.mock import Mock

import pytest
from ovos_bus_client.message import Message
from ovos_skill_volume import VolumeSkill


class VolumeHarness(VolumeSkill):
    def __init__(self, lang):
        self._harness_lang = lang
        self._bus = Mock()
        self.speak_dialog = Mock()
        self.get_response = Mock(side_effect=AssertionError("number already supplied"))
        self._query_volume = Mock(return_value=50)

    @property
    def lang(self):
        return self._harness_lang

    def __del__(self):
        pass


def emitted(skill):
    return [(m.msg_type, m.data) for m in
            (call.args[0] for call in skill._bus.emit.call_args_list)]


@pytest.mark.parametrize("lang, utterance, percent", [
    ("en-US", "set the volume to zero", 0.0),
    ("pt-PT", "põe o volume a vinte e cinco por cento", 0.25),
    ("pt-PT", "põe o volume nos setenta e cinco por cento", 0.75),
    ("pt-BR", "coloca o volume em vinte e cinco por cento", 0.25),
    ("fr-FR", "mets le volume à cinquante pour cent", 0.5),
    ("es-ES", "pon el volumen al veinticinco por ciento", 0.25),
    ("it-IT", "metti il volume al venticinque per cento", 0.25),
    ("gl-ES", "pon o volume ao vinte e cinco por cento", 0.25),
])
def test_change_volume_sets_the_spoken_amount(lang, utterance, percent):
    skill = VolumeHarness(lang)
    skill.handle_change_volume_intent(Message("change_volume.intent", {"utterance": utterance}))
    assert emitted(skill) == [("mycroft.volume.set", {"percent": percent})]


@pytest.mark.parametrize("handler, msg_type, utterance", [
    ("handle_increase_volume_intent", "mycroft.volume.increase", "sobe um pouco o volume"),
    ("handle_less_volume_intent", "mycroft.volume.decrease", "baixa um pouco o volume"),
])
def test_an_article_is_no_amount(handler, msg_type, utterance):
    # "um pouco" is "a little": no amount, so the step is the default 10
    skill = VolumeHarness("pt-PT")
    getattr(skill, handler)(Message("volume.intent", {"utterance": utterance}))
    assert emitted(skill) == [(msg_type, {"percent": 0.1})]
