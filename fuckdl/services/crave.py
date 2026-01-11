import base64
import json
import os
import time
import urllib.parse

import click

from fuckdl.objects import TextTrack, Title, Tracks
from fuckdl.services.BaseService import BaseService
from fuckdl.utils.widevine.device import LocalDevice

class Crave(BaseService):
    """
    Service code for Bell Media's Crave streaming service (https://crave.ca).

    \b
    Authorization: Cookies
    Security: UHD@-- HD@L3, doesn't care about releases.

    """

    ALIASES = ["CRAV", "crave"]
    GEOFENCE = ["ca"]
    TITLE_RE = [r"^(?:https?://(?:www\.)?crave\.ca(?:/[a-z]{2})?/(?:series|movie|special)/)?(?P<id>[a-z0-9-]+)-\d+$", r"^(?:https?://(?:www\.)?crave\.ca(?:/[a-z]{2})?/(?:movies|tv-shows|special)/)?(?P<id>[a-z0-9-]+)"]


    @staticmethod
    @click.command(name="Crave", short_help="https://crave.ca")
    @click.argument("title", type=str, required=False)
    @click.option("-m", "--movie", is_flag=True, default=False, help="Title is a movie.")
    @click.pass_context
    def cli(ctx, **kwargs):
        return Crave(ctx, **kwargs)

    def __init__(self, ctx, title, movie):
        super().__init__(ctx)
        self.parse_title(ctx, title)
        self.movie = movie
        self.vcodec = ctx.parent.params["vcodec"]
        self.cdm = ctx.obj.cdm
        self.profile = ctx.obj.profile

        self.ce_access_token = None
        self.refresh_token = None
        
        self.configure()

    def get_titles(self):
        title_information = self.session.post(
            url="https://www.crave.ca/space-graphql/graphql",
            json={
                "operationName": "axisMedia",
                "variables": {
                    "axisMediaId": self.title
                },
                "query": """
                query axisMedia($axisMediaId: ID!) {
                    contentData: axisMedia(id: $axisMediaId) {
                        id
                        axisId
                        title
                        originalSpokenLanguage
                        firstPlayableContent {
                            id
                            title
                            axisId
                            path
                            seasonNumber
                            episodeNumber
                        }
                        mediaType
                        firstAirYear
                        seasons {
                            title
                            id
                            seasonNumber
                        }
                    }
                }
                """
            }
        ).json()["data"]["contentData"]
        titles = []
        if self.movie:
            return Title(
                id_=self.title,
                type_=Title.Types.MOVIE,
                name=title_information["title"],
                year=title_information.get("firstAirYear"),
                original_lang=title_information["originalSpokenLanguage"],
                source=self.ALIASES[0],
                service_data=title_information["firstPlayableContent"]
            )
        for season in title_information["seasons"]:
            titles.extend(self.session.post(
                url="https://www.crave.ca/space-graphql/graphql",
                json={
                    "operationName": "season",
                    "variables": {
                        "seasonId": season["id"]
                    },
                    "query": """
                    query season($seasonId: ID!) {
                        axisSeason(id: $seasonId) {
                            episodes {
                                axisId
                                title
                                contentType
                                seasonNumber
                                episodeNumber
                                axisPlaybackLanguages {
                                    language
                                }
                            }
                        }
                    }
                    """
                }
            ).json()["data"]["axisSeason"]["episodes"])
        return [Title(
            id_=self.title,
            type_=Title.Types.TV,
            name=title_information["title"],
            year=title_information.get("firstAirYear"),
            season=x.get("seasonNumber"),
            episode=x.get("episodeNumber"),
            episode_name=x.get("title"),
            original_lang=title_information["originalSpokenLanguage"],
            source=self.ALIASES[0],
            service_data=x
        ) for x in titles]
        
    def get_tracks(self, title):
        
        try:
            # Step 1: Get content metadata from Bell Media API
            content_response = self.session.get(
                url=f"https://playback.rte-api.bellmedia.ca/contents/{title.service_data['axisId']}",
                headers={
                    "Authorization": f"Bearer {self.ce_access_token}",
                    "X-Client-Platform": "platform_jasper_web",
                    "X-Playback-Language": "EN",
                    "Accept-Language": "EN",
                    "Origin": "https://www.crave.ca",
                    "Referer": "https://www.crave.ca/"
                }
            ).json()
            
            content_id = content_response.get("contentId")
            content_package = content_response.get("contentPackage", {})
            package_id = content_package.get("id")
            destination_id = content_response.get("destinationId", 1880)
            
            if not content_id or not package_id:
                raise Exception(f"Missing content/package ID in response")
            
            self.log.info(f"Content ID: {content_id}, Package ID: {package_id}, Destination: {destination_id}")
            
            # Step 2: Call 9c9media API directly with Bearer token
            # Modified to request AC3 audio by setting mca=true (multi-channel audio)
            import time
            import random
            
            if self.vcodec == "H265":
                meta_url = (
                    f"https://stream.video.9c9media.com/meta/content/{content_id}/"
                    f"contentpackage/{package_id}/destination/{destination_id}/platform/1"
                    "?format=mpd&filter=ff&uhd=true&hd=true&mcv=true&mca=true&mta=true&stt=true"
                )
            else:
                meta_url = (
                    f"https://stream.video.9c9media.com/meta/content/{content_id}/"
                    f"contentpackage/{package_id}/destination/{destination_id}/platform/1"
                    "?format=mpd&filter=ff&uhd=false&hd=true&mcv=true&mca=true&mta=true&stt=true"
                )
            
            
            # Try multiple times with increasing delays
            max_attempts = 15
            meta_response = None
            base_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Origin": "https://www.crave.ca",
                "Connection": "keep-alive",
                "Referer": "https://www.crave.ca/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site",
                "TE": "trailers"
            }
            
            for attempt in range(1, max_attempts + 1):
                try:
                    # Add some randomization to avoid rate limiting patterns
                    headers = base_headers.copy()
                    headers["Authorization"] = f"Bearer {self.ce_access_token}"
                    
                    # Use a fresh connection each time
                    meta_response = self.session.get(
                        meta_url,
                        headers=headers,
                        timeout=20
                    )
                    
                    if meta_response.status_code == 200:
                        self.log.info(f"✓ Success on attempt {attempt}!")
                        break
                    elif meta_response.status_code == 403:
                        error_msg = meta_response.text
                        if "proxy" in error_msg.lower() or "940" in error_msg:
                            self.log.error(f"9c9media is blocking your IP/connection as a proxy!")
                            self.log.error(f"Error: {error_msg[:200]}")
                            raise Exception("9c9media API blocked request - detected as proxy/VPN. "
                                          "Try: 1) Disable VPN/proxy, 2) Use residential IP, 3) Wait and retry later")
                        else:
                            raise Exception(f"403 Forbidden: {error_msg[:200]}")
                    elif meta_response.status_code == 500:
                        # 500 errors are common, just wait and retry
                        wait_time = min(3 + (attempt * 2), 30)  # progressive: 5s, 7s, 9s, ... up to 30s
                        # Add small random jitter to avoid synchronized retries
                        wait_time += random.uniform(0, 2)
                        
                        if attempt < max_attempts:
                            self.log.warning(f"500 error (attempt {attempt}/{max_attempts}), waiting {wait_time:.1f}s...")
                            time.sleep(wait_time)
                        else:
                            raise Exception(f"Still getting 500 errors after {max_attempts} attempts. 9c9media API may be down.")
                    else:
                        self.log.error(f"Unexpected status {meta_response.status_code}: {meta_response.text[:200]}")
                        if attempt < max_attempts:
                            time.sleep(5)
                        else:
                            raise Exception(f"Unexpected status code: {meta_response.status_code}")
                        
                except Exception as e:
                    if "500" in str(e) or "Max retries" in str(e):
                        if attempt < max_attempts:
                            wait_time = min(3 + (attempt * 2), 30) + random.uniform(0, 2)
                            self.log.warning(f"Network error (attempt {attempt}/{max_attempts}), waiting {wait_time:.1f}s...")
                            time.sleep(wait_time)
                        else:
                            raise Exception(f"Failed after {max_attempts} attempts. 9c9media API appears to be down or blocking requests.")
                    else:
                        raise
            
            if not meta_response or meta_response.status_code != 200:
                raise Exception(f"Could not get valid response from 9c9media after {max_attempts} attempts. The API may be temporarily down.")
            
            meta_data = meta_response.json()
            
            if self.cdm.device.type == LocalDevice.Types.PLAYREADY:
                manifest_url = meta_data.get("playback").replace("widevine", "playready")
            else:
                manifest_url = meta_data.get("playback")
            
            if not manifest_url:
                raise Exception(f"No playback URL in response: {meta_data}")
            
            self.log.info(f"Manifest URL: {manifest_url}")
            
        except Exception as e:
            raise Exception(f"Failed to fetch playback info: {e}")
        
        # Step 3: Fetch MPD manifest
        try:
            mpd_response = self.session.get(
                manifest_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Referer": "https://www.crave.ca/",
                    "Origin": "https://www.crave.ca"
                }
            )
            mpd_response.raise_for_status()
            mpd_data = mpd_response.text
            
            if not mpd_data or not mpd_data.strip().startswith("<?xml"):
                raise Exception(f"Invalid MPD response. Content: {mpd_data[:200]}")
                
        except Exception as e:
            raise Exception(f"Failed to fetch MPD manifest from {manifest_url}: {e}")
        
        tracks = Tracks.from_mpd(
            data=mpd_data,
            url=manifest_url,
            source=self.ALIASES[0]
        )
        
        # Handle audio descriptive tracks
        for track in tracks.audios:
            role = track.extra[1].find("Role")
            if role is not None and role.get("value") in ["description", "alternative", "alternate"]:
                track.descriptive = True
        
        # Handle forced subtitles
        for track in tracks.subtitles:
            # Check if the track has Role elements indicating forced subtitle
            adaptation_set = track.extra[1]  # AdaptationSet element
            roles = adaptation_set.findall("Role")
            
            for role in roles:
                # Check for forced-subtitle role
                role_value = role.get("value", "")
                scheme_id = role.get("schemeIdUri", "")
                
                if role_value == "forced-subtitle" or \
                   (scheme_id == "urn:mpeg:dash:role:2011" and role_value == "forced-subtitle"):
                    track.forced = True
                    self.log.info(f"Detected forced subtitle: {track.language} - {role_value}")
                    break
                
        return tracks
    
    def get_chapters(self, title):
        return []

    def certificate(self, **_):
        return None  # will use common privacy cert

    def license(self, challenge, **_):
        if self.cdm.device.type == LocalDevice.Types.PLAYREADY:
            return self.session.post(
                url=self.config["endpoints"]["license_pr"],
                data=challenge
            ).content
        else:
            return self.session.post(
                url=self.config["endpoints"]["license_wv"],
                data=challenge
            ).content

    # Service specific functions

    def configure(self):
        self.log.info(f"Fetching Axis title ID based on provided path: {self.title}")
        axis_id = self.get_axis_id(f"/tv-shows/{self.title}") or self.get_axis_id(f"/movies/{self.title}")
        if not axis_id:
            raise self.log.exit(f" - Could not obtain the Axis ID for {self.title!r}, are you sure it's right?")
        self.title = axis_id
        self.log.info(f" + Obtained: {self.title}")
        self.cache_path = self.get_cache(f"tokens_{self.profile}.json")
        self.load_tokens()

        if not self.ce_access_token:
            self.ce_access_token = self.session.cookies.get('ce_access')
            self.refresh_token = self.session.cookies.get('ce_refresh')
            if self.ce_access_token:
                self.save_tokens()
        
        if self.ce_access_token and self.is_expired(self.ce_access_token):
            self.log.info("Token expired, refreshing...")
            self.refresh_tokens()

    def load_tokens(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r") as f:
                    data = json.load(f)
                    self.ce_access_token = data.get("access_token")
                    self.refresh_token = data.get("refresh_token")
            except Exception as e:
                self.log.warning(f"Failed to load tokens from cache: {e}")

    def save_tokens(self):
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w") as f:
            json.dump({
                "access_token": self.ce_access_token,
                "refresh_token": self.refresh_token
            }, f, indent=4)

    def is_expired(self, token):
        try:
            payload = token.split(".")[1]
            # Add padding if needed
            payload += "=" * ((4 - len(payload) % 4) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            exp = decoded.get("exp")
            if exp and time.time() > exp:
                return True
            return False
        except Exception:
            return True # If invalid, assume expired

    def refresh_tokens(self):
        if not self.refresh_token:
            self.log.error("No refresh token available.")
            return

        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': 'Basic Y3JhdmUtd2ViOmRlZmF1bHQ=',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.crave.ca',
            'referer': 'https://www.crave.ca/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        }

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
        }

        try:
            response = self.session.post(self.config["endpoints"]["refresh"], headers=headers, data=data)
            response.raise_for_status()
            res_json = response.json()
            
            self.ce_access_token = res_json.get("access_token")
            self.refresh_token = res_json.get("refresh_token")
            
            if self.ce_access_token:
                self.session.cookies.update({
                    "ce_access": self.ce_access_token, 
                    "ce_refresh": self.refresh_token
                })
            
            self.save_tokens()
            self.log.info("Token refreshed successfully.")
        except Exception as e:
            self.log.error(f"Failed to refresh token: {e}")
    

    def get_axis_id(self, path):
        res = self.session.post(
            url="https://www.crave.ca/space-graphql/graphql",
            json={
                "operationName": "resolvePath",
                "variables": {
                    "path": path
                },
                "query": """
                query resolvePath($path: String!) {
                    resolvedPath(path: $path) {
                        lastSegment {
                            content {
                                id
                            }
                        }
                    }
                }
                """
            }
        ).json()
        if "errors" in res:
            if res["errors"][0]["extensions"]["code"] == "NOT_FOUND":
                return None
            raise ValueError("Unknown error has occurred when trying to obtain the Axis ID for: " + path)
        return res["data"]["resolvedPath"]["lastSegment"]["content"]["id"]