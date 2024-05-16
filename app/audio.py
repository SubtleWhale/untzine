from dataclasses import dataclass
from enum import Enum

class AudioQualityPicker(Enum):
    VERY_LOW = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4

    @property
    def name(self) -> str:
        return self._name_.replace('_', " ").capitalize()


@dataclass
class AudioFormat:
    bitrate : int
    extension : str
    codec : str
    quality : AudioQualityPicker

class AudioFormatDefinitions:
    OGG_VORBIS_96 = AudioFormat(96, "ogg", "vorbis", AudioQualityPicker.LOW)
    OGG_VORBIS_160 = AudioFormat(160, "ogg", "vorbis", AudioQualityPicker.MEDIUM)
    OGG_VORBIS_320 = AudioFormat(320, "ogg", "vorbis", AudioQualityPicker.HIGH)
    MP3_256 = AudioFormat(256, "mp3", "mp3", AudioQualityPicker.MEDIUM)
    MP3_320 = AudioFormat(320, "mp3", "mp3", AudioQualityPicker.HIGH)
    MP3_160 = AudioFormat(160, "mp3", "mp3", AudioQualityPicker.LOW)
    MP3_96 = AudioFormat(96, "mp3", "mp3", AudioQualityPicker.VERY_LOW)
    AAC_24 = AudioFormat(24, "m4a", "aac", AudioQualityPicker.MEDIUM)
    AAC_48 = AudioFormat(48, "m4a", "aac", AudioQualityPicker.HIGH)

    @staticmethod
    def list() -> dict[str, AudioFormat]:
        return dict([(name, value) for (name, value) in vars(AudioFormatDefinitions).items() if type(value) is AudioFormat])
