# <img src='https://raw.githack.com/FortAwesome/Font-Awesome/master/svgs/solid/volume-down.svg' card_color='#22a7f0' width='50' height='50' style='vertical-align:bottom'/> Volume Control

## About
This skill controls the system volume of an OpenVoiceOS device by voice. It needs a companion plugin to change the volume on the target platform.

Use [ovos-PHAL-plugin-alsa](https://github.com/OpenVoiceOS/ovos-PHAL-plugin-alsa) on Linux systems that use ALSA. Use [ovos-PHAL-plugin-termux](https://github.com/HiveMindInsiders/ovos-PHAL-plugin-termux) on Android devices that run Termux.

## Install
Install the skill with pip:

```console
pip install ovos-skill-volume
```

## Usage
Say a command like one of these:
* "Turn up the volume"
* "Decrease the audio"
* "Mute audio"
* "Set volume to 5"
* "Set volume to 75 percent"

## Related projects
* [ovos-PHAL-plugin-alsa](https://github.com/OpenVoiceOS/ovos-PHAL-plugin-alsa): the ALSA volume plugin this skill needs on Linux
* [ovos-PHAL-plugin-termux](https://github.com/HiveMindInsiders/ovos-PHAL-plugin-termux): the Termux volume plugin this skill needs on Android

## Credits
Mycroft AI (@MycroftAI)

## Category
**Configuration**

## Tags
#volume
#volume-control
#sound
#system

## License
This skill is available under the [Apache License 2.0](LICENSE).
