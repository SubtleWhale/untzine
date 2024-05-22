import base64
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from io import BytesIO
import json
from tagger import AudioFileTagger
from audio import AudioQualityPicker
from registry import ProviderRegistry
from trackinfo import TrackInfo
from provider import Provider

@dataclass
class TrackSearchContext:

    provider : Provider
    trackinfo : TrackInfo

    @staticmethod
    def _serialize_helper(o):
        if type(o) is timedelta:
            return o.microseconds
        elif isinstance(o, Provider):
            return o.get_name()
        else:
            return o.__dict__

    def to_url(self) -> str:
        return base64.b64encode(json.dumps(self, default=TrackSearchContext._serialize_helper).encode()).decode()
    
    @staticmethod
    def from_url(data : str, registry : ProviderRegistry) -> "TrackSearchContext":
        dic = json.loads(base64.b64decode(data).decode())

        dic['trackinfo']['duration'] = timedelta(microseconds=dic['trackinfo']['duration'])
        dic['trackinfo'] = TrackInfo(**dic['trackinfo'])
        dic['provider'] = registry.get_by_name(dic['provider'])

        return TrackSearchContext(**dic)

@dataclass
class RequestPreferences:
    quality : AudioQualityPicker = AudioQualityPicker.HIGH
    provider_name : str|None = None

    @property
    def available_qualities(self) -> list[AudioQualityPicker]:
        return [e for e in AudioQualityPicker]


    @staticmethod
    def _serialize_helper(o):
        if type(o) is AudioQualityPicker:
            return o.value
        else:
            return o.__dict__

    def to_cookie(self) -> str:
        return base64.b64encode(json.dumps(self, default=RequestPreferences._serialize_helper).encode()).decode()
    
    def update_from_form(self, dct : dict):
        for key, value in dct.items():

            if hasattr(self, key):

                attr = getattr(self, key, None)

                if isinstance(attr, Enum):
                    value = type(attr)(int(value))
                    
                setattr(self, key, value)

    @staticmethod
    def from_cookie(cookie : str|None) -> "RequestPreferences":

        dic = dict()

        if cookie != None:
            dic = json.loads(base64.b64decode(cookie).decode())
            dic['quality'] = AudioQualityPicker(int(dic['quality']))

        return RequestPreferences(**dic)

class RequestManager:

    def __init__(self, registry : ProviderRegistry, tagger : AudioFileTagger, preferences : RequestPreferences) -> None:
        self.registry = registry
        self.tagger = tagger
        self.preferences = preferences
        

    def search(self, terms : str) -> list[TrackSearchContext]:

        if self.preferences.provider_name != None:
            provider = self.registry.get_by_name(self.preferences.provider_name)
        else:
            provider = self.registry.get_loaded_providers()[0]

        if provider is None:
            raise Exception("Cannot find provider")

        res = provider.search_tracks(terms)
        return [TrackSearchContext(provider, x) for x in res]

    def download(self, search : TrackSearchContext) -> tuple[str, BytesIO]:

        # Get quality settings
        valid_audio_formats = list(filter(lambda x : x.quality.value <= self.preferences.quality.value, search.provider.audio_formats_available))
        valid_audio_formats.sort(key=lambda x: x.quality.value, reverse=True)

        if len(valid_audio_formats) == 0:
            raise Exception("Cannot find acceptable audio format")

        audio_format = valid_audio_formats[0]

        content = search.provider.download_track(search.trackinfo.id, audio_format)

        # Apply tags
        self.tagger.tag_audio_file(content, search.trackinfo, audio_format)

        filename = f"{search.trackinfo.artists[0]} - {search.trackinfo.title}.{audio_format.extension}"

        return (filename, content)
        