from ovos_number_parser import extract_number
from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements
from ovos_utterance_normalizer import UtteranceNormalizerPlugin
from ovos_workshop.decorators import intent_handler
from ovos_workshop.intents import IntentBuilder
from ovos_workshop.skills import OVOSSkill

MIN_VOLUME = 0
MAX_VOLUME = 100


class VolumeSkill(OVOSSkill):
    @classproperty
    def runtime_requirements(self):
        return RuntimeRequirements(internet_before_load=False,
                                   network_before_load=False,
                                   gui_before_load=False,
                                   requires_internet=False,
                                   requires_network=False,
                                   requires_gui=False,
                                   no_internet_fallback=True,
                                   no_network_fallback=True,
                                   no_gui_fallback=True)

    def _query_volume(self, message):
        response = self.bus.wait_for_response(message.forward("mycroft.volume.get"))
        if response:
            return int(response.data["percent"] * 100)
        else:
            self.speak_dialog("error.get.volume")
            raise TimeoutError("Failed to get volume")

    # intents
    @intent_handler(IntentBuilder("change_volume").require("change").require("volume"))
    def handle_change_volume_intent(self, message):
        normalizer = UtteranceNormalizerPlugin.get_normalizer(self.lang)
        utt = normalizer.normalize(message.data["utterance"])
        volume_change = extract_number(utt, lang=self.lang)
        if not volume_change:

            def amount_validator(response):
                response = normalizer.normalize(response)
                amount = extract_number(response, lang=self.lang)
                if amount:
                    return MIN_VOLUME <= amount <= MAX_VOLUME
                return None

            response = self.get_response(
                "volume.change.amount", validator=amount_validator
            )
            volume_change = extract_number(normalizer.normalize(response), lang=self.lang)
        if volume_change >= 100:
            self.speak_dialog("volume.max")
        else:
            self.speak_dialog("volume.set.percent", data={"level": int(volume_change)})
        self.bus.emit(
            message.forward("mycroft.volume.set", {"percent": volume_change / 100})
        )

    @intent_handler(
        IntentBuilder("less_volume").require("quieter").require("volume")
    )
    def handle_less_volume_intent(self, message):
        normalizer = UtteranceNormalizerPlugin.get_normalizer(self.lang)
        utt = normalizer.normalize(message.data["utterance"])
        volume = self._query_volume(message)
        volume_change = extract_number(utt, lang=self.lang) or 10
        self.bus.emit(
            message.forward("mycroft.volume.decrease", {"percent": volume_change / 100})
        )
        self.speak_dialog(
            "volume.set.percent",
            data={"level": max(MIN_VOLUME, int(volume - volume_change))},
        )

    @intent_handler(
        IntentBuilder("increase_volume").require("louder").require("volume")
    )
    def handle_increase_volume_intent(self, message):
        volume = self._query_volume(message)
        normalizer = UtteranceNormalizerPlugin.get_normalizer(self.lang)
        utt = normalizer.normalize(message.data["utterance"])
        if not (volume == MAX_VOLUME):
            volume_change = extract_number(utt, lang=self.lang) or 10
            self.bus.emit(
                message.forward(
                    "mycroft.volume.increase", {"percent": volume_change / 100}
                )
            )
            self.speak_dialog(
                "volume.set.percent",
                data={"level": min(MAX_VOLUME, int(volume + volume_change))},
            )
        else:
            self.speak_dialog("volume.max.already")

    @intent_handler("volume.max.intent")
    def handle_max_volume_intent(self, message):
        self.bus.emit(message.forward("mycroft.volume.set", {"percent": 1.0}))
        self.speak_dialog("volume.max")

    @intent_handler("volume.high.intent")
    def handle_high_volume_intent(self, message):
        self.bus.emit(message.forward("mycroft.volume.set", {"percent": 0.9}))

    @intent_handler("volume.default.intent")
    def handle_default_volume_intent(self, message):
        self.bus.emit(message.forward("mycroft.volume.set", {"percent": 0.7}))

    @intent_handler("volume.low.intent")
    def handle_low_volume_intent(self, message):
        self.bus.emit(message.forward("mycroft.volume.set", {"percent": 0.3}))

    @intent_handler("volume.mute.intent")
    def handle_mute_intent(self, message):
        self.bus.emit(message.forward("mycroft.volume.mute"))

    @intent_handler("volume.unmute.intent")
    def handle_unmute_intent(self, message):
        self.bus.emit(message.forward("mycroft.volume.unmute"))

    @intent_handler("volume.mute.toggle.intent")
    def handle_toggle_unmute_intent(self, message):
        self.bus.emit(message.forward("mycroft.volume.mute.toggle"))

    @intent_handler(
        IntentBuilder("current_volume").require("volume").optionally("current")
    )
    def handle_query_volume(self, message):
        volume = self._query_volume(message)
        self.speak_dialog("volume.current", data={"volume": volume})
