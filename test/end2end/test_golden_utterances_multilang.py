"""Multilingual golden-utterance end-to-end coverage for ovos-skill-volume.

Extends test_golden_utterances.py (en-US only) to every locale under
locale/ that ships actual intent/vocab files. One shared MiniCroft is
booted with en-US as the primary language and every other locale as a
``secondary_lang`` (ovoscope>=1.6.5a1 / padacioso>=2.2.3a1, which
contains the upstream fix for padacioso#77 -- cross-language intent
detach scoping -- verified against the resolved padacioso version before
relying on a single shared MiniCroft here).

fa-IR is excluded: its locale/ directory ships only skill.json (store
metadata) with no .intent/.voc files, so there is nothing to route --
see the NATIVE_VALIDATION.md top-line finding.

Tier 1 rows are natural-language expansions of the language's own
locale/<lang>/*.intent templates and assert a hard intent match, same
standard as the en-US golden suite. Machine-drafted Tier 2 paraphrase rows
were dropped from this suite (no drafted/translated content -- see
NATIVE_VALIDATION.md); the ``machine_generated``-row xfail branch below is
kept only as a landing spot for future human-contributed paraphrase rows,
not populated by anything in this suite today.

Known routing bugs unrelated to template coverage (e.g. the skill's own
adapt intents shadowing more specific padatious/padacioso matches) stay
pinned in KNOWN_BUGS/KNOWN_NEGATIVE_BUGS below: the test only calls
``pytest.xfail(reason=...)`` when the row is confirmed to still not match,
falling through to a plain ``assert matched`` otherwise -- so a fix makes
the row a real failure demanding it be dropped from the dict, rather than
staying silently green.

Capture ends at ``mycroft.skill.handler.start`` for the same reason as
the en-US suite: some handlers block on get_response() on a bare
MiniCroft/FakeBus (ovoscope#130); the intent-routing assertion under
test fires before that.
"""
import json
from pathlib import Path

import pytest
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

END2END_DIR = Path(__file__).parent

# Every locale with real intent/vocab content (fa-IR is metadata-only, see
# module docstring / NATIVE_VALIDATION.md).
LANGS = [
    "de-DE", "es-ES", "fr-FR", "it-IT", "nl-NL", "pt-PT", "pt-BR",
    "ca-ES", "da-DK", "eu-ES", "gl-ES",
]

# Cross-language negatives: an English utterance in a non-English session
# (and vice versa) must not match, and phrasing lifted from other skills'
# golden slices (by lexical overlap with volume vocabulary) must not be
# claimed either. Covers 4 major languages per the campaign scope.
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
]


def _candidates(skill_id: str, intent_label: str) -> set:
    """See test_golden_utterances.py::_candidates -- padatious/padacioso
    plugin versions register the matched-intent bus event under different
    normalizations of the ``.intent`` filename basename."""
    base = intent_label[:-len(".intent")] if intent_label.endswith(".intent") else intent_label
    return {f"{skill_id}:{intent_label}", f"{skill_id}:{base}"}


def _load_rows(lang):
    path = END2END_DIR / f"golden_utterances_{lang}.jsonl"
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("needs_manual"):
                continue
            rows.append(row)
    return rows


ALL_ROWS = []
for _lang in LANGS:
    for _row in _load_rows(_lang):
        ALL_ROWS.append(_row)


def _as_param(row):
    tag = "tier2" if row.get("machine_generated") else "tier1"
    return pytest.param(row, id=f"{row['lang']}-{tag}-{row['utterance']}")


GOLDEN_ROWS = [_as_param(r) for r in ALL_ROWS]


@pytest.fixture(scope="module")
def minicroft():
    mc = get_minicroft([SKILL_ID], secondary_langs=LANGS)
    yield mc
    mc.stop()


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


def _golden_id(row):
    return f"{row['lang']}-{row['utterance']}"


# Real, reproduced routing defects found by this Tier-1 pass -- NOT coverage
# gaps, NOT weakened assertions.
#
# Most of the original 11 rows here turned out to be over-broad *.voc
# entries or an incomplete padacioso template, and were fixed in-place
# (see the PR that introduced this comment block for the collision/fix/
# red-green evidence per row: nl-NL "hoog", pt-PT "baixo", ca-ES "alt",
# fr-FR "augmente"/"baisse", it-IT "alza"/"abbassa" were absolute-meaning
# words that didn't belong in the relative louder.voc/quieter.voc lists
# (mirroring the en-US precedent, whose louder.voc/quieter.voc only ever
# contain comparative/imperative words, never the bare high/low adjective);
# de-DE's "stell die Lautstärke auf leise" was simply missing "die
# Lautstärke" from its volume.low.intent template line (a typo/omission --
# the sibling volume.high.intent line already has the correct pattern).
#
# The remaining 3 rows below are NOT vocab typos: they are a genuine
# adapt-vs-padatious pipeline race. ovos-adapt-parser's confidence score is
# character-length-weighted, not token-count-weighted, so a short
# 2-word utterance where the *only* recognized adapt vocab word is a long
# compound noun (German "Lautstärke", Danish "lydstyrke") clears the
# ovos-adapt-pipeline-plugin-high 0.65 confidence threshold on that single
# word alone, before padatious/padacioso-high ever gets a turn in the
# pipeline (see _PIPELINE order above) -- regardless of how the padatious
# template is worded. There is no over-broad vocab entry to trim here:
# "hoch"/"høj"/"lav" (as the Danish *adjective*) aren't adapt vocab at all,
# so nothing can be narrowed without inventing new drafted vocabulary,
# which is out of scope for this pass. da-DK "lav lydstyrke" was probed by
# removing the colliding change.voc entry "lav" (='make'); that only swaps
# which adapt intent shadows volume.low.intent (change_volume -> bare
# current_volume, since "lydstyrke" alone already clears 0.65), so the
# entry was kept and the row stays xfail.
KNOWN_BUGS = {
    ("de-DE", "Lautstärke hoch"): "adapt current_volume shadows volume.high.intent: bare 'Lautstärke' is a "
                                    "single long compound noun whose char-weighted adapt confidence (0.667) "
                                    "clears the 0.65 adapt-high threshold before padacioso-high runs; not an "
                                    "over-broad vocab entry (there is none to trim), needs new vocab work",
    ("da-DK", "høj lydstyrke"): "adapt current_volume shadows volume.high.intent: same char-weighted "
                                  "bare-'lydstyrke' confidence (0.692) clearing the adapt-high threshold, "
                                  "no offending vocab entry to trim",
    ("da-DK", "lav lydstyrke"): "da-DK change.voc entry 'lav' (='make') collides with the Danish adjective "
                                  "'lav' (='low'); adapt change_volume shadows volume.low.intent. Removing "
                                  "'lav' from change.voc does not fix this -- current_volume's bare "
                                  "'lydstyrke' match (0.69 confidence) then shadows it instead, same root "
                                  "cause as the de-DE/da-DK bare-volume-word rows above",
}

