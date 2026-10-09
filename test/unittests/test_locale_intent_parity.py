"""Every locale ships every intent file that en-US ships.

A missing ``.intent`` file removes the intent from that locale. The golden
test cannot see this for an intent listed in its gap tables, so this static
check fails on a missing file whatever the gap tables hold.
"""
from pathlib import Path

import pytest

LOCALE_DIR = Path(__file__).parents[2] / "locale"
REFERENCE = "en-US"
INTENTS = sorted(path.name for path in (LOCALE_DIR / REFERENCE).glob("*.intent"))
LOCALES = sorted(path.name for path in LOCALE_DIR.iterdir() if path.is_dir())


def test_reference_locale_has_intents():
    assert len(INTENTS) == 10, INTENTS


@pytest.mark.parametrize("lang", LOCALES)
def test_locale_ships_every_reference_intent(lang):
    present = {path.name for path in (LOCALE_DIR / lang).glob("*.intent")}
    missing = [name for name in INTENTS if name not in present]
    assert not missing, f"[{lang}] missing intent files: {missing}"
