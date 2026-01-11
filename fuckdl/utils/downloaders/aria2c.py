import os
import re
import sys
import m3u8
import shutil
import requests
import subprocess

from fuckdl.utils.collections import as_list

def m3u8_segments(uri, source, headers, proxy=None):
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
    return segments

def aria2(uri, arg, track, source, out, headers=None, proxy=None):
    executable = shutil.which("aria2c") or shutil.which("aria2")
    if not executable:
        raise EnvironmentError("Aria2c executable not found...")

    arguments = [
        executable,
        "-c",  # Continue downloading a partially downloaded file
        "--remote-time",  # Retrieve timestamp of the remote file from the and apply if available
        "-o", os.path.basename(out),  # The file name of the downloaded file, relative to -d
        "-x", "16",  # The maximum number of connections to one server for each download
        "-j", "16",  # The maximum number of parallel downloads for every static (HTTP/FTP) URL
        "-s", "16",  # Download a file using N connections.
        "--allow-overwrite=true",
        "--disable-ipv6=true",
        "--auto-file-renaming=false",
        "--retry-wait", "5",  # Set the seconds to wait between retries.
        "--max-tries", "15",
        "--max-file-not-found", "15",
        "--summary-interval", "0",
        "--file-allocation", "none" if sys.platform == "win32" else "falloc",
        "--console-log-level", "warn",
        "--download-result", "hide"
    ]

    arguments.extend(arg)

   # if track.descriptor == track.descriptor.M3U:
    #    uri = m3u8_segments(uri, source, headers, proxy)

    segmented = isinstance(uri, list)
    segments_dir = f"{out}_segments"
    
    if segmented:
        if source == 'TUBI':
            uri = "\n".join([
                f"{url}\n"
                f"\tdir={segments_dir}\n"
                f"\tout={i:08}.mp4"
                for i, url in enumerate(uri)
                if i == 0
            ])
        else:
            uri = "\n".join([
                f"{url}\n"
                f"\tdir={segments_dir}\n"
                f"\tout={i:08}.mp4"
                for i, url in enumerate(uri)
            ])

    try:
        if segmented:
            subprocess.run(
                arguments + ["-d", segments_dir, "-i-"],
                input=as_list(uri)[0],
                encoding="utf-8",
                check=True
            )
        else:
            subprocess.run(
                arguments + ["-d", os.path.dirname(out), uri],
                check=True
            )
    except subprocess.CalledProcessError:
        raise ValueError("Aria2c failed too many times, aborting")

    if segmented:
        # merge the segments together
        with open(out, "wb") as ofd:
            for file in sorted(os.listdir(segments_dir)):
                file = os.path.join(segments_dir, file)
                with open(file, "rb") as ifd:
                    data = ifd.read()
                # Apple TV+ needs this done to fix audio decryption
                data = re.sub(b"(tfhd\x00\x02\x00\x1a\x00\x00\x00\x01\x00\x00\x00)\x02", b"\\g<1>\x01", data)
                ofd.write(data)
                os.unlink(file)
        os.rmdir(segments_dir)