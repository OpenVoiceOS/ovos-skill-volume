"""da-DK lines follow the native review in PR #147: imperative "indstil", no duplicates."""
import json
from pathlib import Path

DA = Path(__file__).parents[2] / "locale/da-DK"


def test_volume_level_intent_has_reviewed_lines_once():
    lines = (DA / "volume_level.intent").read_text(encoding="utf-8").splitlines()
    assert "juster lydstyrken til <level>" in lines
    assert not [line for line in lines if "indstill " in line]
    assert len(lines) == len(set(lines))


def test_skill_json_examples_are_spelled_and_unique():
    examples = json.loads((DA / "skill.json").read_text(encoding="utf-8"))["examples"]
    assert not [e for e in examples if "indstill " in e]
    assert len(examples) == len(set(examples))
