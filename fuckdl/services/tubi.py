from __future__ import annotations

import hashlib
import os
import re
import sys
import uuid
from collections.abc import Generator
from typing import Any

import click
from langcodes import Language

from fuckdl.objects import TextTrack, Title, Tracks
from fuckdl.services.BaseService import BaseService
from fuckdl.objects import AudioTrack, TextTrack, Title, Tracks, VideoTrack, AudioTrack, MenuTrack
from fuckdl.utils import Cdm
from fuckdl.vendor.pymp4.parser import Box
from fuckdl.utils.widevine.device import LocalDevice


class TUBI(BaseService):
    """
    Service code for TubiTV streaming service (https://tubitv.com/)

    \b
    Version: 1.0.5
    Author: stabbedbybrick
    Authorization: Cookies (Optional)
    Geofence: Locked to whatever region the user is in (API only)
    Robustness:
        Widevine:
            L3: 1080p, AAC2.0
        PlayReady:
            SL2000: 1080p, AAC2.0
        Clear:
            1080p, AAC2.0

    \b
    Tips:
        - Input can be complete title URL or just the path:
            /series/300001423/gotham
            /tv-shows/200024793/s01-e01-pilot
            /movies/589279/the-outsiders
        - Use '-v H265' to request HEVC tracks.

    \b
    Notes:
        - Authentication is currently not required, but cookies are used if provided.
        - If 1080p exists, it's currently only available as H.265.

    """
    ALIASES = ["TUBI", "tubi", "tubitv", "TubiTV"]
    TITLE_RE = r"^(?:https?://(?:www\.)?tubitv\.com?)?/(?P<type>movies|series|tv-shows)/(?P<id>[a-z0-9-]+)"

    @staticmethod
    @click.command(name="TUBI", short_help="https://tubitv.com/", help=__doc__)
    @click.argument("title", type=str)
    @click.pass_context
    def cli(ctx, **kwargs):
        return TUBI(ctx, **kwargs)

    def __init__(self, ctx, title):
        self.title = title
        super().__init__(ctx)

        self.cdm = ctx.obj.cdm
        self.drm_system = "playready" if self.cdm.device.type == LocalDevice.Types.PLAYREADY else "widevine"

        vcodec = ctx.parent.params.get("vcodec")
        self.vcodec = "H265" if vcodec == "H265" else "H264"

        self.configure()
        
    def configure(self):
        self.auth_token = None
        if self.cookies is not None:
            self.auth_token = next((cookie.value for cookie in self.cookies if cookie.name == "at"), None)
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})

    def get_titles(self):
        try:
            kind, content_id = (re.match(self.TITLE_RE, self.title).group(i) for i in ("type", "id"))
        except Exception:
            raise ValueError("Could not parse ID from title - is the URL correct?")

        params = {
            "app_id": "tubitv",
            "platform": "web", # web, android, androidtv
            "device_id": str(uuid.uuid4()),
            "content_id": content_id,
            "limit_resolutions[]": [
                "h264_1080p",
                "h265_1080p",
            ],
            "video_resources[]": [
                "dash_widevine_nonclearlead",
                "dash_playready_psshv0",
                                                                           
                "dash",
                                
            ],
        }

        if kind == "tv-shows":
            content = self.session.get(self.config["endpoints"]["content"], params=params)
            content.raise_for_status()
            series_id = "0" + content.json().get("series_id")
            params.update({"content_id": int(series_id)})
            data = self.session.get(self.config["endpoints"]["content"], params=params).json()
            
            return [
                        Title(
                            id_=episode["id"],
                            type_=Title.Types.TV,
                            name=data["title"],
                            year=data["year"],
                            season=int(season["id"]),
                            episode=int(episode["episode_number"]),
                            episode_name=episode["title"].split("-")[1],
                            original_lang="en",
                            source=self.ALIASES[0],
                            service_data=episode
                        ) 
                        for season in data["children"]
                        for episode in season["children"]
                    ]

        if kind == "series":
            r = self.session.get(self.config["endpoints"]["content"], params=params)
            r.raise_for_status()
            data = r.json()

            return [
                        Title(
                            id_=episode["id"],
                            type_=Title.Types.TV,
                            name=data["title"],
                            year=data["year"],
                            season=int(season["id"]),
                            episode=int(episode["episode_number"]),
                            episode_name=episode["title"].split("-")[1],
                            original_lang="en",
                            source=self.ALIASES[0],
                            service_data=episode
                        ) 
                        for season in data["children"]
                        for episode in season["children"]
                    ]

        if kind == "movies":
            r = self.session.get(self.config["endpoints"]["content"], params=params)
            r.raise_for_status()
            data = r.json()
            
            return Title(
                    id_=data["id"],
                    type_=Title.Types.MOVIE,
                    name=data["title"],
                    year=data["year"],
                    original_lang="en",  # TODO: Get original language
                    source=self.ALIASES[0],
                    service_data=data,
                )

    def get_tracks(self, title):
        if not (resources := title.service_data.get("video_resources")):
            self.log.error(" - Failed to obtain video resources. Check geography settings.")
            self.log.info(f"Title is available in: {title.service_data.get('country')}")
            sys.exit(1)

        codecs = [x.get("codec") for x in resources]
        if not any(self.vcodec in x for x in codecs):
            raise ValueError(f"Could not find a {self.vcodec} video resource for this title")

        resource = next((
            x for x in resources
            if self.drm_system in x.get("type", "") and self.vcodec in x.get("codec", "")
        ), None) or next((
            x for x in resources
            if self.drm_system not in x.get("type", "") and
            "dash" in x.get("type", "") and
            self.vcodec in x.get("codec", "")
        ), None)
        if not resource:
            raise ValueError("Could not find a video resource for this title")

        manifest = resource.get("manifest", {}).get("url")
        if not manifest:
            raise ValueError("Could not find a manifest for this title")


        
        title.service_data["license_url"] = resource.get("license_server", {}).get("url")
        
        tracks = Tracks.from_mpd(
            url=manifest,
            session=self.session,
            source=self.ALIASES[0]
        )
        
        for track in tracks:
            rep_base = track.extra[1].find("BaseURL")
            if rep_base is not None:
                base_url = os.path.dirname(track.url)
                track_base = rep_base.text
                track.url = f"{base_url}/{track_base}"
                track.descriptor = Track.Descriptor.URL
        #        track.downloader = aria2c

                
        for track in tracks.audios:
            role = track.extra[1].find("Role")
            if role is not None and role.get("value") in ["description", "alternative", "alternate"]:
                track.descriptive = True

            
        if title.service_data.get("subtitles"):
            tracks.add(
                TextTrack(
                    id_=hashlib.md5(title.service_data["subtitles"][0]["url"].encode()).hexdigest()[0:6],
                    source=self.ALIASES[0],
                    url=title.service_data["subtitles"][0]["url"],
                    codec=title.service_data["subtitles"][0]["url"][-3:],
                    language= title.service_data["subtitles"][0].get("lang_alpha3"),
                    forced=False,
                    sdh=False,
                )
            )
            
        return tracks       

    def get_chapters(self, title):
        return []

    def certificate(self, **_):
        # TODO: Hardcode the certificate
        return self.license(**_)

        
    def license(self, challenge, title, **_):
        if not (license_url := title.service_data.get("license_url")):
            return None
        if self.cdm.device.type == LocalDevice.Types.PLAYREADY:
            r = self.session.post(url=license_url, data=challenge)
            if r.status_code != 200:
                raise ConnectionError(r.text)

            return r.content
        else:
            r = self.session.post(url=license_url, data=challenge)
            if r.status_code != 200:
                raise ConnectionError(r.text)

            return r.content

