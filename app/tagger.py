from io import BytesIO
from mediafile import MediaFile, Image, ImageType, UnreadableFileError
import requests
from audio import AudioFormat
from trackinfo import TrackInfo

class AudioFileTagger:

    def tag_audio_file(self, file, trackinfo : TrackInfo, audioinfo : AudioFormat):

        self._rewind_audio_file(file)   

        media = MediaFile(file)

        media.update({
            'title' : trackinfo.title,
            'artists': trackinfo.artists,
            'artist': trackinfo.artists[0],
            'track': trackinfo.track_nb,
            'album': trackinfo.album
        })

        if trackinfo.art_cover != None:
            art = requests.get(trackinfo.art_cover).content if type(trackinfo.art_cover) is str else trackinfo.art_cover
            media.images = [Image(data=art, desc=u"Front Cover", type=ImageType.front)]

        try:
            self._rewind_audio_file(file)        
            media.save()
            self._rewind_audio_file(file)   
        except UnreadableFileError as ex:
            # Error in mutagen when setting ogg artwork, can skip file will be valid
            if "unable to read full header" in ex.__str__():
                pass

    def _rewind_audio_file(self, file):
            
        if isinstance(file, BytesIO):
            file.seek(0)
    
