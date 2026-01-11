import base64
import json
import re
from datetime import datetime, timedelta
from urllib.parse import unquote

import click
import m3u8
import requests

from fuckdl.objects import AudioTrack, TextTrack, Title, Tracks, VideoTrack
from fuckdl.services.BaseService import BaseService
from fuckdl.utils.collections import as_list
from fuckdl.utils import try_get
from fuckdl.vendor.pymp4.parser import Box
from fuckdl.utils.widevine.device import LocalDevice


class AppleTVPlus(BaseService):
    """
    Service code for Apple's TV Plus streaming service (https://tv.apple.com).

    \b
    WIP: decrypt and removal of bumper/dub cards

    \b
    Authorization: Cookies
    Security: UHD@L1 FHD@L1 HD@L3
    """

    ALIASES = ["ATVP", "appletvplus", "appletv+"]
    TITLE_RE = r"^(?:https?://tv\.apple\.com(?:/[a-z]{2})?/(?:movie|show|episode)/[a-z0-9-]+/)?(?P<id>umc\.cmc\.[a-z0-9]+)"  # noqa: E501

    VIDEO_CODEC_MAP = {
        "H264": ["avc"],
        "H265": ["hvc", "hev", "dvh"]
    }
    AUDIO_CODEC_MAP = {
        "AAC": ["HE", "stereo"],
        "AC3": ["ac3"],
        "EC3": ["ec3", "atmos"]
    }

    @staticmethod
    @click.command(name="AppleTVPlus", short_help="https://tv.apple.com")
    @click.argument("title", type=str, required=False)
    @click.option("-sf", "--storefront", type=int, default=None, help="Override storefront int if needed.")
    @click.pass_context
    def cli(ctx, **kwargs):
        return AppleTVPlus(ctx, **kwargs)

    def __init__(self, ctx, title, storefront):
        super().__init__(ctx)
        self.parse_title(ctx, title)
        self.cdm = ctx.obj.cdm
        self.vcodec = ctx.parent.params["vcodec"]
        self.acodec = ctx.parent.params["acodec"]
        self.range = ctx.parent.params.get("range_")
        self.alang = ctx.parent.params["alang"]
        self.subs_only = ctx.parent.params["subs_only"]
        self.storefront = storefront

        if (ctx.parent.params.get("quality") or 0) > 1080 and self.vcodec != "H265":
            self.log.info(" + Switched video codec to H265 to be able to get 2160p video track")
            self.vcodec = "H265"

        if self.range in ("HDR10", "DV", "DVHDR", "HDRDV", "HYBRID") and self.vcodec != "H265":
            self.log.info(f" + Switched video codec to H265 to be able to get {self.range} dynamic range")
            self.vcodec = "H265"

        self.extra_server_parameters = None

        self.configure()

    def get_titles(self):
        r = None
        for i in range(2):
            try:
                self.params = {
                    'utsk': '6e3013c6d6fae3c2::::::9318c17fb39d6b9c',
                    'caller': 'web',
                    'sf': self.storefront,
                    'v': '46',
                    'pfm': 'appletv',
                    'mfr': 'Apple',
                    'locale': 'en-US',
                    'l': 'en',
                    'ctx_brand': 'tvs.sbd.4000',
                    'count': '2000',
                    'skip': '0',
                }
                r = self.session.get(
                    url=self.config["endpoints"]["title"].format(type={0: "shows", 1: "movies"}[i], id=self.title),
                    params=self.params
                )
            except requests.HTTPError as e:
                if e.response.status_code != 404:
                    raise
            else:
                if r.ok:
                    break
        if not r:
            raise self.log.exit(f" - Title ID {self.title!r} could not be found.")
        try:
            title_information = r.json()["data"]["content"]
        except json.JSONDecodeError:
            raise ValueError(f"Failed to load title manifest: {r.text}")

        if title_information["type"] == "Movie":
            return Title(
                id_=self.title,
                type_=Title.Types.MOVIE,
                name=title_information["title"],
                #year=datetime.utcfromtimestamp(title_information["releaseDate"] / 1000).year,
                year=(datetime(1970, 1, 1) + timedelta(milliseconds=title_information['releaseDate'])).strftime('%Y'),
                original_lang=title_information["originalSpokenLanguages"][0]["locale"],
                source=self.ALIASES[0],
                service_data=title_information
            )
        else:
            r = self.session.get(
                url=self.config["endpoints"]["tv_episodes"].format(id=self.title),
                params=self.params
            )
            try:
                episodes = r.json()["data"]["episodes"]
            except json.JSONDecodeError:
                raise ValueError(f"Failed to load episodes list: {r.text}")

            return [Title(
                id_=self.title,
                type_=Title.Types.TV,
                name=episode["showTitle"],
                season=episode["seasonNumber"],
                episode=episode["episodeNumber"],
                episode_name=episode.get("title"),
                original_lang=title_information["originalSpokenLanguages"][0]["locale"],
                source=self.ALIASES[0],
                service_data=episode
            ) for episode in episodes]

    def get_tracks(self, title):
        self.params = {
            'utsk': '6e3013c6d6fae3c2::::::9318c17fb39d6b9c',
            'caller': 'web',
            'sf': self.storefront,
            'v': '46',
            'pfm': 'appletv',
            'mfr': 'Apple',
            'locale': 'en-US',
            'l': 'en',
            'ctx_brand': 'tvs.sbd.4000',
            'count': '100',
            'skip': '0',
        }
        r = self.session.get(
            url=self.config["endpoints"]["manifest"].format(id=title.service_data["id"]),
            params=self.params
        )
        try:
            stream_data = r.json()

        except json.JSONDecodeError:
            raise ValueError(f"Failed to load stream data: {r.text}")
        stream_data = stream_data["data"]["content"]["playables"][0]

        if not stream_data["isEntitledToPlay"]:
            raise self.log.exit(" - User is not entitled to play this title")

        self.extra_server_parameters = stream_data["assets"]["fpsKeyServerQueryParameters"]

        r = requests.get(url=stream_data["assets"]["hlsUrl"], headers={'User-Agent': 'AppleTV6,2/11.1'})
        res = r.text

        tracks = Tracks.from_m3u8(
            master=m3u8.loads(res, r.url),
            source=self.ALIASES[0]
        )

        #New Watermark Token sometimes need it for licensing
        self.watermarktoken = next((re.search(r'watermarkingToken=([^&]+)', t.url).group(1) for t in tracks if isinstance(t, VideoTrack) and 'watermarkingToken=' in t.url), None)

        for track in tracks:
            track.extra = {"manifest": track.extra}

        quality = None
        for line in res.splitlines():
            if line.startswith("#--"):
                quality = {"SD": 480, "HD720": 720, "HD": 1080, "UHD": 2160}.get(line.split()[2])
            elif not line.startswith("#"):
                track = next((x for x in tracks.videos if x.extra["manifest"].uri == line), None)
                if track:
                    track.extra["quality"] = quality

        for track in tracks:
            track_data = track.extra["manifest"]
            if isinstance(track, VideoTrack):
                track.needs_ccextractor_first = True
            if isinstance(track, VideoTrack):
                track.encrypted = True
            if isinstance(track, AudioTrack):
                track.encrypted = True
                bitrate = re.search(r"&g=(\d+?)&", track_data.uri)
                if not bitrate:
                    bitrate = re.search(r"_gr(\d+)_", track_data.uri) # new
                if bitrate:
                    track.bitrate = int(bitrate[1][-3::]) * 1000  # e.g. 128->128,000, 2448->448,000
                else:
                    #raise ValueError(f"Unable to get a bitrate value for Track {track.id}")
                    pass
                track.codec = track.codec.replace("_vod", "")
            if isinstance(track, TextTrack):
                track.codec = "vtt"

        tracks.videos = [x for x in tracks.videos if (x.codec or "")[:3] in self.VIDEO_CODEC_MAP[self.vcodec]]

        if self.acodec:
            tracks.audios = [
                x for x in tracks.audios if (x.codec or "").split("-")[0] in self.AUDIO_CODEC_MAP[self.acodec]
            ]

        tracks.subtitles = [
            x for x in tracks.subtitles
            if (x.language in self.alang or (x.is_original_lang and "orig" in self.alang) or "all" in self.alang)
            or self.subs_only
            or not x.sdh
        ]
 
        return Tracks([
            # multiple CDNs, only want one
            x for x in tracks if "vod-ak" in x.url
        ])

    def get_chapters(self, title):
        return []

    def certificate(self, **_):
        return None  # will use common privacy cert

    def license(self, challenge, track, **_):
        try:
            if self.cdm.device.type == LocalDevice.Types.PLAYREADY:
                res = self.session.post(
                    url=self.config["endpoints"]["license"],
                    json={
                            'streaming-request': {
                                                    'version': 1,
                                                    'streaming-keys': [
                                                                        {
                                                                            #"extra-server-parameters": self.extra_server_parameters,
                                                                            "challenge": base64.b64encode(challenge).decode('utf-8'),
                                                                            "key-system": "com.microsoft.playready",
                                                                            "uri": f"data:text/plain;{'watermarkingToken=' + self.watermarktoken + ';' if self.watermarktoken else ''}charset=UTF-16;base64,{track.pr_pssh}",
                                                                            "id": 0,
                                                                            "lease-action": 'start',
                                                                            "adamId": self.extra_server_parameters['adamId'],
                                                                            "isExternal": True,
                                                                            "svcId": self.extra_server_parameters['svcId'],
                                                                            },
                                                                        ],
                                                    },
                        }
                ).json()
            else:
                res = self.session.post(
                    url=self.config["endpoints"]["license"],
                    json={
                            'streaming-request': {
                                                    'version': 1,
                                                    'streaming-keys': [
                                                                        {
                                                                            #"extra-server-parameters": self.extra_server_parameters,
                                                                            "challenge": base64.b64encode(challenge).decode(),
                                                                            "key-system": "com.widevine.alpha",
                                                                            "uri": f"data:text/plain;{'watermarkingToken=' + self.watermarktoken + ';' if self.watermarktoken else ''}base64,{base64.b64encode(Box.build(track.pssh)).decode()}",
                                                                            "id": 1,
                                                                            "lease-action": 'start',
                                                                            "adamId": self.extra_server_parameters['adamId'],
                                                                            "isExternal": True,
                                                                            "svcId": self.extra_server_parameters['svcId'],
                                                                            },
                                                                        ],
                                                    },
                        }
                ).json()
        except requests.HTTPError as e:
            print(e)
            if not e.response.text:
                raise self.log.exit(" - No license returned!")
            raise self.log.exit(f" - Unable to obtain license (error code: {e.response.json()['errorCode']})")
        #print(res)
        return res['streaming-response']['streaming-keys'][0]["license"]

    # Service specific functions

    def configure(self):
        if not self.storefront:
            cc = self.session.cookies.get_dict()["itua"]
            r = self.session.get("https://gist.githubusercontent.com/BrychanOdlum/2208578ba151d1d7c4edeeda15b4e9b1/raw/8f01e4a4cb02cf97a48aba4665286b0e8de14b8e/storefrontmappings.json").json()
            for g in r:
                if g['code'] == cc:
                    store_front = g['storefrontId']
                    self.storefront = store_front

        environment = self.get_environment_config()
        if not environment:
            raise ValueError("Failed to get AppleTV+ WEB TV App Environment Configuration...")
        self.session.headers.update({
            "User-Agent": self.config["user_agent"],
            "Authorization": f"Bearer {environment['developerToken']}",
            "media-user-token": self.session.cookies.get_dict()["media-user-token"],
            "x-apple-music-user-token": self.session.cookies.get_dict()["media-user-token"]
        })

    def get_environment_config(self):
        """Loads environment config data from WEB App's serialized server data."""
        res = self.session.get("https://tv.apple.com").text
        
        script_match = re.search(r'<script[^>]*id=["\']serialized-server-data["\'][^>]*>(.*?)</script>', res, re.DOTALL)
        if script_match:
            try:
                script_content = script_match.group(1).strip()
                # Parse the JSON array
                data = json.loads(script_content)
                if data and len(data) > 0 and 'data' in data[0] and 'configureParams' in data[0]['data']:
                    return data[0]['data']['configureParams']
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                print(f"Failed to parse serialized server data: {e}")
        
        return None