import unittest
from os.path import dirname

from ovos_plugin_manager.skills import find_skill_plugins
from ovos_utils.messagebus import FakeBus

from ovos_skill_volume import VolumeSkill


class TestSkillLoading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_id = "ovos-skill-volume.openvoiceos"
        cls.path = dirname(dirname(dirname(__file__)))

    def test_from_class(self):
        bus = FakeBus()
        skill = VolumeSkill()
        skill._startup(bus, self.skill_id)
        self.assertEqual(skill.bus, bus)
        self.assertEqual(skill.skill_id, self.skill_id)

    def test_from_plugin(self):
        bus = FakeBus()
        for skill_id, plug in find_skill_plugins().items():
            if skill_id == self.skill_id:
                skill = plug()
                skill._startup(bus, self.skill_id)
                self.assertEqual(skill.bus, bus)
                self.assertEqual(skill.skill_id, self.skill_id)
                break
        else:
            raise RuntimeError("plugin not found")
