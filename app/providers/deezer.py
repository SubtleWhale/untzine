import binascii
from dataclasses import dataclass
from datetime import timedelta
import functools
import hashlib
from io import BytesIO
from pathlib import Path
import re
from ssl import SSLError
from time import sleep
import requests
from requests.exceptions import ConnectionError as RequestsConnectionError, ReadTimeout, ChunkedEncodingError
from trackinfo import TrackInfo
from provider import AccountType, Provider, ProviderBuilder, ProviderConfiguration
from audio import AudioFormat, AudioFormatDefinitions
from deezer import Deezer, WrongLicense, WrongGeolocation
from Cryptodome.Cipher import AES, Blowfish
from Cryptodome.Util import Counter


MP3_128_QUALITY_ID = 9
MP3_320_QUALITY_ID = 3
FLAC_QUALITY_ID = 1

MP3_128_QUALITY_STR = "MP3_128"
MP3_320_QUALITY_STR = "MP3_320"
FLAC_QUALITY_STR = "FLAC"

BLOWFISH_SECRET = "g4el58wc0zvf9na1"

USER_AGENT_HEADER = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) " \
                    "Chrome/79.0.3945.130 Safari/537.36"

_audioFormatMapping = {
   AudioFormatDefinitions.MP3_128.id : (MP3_128_QUALITY_ID, MP3_128_QUALITY_STR),
   AudioFormatDefinitions.MP3_320.id : (MP3_320_QUALITY_ID, MP3_320_QUALITY_STR),
   AudioFormatDefinitions.FLAC_16.id : (FLAC_QUALITY_ID, FLAC_QUALITY_STR),
}

@dataclass
class DeezerConfiguration(ProviderConfiguration):
    arl : str|None = None
    
def _not_empty(prop : str|None) -> bool:
    return bool(prop and prop.strip())

