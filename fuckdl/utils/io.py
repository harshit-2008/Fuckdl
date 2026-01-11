import asyncio
import contextlib
import os
import re
import shutil
import subprocess
import sys
import httpx
import pproxy
import requests
import yaml
import tqdm
import logging
from fuckdl import config
from fuckdl.utils.collections import as_list
from pathlib import Path
import m3u8
from fuckdl.utils.downloaders import n_m3u8dl, aria2

def load_yaml(path):
    if not os.path.isfile(path):
        return {}
    with open(path) as fd:
        return yaml.safe_load(fd)


_ip_info = None


def get_ip_info(session=None, fresh=False):
    """Use extreme-ip-lookup.com to get IP location information."""
    global _ip_info

    if fresh or not _ip_info:
        # alternatives: http://www.geoplugin.net/json.gp, http://ip-api.com/json/, https://extreme-ip-lookup.com/json
        _ip_info = (session or httpx).get("https://ipwho.is/").json()

    return _ip_info


@contextlib.asynccontextmanager
async def start_pproxy(host, port, username, password):
    rerouted_proxy = "http://localhost:8081"
    server = pproxy.Server(rerouted_proxy)
    remote = pproxy.Connection(f"http+ssl://{host}:{port}#{username}:{password}")
    handler = await server.start_server(dict(rserver=[remote]))
    try:
        yield rerouted_proxy
    finally:
        handler.close()
        await handler.wait_closed()



def download_range(url, count, start=0, proxy=None):
    """Download n bytes without using the Range header due to support issues."""
    # TODO: Can this be done with Aria2c?
    executable = shutil.which("curl")
    if not executable:
        raise EnvironmentError("Track needs curl to download a chunk of data but wasn't found...")

    arguments = [
        executable,
        "-s",  # use -s instead of --no-progress-meter due to version requirements
        "-L",  # follow redirects, e.g. http->https
        "--proxy-insecure",  # disable SSL verification of proxy
        "--output", "-",  # output to stdout
        "--url", url
    ]
    if proxy:
        arguments.extend(["--proxy", proxy])

    curl = subprocess.Popen(
        arguments,
        stdout=subprocess.PIPE,
        stderr=open(os.devnull, "wb"),
        shell=False
    )
    buffer = b''
    location = -1
    while len(buffer) < count:
        stdout = curl.stdout
        data = b''
        if stdout:
            data = stdout.read(1)
        if len(data) > 0:
            location += len(data)
            if location >= start:
                buffer += data
        else:
            if curl.poll() is not None:
                break
    curl.kill()  # stop downloading
    return buffer


async def aria2c(uri, track, source, out, headers=None, proxy=None):
    """
    Downloads file(s) using Aria2(c).

    Parameters:
        uri: URL to download. If uri is a list of urls, they will be downloaded and
          concatenated into one file.
        out: The output file path to save to.
        headers: Headers to apply on aria2c.
        proxy: Proxy to apply on aria2c.
    """

    executable = shutil.which("aria2c") or shutil.which("aria2")
    if not executable:
        raise EnvironmentError("Aria2c executable not found...")

    arguments = []

    for option, value in config.config.aria2c.items():
        arguments.append(f"--{option.replace('_', '-')}={value}")
    
    segmented = isinstance(uri, list)
    segments_dir = f"{out}_segments"

    if proxy:
        arguments.append("--all-proxy")
        if proxy.lower().startswith("https://"):
            auth, hostname = proxy[8:].split("@")
            async with start_pproxy(*hostname.split(":"), *auth.split(":")) as pproxy_:
                arguments.extend([pproxy_, "-d"])
                if segmented:
                    arguments.extend([segments_dir, "-i-"])
                    proc = await asyncio.create_subprocess_exec(*arguments, stdin=subprocess.PIPE)
                    await proc.communicate(as_list(uri)[0].encode("utf-8"))
                else:
                    arguments.extend([os.path.dirname(out), uri])
                    proc = await asyncio.create_subprocess_exec(*arguments)
                    await proc.communicate()
        else:
            arguments.append(proxy)

    for header, value in (headers or {}).items():
        if header.lower() == "accept-encoding":
            # we cannot set an allowed encoding, or it will return compressed
            # and the code is not set up to uncompress the data
            continue
        arguments.extend(["--header", f"{header}: {value}"])

    aria2(uri=uri, arg=arguments, track=track, source=source, out=out, headers=headers, proxy=proxy)
    print()


