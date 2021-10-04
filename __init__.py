from os.path import dirname, join

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler, intent_file_handler
from mycroft.util import play_wav, normalize
from mycroft.util.parse import extract_number
from ovos_utils.sound.alsa import AlsaControl
from mycroft_bus_client import Message


class VolumeSkill(MycroftSkill):
    def __init__(self):
        super(VolumeSkill, self).__init__("VolumeSkill")
        self.volume_sound = join(dirname(__file__), "blop-mark-diangelo.wav")

    # bus api
    def initialize(self):
        self.add_event("mycroft.volume.get", self.handle_volume_request)
        self.add_event("mycroft.volume.set", self.handle_volume_change)
        self.add_event("mycroft.volume.set.gui",
                       self.handle_volume_change_gui)

        self.handle_volume_request(Message("mycroft.volume.get"))

    def handle_volume_request(self, message):
        percent = self.get_volume() / 100
        self.bus.emit(message.response({"percent": percent}))

    def handle_volume_change(self, message):
        percent = message.data["percent"] * 100
        self.set_volume(percent)

    def handle_volume_change_gui(self, message):
        percent = message.data["percent"] * 100
        self.set_volume_by_gui(percent)

    # volume control
    def get_intro_message(self):
        # just pretend this method is called "on_first_boot"
        # will only run once when the skill is loaded for the first time
        self.set_volume(50)

    def get_volume(self):
        return AlsaControl().get_volume_percent()

    def set_volume(self, percent=None):
        volume = int(percent)
        volume = min(100, volume)
        volume = max(0, volume)
        AlsaControl().set_volume_percent(volume)
        play_wav(self.volume_sound)

        # report change to GUI
        percent = volume / 100
        self.handle_volume_request(
            Message("mycroft.volume.get", {"percent": percent}))

    def set_volume_by_gui(self, percent=None):
        volume = int(percent)
        volume = min(100, volume)
        volume = max(0, volume)
        AlsaControl().set_volume_percent(volume)
        play_wav(self.volume_sound)

    def increase_volume(self, volume_change=None):
        if not volume_change:
            volume_change = 15
        AlsaControl().increase_volume(volume_change)
        play_wav(self.volume_sound)
        self.handle_volume_request(Message("mycroft.volume.get"))

    def decrease_volume(self, volume_change=None):
        if not volume_change:
            volume_change = -15
        if volume_change > 0:
            volume_change = 0 - volume_change
        AlsaControl().increase_volume(volume_change)
        play_wav(self.volume_sound)
        self.handle_volume_request(Message("mycroft.volume.get"))

    # intents
    @intent_handler(IntentBuilder("change_volume").require('change_volume'))
    def handle_change_volume_intent(self, message):
        utterance = message.data['utterance']
        volume_change = extract_number(normalize(utterance))
        self.set_volume(volume_change)
        if volume_change >= 100:
            self.speak_dialog('max.volume')
        else:
            self.speak_dialog('set.volume.percent',
                              data={'level': volume_change})

    @intent_handler(IntentBuilder("less_volume").require('less_volume'))
    def handle_less_volume_intent(self, message):
        utterance = message.data['utterance']
        volume_change = extract_number(normalize(utterance))
        if volume_change > 0:
            volume_change = 0 - volume_change
        self.decrease_volume(volume_change)

    @intent_handler(
        IntentBuilder("increase_volume").require('increase_volume'))
    def handle_increase_volume_intent(self, message):
        utterance = message.data['utterance']
        volume_change = extract_number(normalize(utterance))
        self.increase_volume(volume_change)

    @intent_file_handler('max_volume.intent')
    def handle_max_volume_intent(self, message):
        self.set_volume(100)
        self.speak_dialog('max.volume')

    @intent_file_handler('high_volume.intent')
    def handle_high_volume_intent(self, message):
        self.set_volume(85)

    @intent_file_handler('default_volume.intent')
    def handle_default_volume_ntent(self, message):
        self.set_volume(70)

    @intent_file_handler('low_volume.intent')
    def handle_low_volume_intent(self, message):
        self.set_volume(30)

    @intent_handler(IntentBuilder("current_volume").require('current_volume'))
    def handle_query_volume(self, message):
        volume = AlsaControl().get_volume()
        self.speak_dialog('volume.is', data={'volume': volume})


def create_skill():
    return VolumeSkill()