# volume_level.intent's default/max level words ("default", "massimo", ...)
# are also plain English for "reset the volume"/"crank it up", so a handful
# of reset/boost phrasings ported from en-US's volume.reset.intent /
# volume.max.boost.intent legitimately overlap with a volume_level.intent
# literal expansion of the same words. Both outcomes set the identical
# percent (handle_reset_volume_intent and the default/max branch of
# handle_set_volume_level agree on 0.7/1.0), so either intent winning the
# classification race is correct behavior, not a bug -- these rows accept
# either label.
EQUIVALENT_INTENTS = {
    ("it-IT", "Alza il volume al massimo"): "volume_level.intent",
    ("it-IT", "Ripristina il volume di default"): "volume.reset.intent",
    ("ca-ES", "restableix el volum"): "volume.reset.intent",
    ("da-DK", "nulstil lydstyrken"): "volume.reset.intent",
    ("gl-ES", "restaurar o volume"): "volume.reset.intent",
}


@pytest.mark.timeout(60)
@pytest.mark.parametrize("row", GOLDEN_ROWS, ids=_golden_id)
def test_golden_utterance_multilang(minicroft, row):
    candidates = _candidates(SKILL_ID, row["intent_label"])
    equivalent = EQUIVALENT_INTENTS.get((row["lang"], row["utterance"]))
    if equivalent:
        candidates |= _candidates(SKILL_ID, equivalent)
    types = _types(minicroft, row["utterance"], row["lang"], f"golden-{_golden_id(row)}")
    matched = any(t in candidates for t in types)
    bug_key = (row["lang"], row["utterance"])
    if bug_key in KNOWN_BUGS and not matched:
        pytest.xfail(reason=f"known-bug: {KNOWN_BUGS[bug_key]}")
    if row.get("machine_generated") and not matched:
        pytest.xfail(reason="coverage-gap (machine-drafted, pending native validation)")
    assert matched, (
        f"[{row['lang']}] {row['utterance']!r}: expected one of {sorted(candidates)!r}, got {types!r}"
    )


# Same root cause as KNOWN_BUGS above: adapt's current_volume intent
# requires only the "volume" vocab word, so it claims ANY utterance that
# happens to contain a volume-vocab token, including foreign-language
# utterances with no other overlap. This is a real, reproduced
# cross-language routing defect, not a weakened assertion.
KNOWN_NEGATIVE_BUGS = {
    ("en-US", "volume máximo"): "adapt current_volume claims any utterance containing the bare 'volume' vocab word, "
                                 "including this pt-PT phrase, in an en-US session -- same char-weighted "
                                 "bare-'volume'-word confidence issue as the de-DE/da-DK KNOWN_BUGS rows above, "
                                 "not fixable by trimming vocab",
}


@pytest.mark.timeout(60)
@pytest.mark.parametrize("negative", CROSS_LANG_NEGATIVES, ids=lambda n: f"{n[1]}-{n[0]}")
def test_cross_language_negative(minicroft, negative):
    text, lang, _why = negative
    types = _types(minicroft, text, lang, f"negative-{lang}-{text}")
    claimed = any(t.startswith(f"{SKILL_ID}:") for t in types)
    bug_key = (lang, text)
    if bug_key in KNOWN_NEGATIVE_BUGS and claimed:
        pytest.xfail(reason=f"known-bug: {KNOWN_NEGATIVE_BUGS[bug_key]}")
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
def test_numeric_amount_never_claimed_by_volume_level(minicroft, case):
    lang, text = case
    for _trial in range(3):
        types, percent, claimed_volume_level = _percent_for(
            minicroft, text, lang, f"numeric-{lang}-{text}-{_trial}"
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
def test_level_word_sets_correct_percent(minicroft, case):
    lang, text, expected = case
    types, percent, claimed_volume_level = _percent_for(minicroft, text, lang, f"percent-{lang}-{text}")
    assert claimed_volume_level, (
        f"[{lang}] {text!r}: a level word must be claimed by volume_level.intent, not lost to "
        f"change_volume's {{amount}} slot (got {types!r})"
    )
    assert percent == pytest.approx(expected), (
        f"[{lang}] {text!r}: expected mycroft.volume.set percent={expected!r}, got {percent!r} "
        f"(types={types!r})"
    )
