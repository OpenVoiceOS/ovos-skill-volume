from ovos_number_parser import extract_number
from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements
from ovos_utterance_normalizer import UtteranceNormalizerPlugin
from ovos_workshop.decorators import intent_handler
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
    @intent_handler("change_volume.intent")
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
            if response is None:
                self.speak_dialog("error.get.volume")
                return
            volume_change = extract_number(normalizer.normalize(response), lang=self.lang)
        if volume_change >= 100:
            self.speak_dialog("volume.max")
        else:
            self.speak_dialog("volume.set.percent", data={"level": int(volume_change)})
        self.bus.emit(
            message.forward("mycroft.volume.set", {"percent": volume_change / 100})
        )

    @intent_handler("less_volume.intent")
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

    @intent_handler("increase_volume.intent")
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

    # level word -> (voc filename, volume percent), most specific first
    _LEVEL_VOCS = (
        ("level.max", 1.0),
        ("level.high", 0.9),
        ("level.medium", 0.7),
        ("level.low", 0.3),
        ("level.default", 0.7),
    )

    def _set_volume_level(self, message, percent):
        self.bus.emit(message.forward("mycroft.volume.set", {"percent": percent}))
        if percent == 1.0:
            self.speak_dialog("volume.max")

    @intent_handler("volume_level.intent")
    def handle_set_volume_level(self, message):
        level = message.data.get("level", "")
        utterance = message.data.get("utterance", "")
        # a bare level word ("Grida", "Standardlautstärke") carries no {level}
        # slot at all -- fall back to matching the level vocs against the
        # whole utterance so those literal-only training lines still resolve
        for candidate in (level, utterance):
            if not candidate:
                continue
            for voc_filename, percent in self._LEVEL_VOCS:
                if self.voc_match(candidate, voc_filename, exact=False):
                    self._set_volume_level(message, percent)
                    return
        self.speak_dialog("volume.level.unknown", data={"level": level})

    @intent_handler("volume.max.boost.intent")
    def handle_max_volume_boost_intent(self, message):
        self._set_volume_level(message, 1.0)

    @intent_handler("volume.reset.intent")
    def handle_reset_volume_intent(self, message):
        self._set_volume_level(message, 0.7)

    @intent_handler("volume.mute.intent")
    def handle_mute_intent(self, message):
        self.bus.emit(message.forward("mycroft.volume.mute"))

    @intent_handler("volume.unmute.intent")
    def handle_unmute_intent(self, message):
        self.bus.emit(message.forward("mycroft.volume.unmute"))

    @intent_handler("volume.mute.toggle.intent")
    def handle_toggle_unmute_intent(self, message):
        self.bus.emit(message.forward("mycroft.volume.mute.toggle"))

    @intent_handler("current_volume.intent")
    def handle_query_volume(self, message):
        volume = self._query_volume(message)
        self.speak_dialog("volume.current", data={"volume": volume})
