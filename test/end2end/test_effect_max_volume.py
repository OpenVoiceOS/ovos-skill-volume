"""Effect-checking end-to-end coverage for ovos-skill-volume.

``test_golden_utterances.py`` only asserts that an utterance routed to the
expected intent -- a handler that matched and then did nothing would still
pass. This suite drives a real MiniCroft over a real bus and asserts the
consequence of ``handle_set_volume_level`` for the "max" level word: the
``mycroft.volume.set`` bus message the handler emits (with ``percent``
actually 1.0) and the ``volume.max`` dialog it speaks.

Also boots with it-IT active and drives the Italian "set volume to max"
phrasing, since the skill ships an it-IT locale (``locale/it-IT``) and a
default en-US boot only registers en-US intents.
"""
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-volume.openvoiceos"

_PIPELINE = [
    "ovos-adapt-pipeline-plugin-high",
    "ovos-padatious-pipeline-plugin-high",
    "ovos-padacioso-pipeline-plugin-high",
    "ovos-adapt-pipeline-plugin-medium",
    "ovos-padacioso-pipeline-plugin-medium",
    "ovos-adapt-pipeline-plugin-low",
]


def _drive(mc, utterance: str, lang: str, session_id: str):
    session = Session(session_id)
    session.lang = lang
    session.pipeline = list(_PIPELINE)
    session.blacklisted_intents = []
    msg = Message(
        "recognizer_loop:utterance",
        {"utterances": [utterance], "lang": lang},
        {"session": session.serialize(), "source": "A", "destination": "B"},
    )
    capture = CaptureSession(mc, eof_msgs=["ovos.utterance.handled"])
    capture.capture(msg, timeout=30)
    return capture.finish()


def _assert_max_volume_effect(messages, utterance):
    sets = [m for m in messages if m.msg_type == "mycroft.volume.set"]
    assert sets, f"{utterance!r}: no mycroft.volume.set emitted, got {[m.msg_type for m in messages]!r}"
    assert sets[0].data["percent"] == 1.0, (
        f"{utterance!r}: expected percent=1.0, got {sets[0].data!r}"
    )
    speaks = [m for m in messages if m.msg_type in ("speak", "ovos.utterance.speak")]
    assert speaks, f"{utterance!r}: no speak message emitted"
    assert speaks[0].data["meta"]["dialog"] == "volume.max", (
        f"{utterance!r}: expected dialog 'volume.max', got {speaks[0].data['meta']!r}"
    )


def test_set_volume_to_max_en_us():
    mc = get_minicroft([SKILL_ID])
    try:
        messages = _drive(mc, "set the volume to max", "en-US", "e2e-vol-max-en")
        _assert_max_volume_effect(messages, "set the volume to max")
    finally:
        mc.stop()


def test_set_volume_to_max_it_it():
    mc = get_minicroft([SKILL_ID], lang="it-IT")
    try:
        messages = _drive(mc, "imposta il volume al massimo", "it-IT", "e2e-vol-max-it")
        _assert_max_volume_effect(messages, "imposta il volume al massimo")
    finally:
        mc.stop()
