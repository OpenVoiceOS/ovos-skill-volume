"""Guard for the rule PR OpenVoiceOS/ovos-skill-volume#131 established:
``louder.voc``/``quieter.voc`` carry only comparative or imperative words.
They must never carry a bare word that also appears, unmodified, as the
literal wording of ``volume.high.intent``/``volume.low.intent`` or
``volume_level.intent``'s level vocabularies -- doing so lets the relative
increase/decrease intent claim an utterance that names an absolute level.

This guard was originally an intent-routing test: with
``ovos-skill-volume``'s increase_volume/less_volume intents built from
Adapt keywords (``IntentBuilder(...).require("louder").require("volume")``),
a stray bare word in ``louder.voc``/``quieter.voc`` measurably changed which
intent an utterance matched. OpenVoiceOS/ovos-skill-volume#133 migrated
those intents to literal padatious/padacioso templates that never read
``louder.voc``/``quieter.voc`` at all, so a routing test can no longer see
the difference -- reproduced across all five locales below (a probe
utterance for each locale matches the identical intent whether the word is
present or absent in the file). Until the intents read these files again,
a direct content check is the only mechanism that can still fail when the
rule is broken.
"""
import unittest
from os.path import dirname, join

LOCALE_DIR = join(dirname(dirname(dirname(__file__))), "locale")

# (locale, vocab filename, forbidden word, why it must not be here)
FORBIDDEN = [
    ("nl-NL", "louder.voc", "hoog",
     "bare absolute 'high', duplicates volume.high.intent/level.high.voc wording"),
    ("pt-PT", "quieter.voc", "baixo",
     "bare absolute 'low', duplicates volume.low.intent/level.low.voc wording"),
    ("ca-ES", "louder.voc", "alt",
     "bare absolute 'high', duplicates volume.high.intent/level.high.voc wording"),
    ("fr-FR", "louder.voc", "augmente",
     "duplicates the literal first word of volume.high.intent's "
     "'augmente le volume' line"),
    ("fr-FR", "quieter.voc", "baisse",
     "duplicates the literal first word of volume.low.intent's "
     "'baisse le volume' line"),
    ("it-IT", "louder.voc", "alza",
     "duplicates the literal first word of volume.high.intent's "
     "'Alza il volume' line"),
    ("it-IT", "quieter.voc", "abbassa",
     "duplicates the literal first word of volume.low.intent's "
     "'Abbassa il volume' line"),
]


class TestRelativeVocabNoAbsoluteWords(unittest.TestCase):
    def test_louder_quieter_voc_excludes_absolute_words(self):
        for lang, filename, word, reason in FORBIDDEN:
            with self.subTest(lang=lang, filename=filename, word=word):
                path = join(LOCALE_DIR, lang, filename)
                with open(path, encoding="utf-8") as f:
                    lines = [ln.strip() for ln in f if ln.strip()]
                self.assertNotIn(
                    word, lines,
                    f"{lang}/{filename} carries '{word}': {reason}. "
                    f"Restore the fix from OpenVoiceOS/ovos-skill-volume#131.",
                )
