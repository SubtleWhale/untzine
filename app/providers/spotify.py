from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from librespot.core import Session
import requests
from trackinfo import TrackInfo
from provider import AccountType, Provider, ProviderBuilder, ProviderConfiguration
from audio import AudioFormat, AudioFormatDefinitions
from librespot.audio.decoders import VorbisOnlyAudioQuality, AudioQuality
from librespot.metadata import TrackId

SEARCH_URL = 'https://api.spotify.com/v1/search'

FOLLOWED_ARTISTS_URL = 'https://api.spotify.com/v1/me/following?type=artist'

SAVED_TRACKS_URL = 'https://api.spotify.com/v1/me/tracks'

TRACKS_URL = 'https://api.spotify.com/v1/tracks'

TRACK_STATS_URL = 'https://api.spotify.com/v1/audio-features/'

USER_READ_EMAIL = 'user-read-email'

USER_FOLLOW_READ = 'user-follow-read'

PLAYLIST_READ_PRIVATE = 'playlist-read-private'

USER_LIBRARY_READ = 'user-library-read'

_audioFormatMapping = {
   AudioQuality.NORMAL : AudioFormatDefinitions.OGG_VORBIS_96,
   AudioQuality.HIGH : AudioFormatDefinitions.OGG_VORBIS_160,
   AudioQuality.VERY_HIGH : AudioFormatDefinitions.OGG_VORBIS_320,
}

@dataclass
class SpotifyConfiguration(ProviderConfiguration):

    login : str|None = None
    password : str|None = None
    login_session_save_path : str|None = None
    session : str|None = None
    
def _not_empty(prop : str|None) -> bool:
    return bool(prop and prop.strip())

class SpotifyProvider(Provider):

    __session : Session

    def __init__(self, session: Session):
        self.__session = session
        
    def _get_auth_token(self):
        return self.__session.tokens().get_token(
            USER_READ_EMAIL, PLAYLIST_READ_PRIVATE, USER_LIBRARY_READ, USER_FOLLOW_READ
        ).access_token
    
    def _request(self, url, params : dict = dict()) -> dict:

        headers = {
            'Authorization': f'Bearer {self._get_auth_token()}',
            'Accept-Language': 'en',
            'Accept': 'application/json',
            'app-platform': 'WebPlayer'
        }
        
        return requests.get(url, headers=headers, params=params).json()
    
    @staticmethod
    def _parse_track_info(track : dict) -> TrackInfo:
        return TrackInfo(
                id=track['id'],
                album=track['album']['name'],
                artists=[a['name'] for a in track['artists']],
                duration=timedelta(milliseconds=track['duration_ms']),
                explicit=track['explicit'],
                title=track['name'],
                track_nb=track['track_number'],
                art_cover=track['album']['images'][0]['url']
            )

    def search_tracks(self, terms : str) -> list[TrackInfo]:

        resp = self._request(SEARCH_URL, {
            'limit': '30',
            'offset': '0',
            'q': terms,
            'type': 'track'
        })

        results = list[TrackInfo]()

        # Convert search result to track info
        for track in resp['tracks']['items']:

            # Sort album images by quality
            track['album']['images'].sort(reverse=True, key=lambda x : x['height'])

            results.append(self._parse_track_info(track))

        return results
    
    def get_track_info(self, track_id : str) -> TrackInfo:
        track = self._request(f'{TRACKS_URL}?ids={track_id}&market=from_token')
        return self._parse_track_info(track['tracks'][0])


    def download_track(self, track_id : str, quality : AudioFormat) -> BytesIO:

        track = TrackId.from_base62(track_id)

        # Map quality request
        for q, f in _audioFormatMapping.items():
            if f == quality:
                spotify_quality = q
                break

        # Get content stream
        audio = self.__session.content_feeder().load(track, VorbisOnlyAudioQuality(spotify_quality), False, None)

        if audio == None:
            raise Exception("Track is not available")

        return BytesIO(audio.input_stream.stream().read())

    @property
    def account_type(self) -> AccountType:
        return AccountType.PREMIUM if self.__session.get_user_attribute('type') == 'premium' else AccountType.FREE
    
    @property
    def audio_formats_available(self) -> list[AudioFormat]:
        return list(_audioFormatMapping.values())

class SpotifyBuilder(ProviderBuilder[SpotifyProvider, SpotifyConfiguration]):

    def build(self, conf : SpotifyConfiguration) -> SpotifyProvider:

        configuration_builder = Session.Configuration.Builder()

        if conf.login_session_save_path and conf.login_session_save_path.strip():
            configuration_builder.set_stored_credential_file(conf.login_session_save_path)
        else:
            configuration_builder.set_store_credentials(False)

        session_builder = Session.Builder(configuration_builder.build())
        
        try:

            if _not_empty(conf.session):
                session = session_builder.stored(conf.session).create()

            elif _not_empty(conf.login_session_save_path) and Path(conf.login_session_save_path).exists():
                session = session_builder.stored_file(conf.login_session_save_path).create()

            elif _not_empty(conf.login) and _not_empty(conf.password):

                session = session_builder.user_pass(conf.login, conf.password).create()
            else:
                raise Exception("Cannot build spotify provider, no login method configured")
    
        except RuntimeError as ex:
            raise Exception(f"Cannot build spotify provider, login failed: {ex}")

        return SpotifyProvider(session)