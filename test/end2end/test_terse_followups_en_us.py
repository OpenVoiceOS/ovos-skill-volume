"""End-to-end coverage for the terse, object-less follow-up phrasings added
in OpenVoiceOS/ovos-skill-volume#135 (eg. "make it louder", "mute it for a
second") that lack the word "volume" and previously fell through to
fallback. Mirrors the harness in test_intents_en_us.py.

Alongside the new positives, this asserts a set of media/OCP-flavored
confusables are NOT claimed by this skill -- the new lines are anchored on
the "it" object pronoun specifically so that phrasings naming an explicit
target ("the music", "the song") stay out of scope.
"""
import pytest
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

POSITIVE_ROWS = [
    ("make it louder", "increase_volume"),
    ("turn it back up", "increase_volume"),
    ("crank it up", "increase_volume"),
    ("louder please", "increase_volume"),
    ("turn it way up", "increase_volume"),
    ("make it quieter", "less_volume"),
    ("turn it back down", "less_volume"),
    ("lower it please", "less_volume"),
    ("quieter please", "less_volume"),
    ("turn it way down", "less_volume"),
    ("mute it for a second", "volume.mute"),
    ("mute it for a bit", "volume.mute"),
    ("mute it for a minute", "volume.mute"),
    ("unmute it now", "volume.unmute"),
    ("put it back to normal", "volume.default"),
    ("put it back to default", "volume.default"),
]

# "turn it up" is accepted as this skill's own by design (#135); it is not a
# negative case even though "it" is ambiguous outside of a follow-up context.
ACCEPTED_BY_DESIGN = [
    ("turn it up", "increase_volume"),
]

# media/OCP-flavored confusables that name an explicit target rather than
# the bare "it" pronoun -- these must stay out of scope for this skill.
NEGATIVE_UTTERANCES = [
    "turn up the music",
    "play it louder",
    "turn the music up",
    "play the song louder",
    "crank up the music",
]


@pytest.fixture(scope="module")
def minicroft():
    mc = get_minicroft([SKILL_ID])
    yield mc
    mc.stop()


def _types(mc, text, session_id):
    session = Session(session_id)
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
    capture = CaptureSession(
        mc,
        eof_msgs=["mycroft.skill.handler.start"],
        ignore_messages=_IGNORE,
    )
    capture.capture(utterance, timeout=30)
    return [m.msg_type for m in capture.finish()]


@pytest.mark.timeout(60)
@pytest.mark.parametrize("row", POSITIVE_ROWS + ACCEPTED_BY_DESIGN, ids=lambda r: r[0])
def test_terse_followup_routes_to_intent(minicroft, row):
    text, intent = row
    types = _types(minicroft, text, f"terse-{text}")
    assert f"{SKILL_ID}:{intent}" in types, f"{text!r}: expected {intent!r}, got {types!r}"


@pytest.mark.timeout(60)
@pytest.mark.parametrize("text", NEGATIVE_UTTERANCES)
def test_media_confusable_not_claimed(minicroft, text):
    types = _types(minicroft, text, f"terse-negative-{text}")
    claimed = any(t.startswith(f"{SKILL_ID}:") for t in types)
    assert not claimed, f"{text!r} was incorrectly claimed by {SKILL_ID}: {types!r}"