class DeezerProvider(Provider):

    _is_encrypted = re.compile("/m(?:obile|edia)/")
    _api : Deezer

    def __init__(self, api: Deezer):
        self._api = api
    
    @staticmethod
    def _parse_track_info(track : dict) -> TrackInfo:

        return TrackInfo(
                id=track['SNG_ID'],
                album=track['ALB_TITLE'],
                artists=[a['ART_NAME'] for a in track['ARTISTS']],
                duration=timedelta(seconds=int(track['DURATION'])),
                explicit=track['EXPLICIT_LYRICS'] == "1",
                title=track['SNG_TITLE'],
                track_nb=int(track['TRACK_NUMBER']),
                art_cover= f"https://api.deezer.com/album/{track['ALB_ID']}/image"
            )

    def search_tracks(self, terms : str) -> list[TrackInfo]:

        # First search request
        tracks = self._api.gw.search_music(terms, "TRACK", limit=25)['data']

        # Also get album covers link in good quality
        # for track in tracks:
        #     a = self._api.gw.get_album(track['ALB_ID'])
        #     track['cover'] = a['cover_big']

        return list(map(self._parse_track_info, tracks))
    
    def get_track_info(self, track_id : str) -> TrackInfo:
        return self._parse_track_info(self._api.api.get_track(track_id))
    
    def _stream_track(self, outputStream, url : str, track_id : str, is_crypted : bool, start=0):

        headers= {'User-Agent': USER_AGENT_HEADER}
        chunkLength = start

        try:
            with requests.get(url, headers=headers, stream=True, timeout=10) as request:
                request.raise_for_status()
                if is_crypted:
                    blowfish_key = DeezerProvider._generate_blowfish_key(track_id)

                isStart = True
                for chunk in request.iter_content(2048 * 3):
                    if is_crypted:
                        if len(chunk) >= 2048:
                            chunk = DeezerProvider._decrypt_chunk(blowfish_key, chunk[0:2048]) + chunk[2048:]

                    if isStart and chunk[0] == 0 and chunk[4:8].decode('utf-8') != "ftyp":
                        for i, byte in enumerate(chunk):
                            if byte != 0: break
                        chunk = chunk[i:]
                    isStart = False

                    outputStream.write(chunk)
                    chunkLength += len(chunk)

        except (SSLError, SSLError):
            self._stream_track(outputStream, url, track_id, is_crypted, chunkLength)
        except (RequestsConnectionError, ReadTimeout, ChunkedEncodingError):
            sleep(2)
            self._stream_track(outputStream, url, track_id, is_crypted, chunkLength)


    def download_track(self, track_id : str, quality : AudioFormat) -> BytesIO:
        

        track_info = self._api.gw.get_track(track_id)


        # Map quality request
        (quality_id, quality_str) = _audioFormatMapping[quality.id]


        try:
            url = self._api.get_track_url(track_info['TRACK_TOKEN'], quality_str)
        except WrongLicense:
            raise Exception(
                "The requested quality is not available with your subscription. "
                "Deezer HiFi is required for quality 2. Otherwise, the maximum "
                "quality allowed is 1.",
            )
        except WrongGeolocation:

            # Try to get alternative id
            if "FALLBACK" in track_info and "SNG_ID" in track_info["FALLBACK"]:
                return self.download_track(track_info["FALLBACK"]["SNG_ID"], quality)
            
            raise Exception(
                "The requested track is not available. This may be due to your country/location.",
            )

        url = self._api.get_track_url(track_info["TRACK_TOKEN"], quality_str)
        
        if url is None:
            url = self._get_encrypted_file_url(
                track_id,
                track_info["MD5_ORIGIN"],
                track_info["MEDIA_VERSION"],
            )

        is_encrypted = True if self._is_encrypted.search(url) else False 

        stream = BytesIO()

        self._stream_track(stream, url, track_id, is_encrypted)

        return stream
    
    def _get_encrypted_file_url(
        self,
        meta_id: str,
        track_hash: str,
        media_version: str,
    ):
        format_number = 1

        url_bytes = b"\xa4".join(
            (
                track_hash.encode(),
                str(format_number).encode(),
                str(meta_id).encode(),
                str(media_version).encode(),
            ),
        )
        url_hash = hashlib.md5(url_bytes).hexdigest()
        info_bytes = bytearray(url_hash.encode())
        info_bytes.extend(b"\xa4")
        info_bytes.extend(url_bytes)
        info_bytes.extend(b"\xa4")
        # Pad the bytes so that len(info_bytes) % 16 == 0
        padding_len = 16 - (len(info_bytes) % 16)
        info_bytes.extend(b"." * padding_len)

        path = binascii.hexlify(
            AES.new(b"jo6aey6haid2Teih", AES.MODE_ECB).encrypt(info_bytes),
        ).decode("utf-8")
        url = f"https://e-cdns-proxy-{track_hash[0]}.dzcdn.net/mobile/1/{path}"
        return url

    @property
    def account_type(self) -> AccountType:
        # Deezer can download FLAC even with free account
        return AccountType.PREMIUM
    
    @property
    def audio_formats_available(self) -> list[AudioFormat]:
        return [AudioFormatDefinitions.MP3_128, AudioFormatDefinitions.MP3_320, AudioFormatDefinitions.FLAC_16]
    


    @staticmethod
    def _decrypt_chunk(key, data):
        """Decrypt a chunk of a Deezer stream.

        :param key:
        :param data:
        """
        return Blowfish.new(
            key,
            Blowfish.MODE_CBC,
            b"\x00\x01\x02\x03\x04\x05\x06\x07",
        ).decrypt(data)

    @staticmethod
    def _generate_blowfish_key(track_id: str) -> bytes:
        """Generate the blowfish key for Deezer downloads.

        :param track_id:
        :type track_id: str
        """
        md5_hash = hashlib.md5(track_id.encode()).hexdigest()
        # good luck :)
        return "".join(
            chr(functools.reduce(lambda x, y: x ^ y, map(ord, t)))
            for t in zip(md5_hash[:16], md5_hash[16:], BLOWFISH_SECRET)
        ).encode()

class DeezerBuilder(ProviderBuilder[DeezerProvider, DeezerConfiguration]):

    def build(self, conf : DeezerConfiguration) -> DeezerProvider:

        api = Deezer()

        if _not_empty(conf.arl):
            if not api.login_via_arl(conf.arl):
                raise Exception("Logging with arl failed")
        else:
            raise Exception("No logging configuration")

        return DeezerProvider(api)
    