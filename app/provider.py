from abc import abstractmethod
from enum import Enum
from audio import AudioFormat
from trackinfo import TrackInfo
from io import BytesIO

# class syntax
class AccountType(Enum):
    FREE = 1,
    PREMIUM = 2

class ProviderConfiguration:

    def getConfKey(self) -> str:
        # By default, return instance class name without 'configuration' in lowercase
        return self.__class__.__name__.lower().removesuffix("configuration").strip()

class Provider:

    @property
    @abstractmethod
    def account_type(self) -> AccountType:
        pass

    @property
    @abstractmethod
    def audio_formats_available(self) -> list[AudioFormat]:
        pass

    @abstractmethod
    def search_tracks(self, terms : str) -> list[TrackInfo]:
        pass

    @abstractmethod
    def get_track_info(self, track_id : str) -> TrackInfo:
        pass

    @abstractmethod
    def download_track(self, track_id : str, format : AudioFormat) -> BytesIO:
        pass

    def get_name(self) -> str:
        return self.__class__.__name__.removesuffix("Provider").strip()

class ProviderBuilder[ProviderType : Provider, ConfigurationType : ProviderConfiguration]:

    @abstractmethod
    def build(self, conf : ConfigurationType) -> ProviderType:
        pass