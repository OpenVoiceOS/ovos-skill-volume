"""Every dialog the code speaks resolves to a file in every shipped locale.

A ``speak_dialog("name")`` whose ``name.dialog`` is missing in a locale
makes the skill speak the literal name aloud in that locale. The
end-to-end suites did not see it: with an en-US dialog renamed away from
the name the code speaks, this skill's suite stayed fully green, because
those tests assert routing and message counts, not what resolved. This
is the check that fails on a rename mistake.

Read from the source with ``ast``: every call named ``speak_dialog``
whose first argument is a string literal. A call whose name is built at
runtime cannot be checked here and is counted, so the number of names
this test covers is visible and a drop in it is a regression of the
test, not of the skill.

For each spoken name and each locale directory that ships any
``.dialog`` file, ``<name>.dialog`` must exist (at the locale root or
under ``dialog/``, both layouts the resource loader reads). Every slot
the en-US file renders must be in every other locale's file too, or that
locale speaks a sentence with the value missing. A key the code passes
that en-US itself never renders is not a locale defect and is not
checked here; it is dead data at the call site.
"""
import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LOCALE = next(p for p in (ROOT / "locale", *ROOT.glob("*/locale")) if p.is_dir())
SOURCES = sorted(p for p in ROOT.rglob("*.py")
                 if ".venv" not in p.parts and "test" not in p.parts and "tests" not in p.parts)
SLOT = re.compile(r"\{(\w+)\}")


def _spoken() -> tuple:
    """(name -> set of slot keys passed), and the count of dynamic calls."""
    names, dynamic = {}, 0
    for source in SOURCES:
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "speak_dialog" and node.args):
                continue
            first = node.args[0]
            if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
                dynamic += 1
                continue
            slots = set()
            data = node.args[1] if len(node.args) > 1 else next(
                (kw.value for kw in node.keywords if kw.arg == "data"), None)
            if isinstance(data, ast.Dict):
                slots = {k.value for k in data.keys if isinstance(k, ast.Constant)}
            names.setdefault(first.value, set()).update(slots)
    return names, dynamic


SPOKEN, DYNAMIC = _spoken()
LOCALES = sorted(p.name for p in LOCALE.iterdir()
                 if p.is_dir() and any(p.rglob("*.dialog")))


def _dialog_file(lang: str, name: str):
    for candidate in (LOCALE / lang / f"{name}.dialog", LOCALE / lang / "dialog" / f"{name}.dialog"):
        if candidate.is_file():
            return candidate
    return None


def test_the_source_speaks_dialogs_this_test_can_see():
    """The control on the scan: names were found, and the dynamic count is
    what it is today. Raise the second number only with a reason."""
    assert SPOKEN, "no speak_dialog with a literal name found; the scan is stale"
    assert DYNAMIC == 0, f"{DYNAMIC} speak_dialog calls build their name at runtime and are unchecked"


@pytest.mark.parametrize("lang", LOCALES)
def test_every_spoken_dialog_resolves_in_the_locale(lang):
    missing = sorted(name for name in SPOKEN if _dialog_file(lang, name) is None)
    assert not missing, (
        f"{lang}: the code speaks {missing} and the locale ships no such file, "
        f"so the skill would speak the literal name")


@pytest.mark.parametrize("lang", LOCALES)
def test_every_slot_the_reference_renders_is_in_the_locale_file(lang):
    holes = []
    for name, slots in SPOKEN.items():
        path = _dialog_file(lang, name)
        reference = _dialog_file("en-US", name)
        if path is None or reference is None or not slots:
            continue
        rendered = {s for s in slots if f"{{{s}}}" in reference.read_text(encoding="utf-8")}
        lines = [l for l in path.read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.startswith("#")]
        for slot in sorted(rendered):
            if not any(f"{{{slot}}}" in l for l in lines):
                holes.append(f"{name}.dialog lacks {{{slot}}}")
    assert not holes, f"{lang}: {holes}"