async def saldl(uri, track, source, out, headers=None, proxy=None):
    if headers:
        headers.update({k: v for k, v in headers.items() if k.lower() != "accept-encoding"})

    executable = shutil.which("saldl") or shutil.which("saldl-win64") or shutil.which("saldl-win32")
    if not executable:
        raise EnvironmentError("Saldl executable not found...")
    
    if track.descriptor == track.descriptor.M3U:
            master = m3u8.loads(
                requests.get(
                    as_list(uri)[0],
                    headers=headers,
                    proxies=proxy if proxy is not None else {}
                ).text,
                uri=as_list(uri)[0]
            )

            durations = []
            duration = 0
            for segment in master.segments:
                if segment.discontinuity:
                    durations.append(duration)
                    duration = 0
                duration += segment.duration
            durations.append(duration)
            largest_continuity = durations.index(max(durations))

            discontinuity = 0
            has_init = False
            segments = []
            for segment in master.segments:
                if segment.discontinuity:
                    discontinuity += 1
                    has_init = False
                if source in ["DSNP", "STRP"] and re.search(
                    r"[a-zA-Z0-9]{4}-(BUMPER|DUB_CARD)/",
                    segment.uri + (segment.init_section.uri if segment.init_section else '')
                ):
                    continue
                if source == "ATVP" and discontinuity != largest_continuity:
                    # the amount of pre and post-roll sections change all the time
                    # only way to know which section to get is by getting the largest
                    continue
                if segment.init_section and not has_init:
                    segments.append(
                        ("" if re.match("^https?://", segment.init_section.uri) else segment.init_section.base_uri) +
                        segment.init_section.uri
                    )
                    has_init = True
                segments.append(
                    ("" if re.match("^https?://", segment.uri) else segment.base_uri) +
                    segment.uri
                )
            uri = segments

    arguments = [
        executable,
        # "--no-status",
        "--skip-TLS-verification",
        "--resume",
        "--merge-in-order",
        "-c8",
        "--auto-size", "1",
        "-D", os.path.dirname(out),
        "-o", os.path.basename(out),
    ]

    if headers:
        arguments.extend([
            "--custom-headers",
            "\r\n".join([f"{k}: {v}" for k, v in headers.items()])
        ])

    if proxy:
        arguments.extend(["--proxy", proxy])

    if isinstance(uri, list):
        raise ValueError("Saldl code does not yet support multiple uri (e.g. segmented) downloads.")
    arguments.append(uri)

    try:
        subprocess.run(arguments, check=True)
    except subprocess.CalledProcessError:
        raise ValueError("Saldl failed too many times, aborting")

    print()

async def m3u8dl(uri, track, out, headers=None, proxy=None):
    out = Path(out)

    if track.descriptor == track.descriptor.M3U and isinstance(uri, list):
        url = uri[0]
    else:
        url = uri

    if headers:
        headers.update({k: v for k, v in headers.items() if k.lower() != "accept-encoding"})

    executable = shutil.which("m3u8re") or shutil.which("N_m3u8DL-RE")
    if not executable:
        raise EnvironmentError("N_m3u8DL-RE executable not found...")

    if isinstance(uri, list):
        raise ValueError("N_m3u8DL code does not yet support multiple uri (e.g. segmented) downloads.")
    
    else:
        n_m3u8dl(str(url), track, str(out.parent), out.name.replace('.mp4','').replace('.vtt',''), headers, proxy)
    
    for filename in os.listdir(os.path.dirname(out)):
        if filename == out.name.replace('.mp4','.m4a'):
            os.rename(str(out).replace(".mp4", ".m4a"), out)
        if filename == out.name.replace(".mp4", ".ts"):
            os.rename(str(out).replace(".mp4", ".ts"), out)
        if filename == out.name.replace(".mp4", ".srt"):
            os.rename(str(out).replace(".mp4", ".srt"), out)
        if filename == out.name.replace(".mp4", ".vtt"):
            os.rename(str(out).replace(".mp4", ".vtt"), out)

    print()
    
async def tqdm_downloader(uri, out, headers=None, proxy=None):
    proxies = {'https': f"{proxy}"} if 'https://' in proxy else {'http': f"{proxy}"}
    r = requests.get(uri, proxies=proxies, stream=True)
    file_size = int(r.headers["Content-Length"])
    chunk = 1
    chunk_size = 1024
    num_bars = int(file_size / chunk_size)

    with open(out, "wb") as fp:
        for chunk in tqdm.tqdm(
            r.iter_content(chunk_size=chunk_size),
            total=num_bars,
            unit="KB",
            desc=out,
            leave=True,  # progressbar stays
        ):
            fp.write(chunk)
    
    print()

async def m3u8re(uri, out, headers=None, proxy=None):
    out = Path(out)

    if headers:
        headers.update({k: v for k, v in headers.items() if k.lower() != "accept-encoding"})

    executable = shutil.which("m3u8re") or shutil.which("N_m3u8DL-RE")
    if not executable:
        raise EnvironmentError("N_m3u8DL-RE executable not found...")

    if isinstance(uri, list):
        raise ValueError("N_m3u8DL code does not yet support multiple uri (e.g. segmented) downloads.")

    arguments = [
        executable,
        uri,
        "--tmp-dir", str(out.parent),
        "--save-dir", str(out.parent),
        "--save-name", out.name.replace('.mp4','').replace('.vtt','').replace('.m4a',''),
        "--auto-subtitle-fix", "False",
        "--thread-count", "32",
        "--log-level", "INFO"
    ]

    if headers:
        arguments.extend([
            "--header",
            "\r\n".join([f"{k}: {v}" for k, v in headers.items()])
        ])
        
    if proxy:
        arguments.extend(["--custom-proxy", proxy])

    try:
        subprocess.run(arguments, check=True)
    except subprocess.CalledProcessError:
        raise ValueError("N_m3u8DL-RE failed too many times, aborting")

    print()    

