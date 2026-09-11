"""No phrasing may newly land on two intents at once.

When one sentence expands out of two `.intent` files, padacioso has nothing to
choose between them and logs a tie; which handler runs is not defined. A locale
change is the easy way to create one, because a translator working from a
single file cannot see what its siblings already claim.

The ties that exist today are recorded in `known_intent_ties.json`. This
asserts the set never grows, so a change that adds one fails here rather than
in someone's living room. Removing a tie is expected and passes; the recorded
file is then trimmed in the same commit.
"""
import collections
import json
from pathlib import Path

import pytest

from ovos_spec_tools.expansion import expand

ROOT = Path(__file__).resolve().parents[2]
LOCALES = ROOT / "locale"
KNOWN = json.loads((Path(__file__).parent / "known_intent_ties.json").read_text(encoding="utf-8"))


def vocabularies(locale: Path) -> dict:
    out = {}
    for pattern in ("*.voc", "*.entity"):
        for f in locale.glob(pattern):
            out[f.stem] = [l.strip() for l in f.read_text(encoding="utf-8").splitlines()
                           if l.strip()]
    return out


def ties(locale: Path) -> dict:
    vocs = vocabularies(locale)
    claimed = collections.defaultdict(set)
    for f in sorted(locale.glob("*.intent")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                sentences = expand(line, vocs)
            except Exception:
                continue  # a malformed line is another test's business
            for s in sentences:
                claimed[s.strip().lower()].add(f.stem)
    return {s: sorted(v) for s, v in claimed.items() if len(v) > 1}


@pytest.mark.parametrize("locale", sorted(p.name for p in LOCALES.iterdir() if p.is_dir()))
def test_no_locale_gains_a_tie(locale):
    found = ties(LOCALES / locale)
    new = {s: v for s, v in found.items() if s not in KNOWN.get(locale, {})}
    assert not new, (
        f"{locale}: these phrasings now expand out of two intent files, and "
        f"padacioso cannot choose between them:\n  "
        + "\n  ".join(f"{s!r} -> {v}" for s, v in sorted(new.items())))
