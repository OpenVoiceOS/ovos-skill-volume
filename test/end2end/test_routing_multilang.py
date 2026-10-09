"""Multilingual routing and effect checks for ovos-skill-volume.

These tests run on the adapt and padacioso pipelines. Golden-row coverage
per locale lives in ``test_golden_utterances.py`` on the m2v pipeline.

One MiniCroft is booted per locale (lang=<locale>, no secondary_langs).
The tests cover three things: utterances in another language or from
another skill are not claimed, a numeric amount always resolves through
change_volume, and a level word sets the right percent.

Capture ends at ``mycroft.skill.handler.start`` for routing checks. A
handler that calls get_response() would wait for a reply that never comes
on a bare MiniCroft (ovoscope#130), so the ``_no_follow_up_prompt`` fixture
answers every follow-up prompt with None.
"""
import pytest
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovos_skill_volume import VolumeSkill
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-volume.openvoiceos"

_PIPELINE = [
    "ovos-adapt-pipeline-plugin-high",
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

# Cross-language negatives: an English utterance in a non-English session
# (and vice versa) must not match, and phrasing lifted from other skills'
# golden slices (by lexical overlap with volume vocabulary) must not be
# claimed either.
CROSS_LANG_NEGATIVES = [
    # (utterance, session_lang, why)
    ("max volume", "de-DE", "english utterance in a german session"),
    ("Lautstärke hoch", "en-US", "german utterance in an english session"),
    ("volumen alto", "fr-FR", "spanish utterance in a french session"),
    ("volume fort", "es-ES", "french utterance in a spanish session"),
    ("volume máximo", "en-US", "portuguese utterance in an english session"),
    ("mute", "pt-PT", "english utterance in a portuguese session"),
    ("play some music", "de-DE", "other-skill (music) phrasing, german session"),
    ("busca en duckduckgo Isaac Newton", "es-ES", "other-skill (ddg) phrasing, spanish session"),
    ("play some music", "en-US", "other-skill (music) phrasing"),
    ("pause the music", "en-US", "other-skill (music) phrasing"),
    ("skip this song", "en-US", "other-skill (music) phrasing"),
    ("turn up the brightness", "en-US", "other-skill (homeassistant) phrasing"),
    ("increase the temperature", "en-US", "other-skill (homeassistant) phrasing"),
    ("what's the weather", "en-US", "other-skill (weather) phrasing"),
    ("set a timer for 5 minutes", "en-US", "other-skill (alerts) phrasing"),
    ("set an alarm to maximum", "en-US", "other-skill (alerts) phrasing"),
]


def _candidates(skill_id: str, intent_label: str) -> set:
    """Padatious and padacioso plugin versions register the matched-intent
    bus event under the ``.intent`` basename with or without the extension."""
    base = intent_label[:-len(".intent")] if intent_label.endswith(".intent") else intent_label
    return {f"{skill_id}:{intent_label}", f"{skill_id}:{base}"}


_BOOTED = {}


@pytest.fixture(scope="module", autouse=True)
def _no_follow_up_prompt():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(VolumeSkill, "get_response", lambda self, *args, **kwargs: None)
        yield


@pytest.fixture(scope="module")
def mc_factory(request):
    """Boots one MiniCroft per locale on first use (lang=<locale>, no
    secondary_langs -- see ovos-skill-date-time/test/end2end/test_intents_it_it.py
    on dev), reusing it for every row/negative in that locale, and stops
    every booted instance at module teardown."""
    def _get(lang):
        if lang not in _BOOTED:
            mc = get_minicroft([SKILL_ID], max_wait=150, lang=lang)
            _BOOTED[lang] = mc
            request.addfinalizer(mc.stop)
        return _BOOTED[lang]
    return _get


def _types(mc, text, lang, session_id):
    session = Session(session_id)
    session.lang = lang
    session.pipeline = list(_PIPELINE)
    session.blacklisted_intents = []
    utterance = Message(
        "recognizer_loop:utterance",
        {"utterances": [text], "lang": lang},
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
@pytest.mark.parametrize("negative", CROSS_LANG_NEGATIVES, ids=lambda n: f"{n[1]}-{n[0]}")
def test_cross_language_negative(mc_factory, negative):
    text, lang, _why = negative
    mc = mc_factory(lang)
    types = _types(mc, text, lang, f"negative-{lang}-{text}")
    claimed = any(t.startswith(f"{SKILL_ID}:") for t in types)
    assert not claimed, f"[{lang}] {text!r} was incorrectly claimed by {SKILL_ID}"


# ---------------------------------------------------------------------------
# Percent-level assertions: the tests above only prove intent-name routing.
# volume_level.intent bakes its level word in as an inline <level> reference
# (a closed set of level.voc words), so a bare digit structurally cannot
# match it -- these rows close that gap by asserting the actual
# "mycroft.volume.set" percent, and that a numeric amount is never captured
# by volume_level and always resolves through change_volume instead. None of
# these rows ever reach a get_response() follow-up (change_volume always has
# an extractable number, volume_level never prompts), so capturing all the
# way to "mycroft.volume.set" is safe -- unlike the routing-only tests above,
# which stop at "mycroft.skill.handler.start" specifically to dodge that
# deadlock for ambiguous rows.
NUMERIC_ROWS = [
    ("it-IT", "imposta il volume a 40"),
    ("nl-NL", "zet het volume op 40"),
    ("de-DE", "stelle die Lautstärke auf 40"),
    ("en-US", "set volume to 40"),
]

LEVEL_PERCENT_ROWS = [
    ("es-ES", "volumen alto", 0.9),
    ("es-ES", "volumen bajo", 0.3),
    ("es-ES", "volumen máximo", 1.0),
    ("es-ES", "volumen medio", 0.7),
    ("de-DE", "Lautstärke hoch", 0.9),
    ("de-DE", "Lautstärke niedrig", 0.3),
    ("de-DE", "Lautstärke auf maximum", 1.0),
    ("it-IT", "Metti il volume alto", 0.9),
    ("it-IT", "Metti il volume basso", 0.3),
    ("it-IT", "Volume massimo", 1.0),
    ("it-IT", "Grida", 0.9),
    ("it-IT", "Imposta il volume a medio", 0.7),
    ("de-DE", "Standardlautstärke", 0.7),
    ("nl-NL", "standaardvolume", 0.7),
    ("nl-NL", "zet het volume op maximaal", 1.0),
    ("en-US", "set the volume to high", 0.9),
    ("en-US", "set the volume to low", 0.3),
    ("en-US", "set the volume to max", 1.0),
    ("en-US", "set the volume to normal", 0.7),
]


def _percent_for(mc, text, lang, session_id):
    session = Session(session_id)
    session.lang = lang
    session.pipeline = list(_PIPELINE)
    session.blacklisted_intents = []
    utterance = Message(
        "recognizer_loop:utterance",
        {"utterances": [text], "lang": lang},
        {"session": session.serialize(), "source": "A", "destination": "B"},
    )
    capture = CaptureSession(
        mc,
        eof_msgs=["mycroft.volume.set"],
        ignore_messages=[m for m in _IGNORE if m != "mycroft.volume.set"],
    )
    capture.capture(utterance, timeout=30)
    msgs = capture.finish()
    types = [m.msg_type for m in msgs]
    percent = None
    claimed_volume_level = False
    for m in msgs:
        if m.msg_type == "mycroft.volume.set":
            percent = m.data.get("percent")
        if m.msg_type in _candidates(SKILL_ID, "volume_level.intent"):
            claimed_volume_level = True
    return types, percent, claimed_volume_level


@pytest.mark.timeout(60)
@pytest.mark.parametrize("case", NUMERIC_ROWS, ids=lambda c: f"{c[0]}-{c[1]}")
def test_numeric_amount_never_claimed_by_volume_level(mc_factory, case):
    lang, text = case
    mc = mc_factory(lang)
    for _trial in range(3):
        types, percent, claimed_volume_level = _percent_for(
            mc, text, lang, f"numeric-{lang}-{text}-{_trial}"
        )
        assert not claimed_volume_level, (
            f"[{lang}] {text!r} was claimed by volume_level.intent instead of change_volume "
            f"(got {types!r})"
        )
        assert percent == pytest.approx(0.4), (
            f"[{lang}] {text!r}: expected mycroft.volume.set percent=0.4, got {percent!r} (types={types!r})"
        )


@pytest.mark.timeout(60)
@pytest.mark.parametrize("case", LEVEL_PERCENT_ROWS, ids=lambda c: f"{c[0]}-{c[1]}")
def test_level_word_sets_correct_percent(mc_factory, case):
    lang, text, expected = case
    mc = mc_factory(lang)
    types, percent, claimed_volume_level = _percent_for(mc, text, lang, f"percent-{lang}-{text}")
    assert claimed_volume_level, (
        f"[{lang}] {text!r}: a level word must be claimed by volume_level.intent, not lost to "
        f"change_volume's {{amount}} slot (got {types!r})"
    )
    assert percent == pytest.approx(expected), (
        f"[{lang}] {text!r}: expected mycroft.volume.set percent={expected!r}, got {percent!r} "
        f"(types={types!r})"
    )

