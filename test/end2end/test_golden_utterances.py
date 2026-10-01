"""Golden-utterance end-to-end coverage for ovos-skill-volume (en-US).

The golden corpus (``golden_utterances.jsonl``) is a vendored slice of the
shared ovoscope golden-utterance dataset, keyed by
``skill_id == "ovos-skill-volume.openvoiceos"``. One shared ``MiniCroft``
(module-scoped fixture) is booted for the whole suite; every row is its own
parametrized test item.

Some volume handlers (eg. plain "change volume" with no target level) call
``get_response()`` for a follow-up, which deadlocks on a bare ``FakeBus``
(the upstream fix is in flight, see ovoscope#130). Following the same
mechanism as ``test_intents_en_us.py``, capture ends at
``mycroft.skill.handler.start`` (right after the intent binding fires, before
any handler body runs) rather than waiting for ``ovos.utterance.handled``, so
the intent-routing assertion under test never depends on the handler
finishing.
"""
import json
from pathlib import Path

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

GOLDEN_PATH = Path(__file__).parent / "golden_utterances.jsonl"

# utterances lifted verbatim from OTHER skills' golden-utterance slices,
# picked for lexical overlap with volume's "volume"/"mute"/"increase"/
# "decrease" vocabulary.
NEGATIVE_UTTERANCES = [
    ("play some music", "ovos-skill-music.openvoiceos"),
    ("pause the music", "ovos-skill-music.openvoiceos"),
    ("skip this song", "ovos-skill-music.openvoiceos"),
    ("turn up the brightness", "ovos-skill-homeassistant.openvoiceos"),
    ("increase the temperature", "ovos-skill-homeassistant.openvoiceos"),
    ("what's the weather", "ovos-skill-weather.openvoiceos"),
    ("set a timer for 5 minutes", "ovos-skill-alerts.openvoiceos"),
    ("set an alarm to maximum", "ovos-skill-alerts.openvoiceos"),
]


def _candidates(skill_id: str, intent_label: str) -> set:
    """Different padatious/padacioso plugin versions register the
    matched-intent bus event under different normalizations of the
    ``.intent`` filename basename -- observed variants include the bare
    basename with no extension (current OVOS-INTENT-2 naming, see
    ovos-skill-parrot#119) and the basename with the extension kept (older
    naming, still what ``test_intents_en_us.py`` asserts). ovos-padatious
    isn't installed in this environment (heavy native/swig dependency, see
    pyproject.toml's ``end2end`` extra comment) so padatious-high silently
    falls through to padacioso-high, which matches under the newer
    unsuffixed name -- candidates cover both so the suite isn't pinned to
    whichever pipeline plugin happens to be installed."""
    base = intent_label[:-len(".intent")] if intent_label.endswith(".intent") else intent_label
    return {f"{skill_id}:{intent_label}", f"{skill_id}:{base}"}


def _load_golden_rows():
    rows = []
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("needs_manual"):
                continue
            rows.append(row)
    return rows


# "volume change" carries no numeric amount, so handle_change_volume_intent
# falls into a get_response() follow-up (validated against a spoken number)
# once the handler body runs. get_response() can deadlock on a bare
# FakeBus/MiniCroft with no real STT round-trip -- upstream fix in flight,
# see ovoscope#130. This suite's capture already ends at
# "mycroft.skill.handler.start" (right after the intent binding fires, before
# the handler body/get_response ever runs -- see the module docstring), so
# the row itself does not observe that deadlock; no xfail is needed here.
# Defensive: give it a tighter per-row timeout than the suite default so
# that if some future environment's ordering of "mycroft.skill.handler.start"
# vs. get_response() differs and this DOES hang, it fails fast (20s) rather
# than consuming the full 60s suite timeout.
_ROW_TIMEOUTS = {
    "volume change": 20,
}


def _as_param(row):
    timeout = _ROW_TIMEOUTS.get(row["utterance"])
    marks = pytest.mark.timeout(timeout) if timeout else ()
    return pytest.param(row, id=row["utterance"], marks=marks)


GOLDEN_ROWS = [_as_param(r) for r in _load_golden_rows()]


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
    # End capture right after the intent binding fires (handler start) rather
    # than at ovos.utterance.handled: some handlers block on a follow-up
    # get_response, which never resolves on a bare MiniCroft/FakeBus. The
    # intent binding under test is emitted first, so this bounds each case
    # while still capturing what is asserted.
    capture = CaptureSession(
        mc,
        eof_msgs=["mycroft.skill.handler.start"],
        ignore_messages=_IGNORE,
    )
    capture.capture(utterance, timeout=30)
    return [m.msg_type for m in capture.finish()]


def _golden_id(row):
    return row["utterance"]


@pytest.mark.timeout(60)
@pytest.mark.parametrize("row", GOLDEN_ROWS, ids=_golden_id)
def test_golden_utterance(minicroft, row):
    candidates = _candidates(SKILL_ID, row["intent_label"])
    types = _types(minicroft, row["utterance"], f"golden-{_golden_id(row)}")
    assert any(t in candidates for t in types), (
        f"{row['utterance']!r}: expected one of {sorted(candidates)!r}, got {types!r}"
    )


@pytest.mark.timeout(60)
@pytest.mark.parametrize("negative", NEGATIVE_UTTERANCES, ids=lambda n: n[0])
def test_negative_confusable_not_claimed(minicroft, negative):
    text, source_skill = negative
    types = _types(minicroft, text, f"negative-{text}")
    claimed = any(t.startswith(f"{SKILL_ID}:") for t in types)
    assert not claimed, f"{text!r} (from {source_skill}) was incorrectly claimed by {SKILL_ID}"
