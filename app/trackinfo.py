from dataclasses import dataclass
from datetime import timedelta

@dataclass
class TrackInfo:
    id : str
    title : str
    artists : list[str]
    track_nb : int
    album : str
    duration : timedelta
    explicit : bool
    art_cover: bytes|str|None