import os
import shutil
import subprocess
from itertools import chain

AUDIO_CODEC_MAP = {"AAC": "mp4a", "AC3": "ac-3", "EC3": "ec-3", "mp4a": "mp4a", "ec-3": "ec-3", "ac-3": "ac-3"}
VIDEO_CODEC_MAP = {"avc1": "avc", "hvc1": "hvc", "dvhe": "dvh", "HLG": "hev"}

def track_selection(track):
    adaptation_set = track.extra[1]
    representation = track.extra[0]

    track_type = track.__class__.__name__
    codec = track.codec
    bitrate = track.bitrate // 1000 if track_type != "TextTrack" else None
    language = track.language
    
    width = track.width if track_type == "VideoTrack" else None
    if track_type == "VideoTrack":
        range = "HDR" if track.hdr10 else "HLG" if track.hlg else "DV" if track.dv else "SDR"
    else:
        range = None
    
    global langs
    langs = None


    if track_type == "AudioTrack":
        codecs = AUDIO_CODEC_MAP.get(codec)
        langs = adaptation_set.get('lang')
        track_ids = list(set(
            v for x in chain(adaptation_set, representation)
            for v in (x.get("audioTrackId"), x.get("id"))
            if v is not None
        ))
        roles = adaptation_set.findall("Role") + representation.findall("Role")
        main_role = next((i for i in roles if i.get("value", "").lower() == "main"), None)
        role = ":role=main" if main_role is not None else ""
        bandwidth = f"bwMin={bitrate - 1}:bwMax={bitrate + 1}"
        
        if langs is not None:
            track_selection = ["-sa", f"lang={langs}:codecs={codecs}:{bandwidth}{role}"]
        elif len(track_ids) == 1:
            track_selection = ["-sa", f"id={track_ids[0]}"]
        else:
            track_selection = ["-sa", f"for=best{role}"]
        return track_selection

    if track_type == "VideoTrack":
        # adjust codec based on range
        codec_adjustments = {
            ("HEVC", "DV"): "DV",
            ("HEVC", "HLG"): "HLG",
            ("SDR"): "SDR"
        }
        codec = codec_adjustments.get((codec, range), codec)
        codecs = VIDEO_CODEC_MAP.get(codec)
        
        bandwidth = f"bwMin={int(bitrate)}:bwMax={int(bitrate + 5)}"
        #track_selection = ["-sv", f"res={width}*:codecs={codecs}:{bandwidth}"]
        track_selection = ["-sv", f"res={width}*:codecs={codecs}:for=best"]
        return track_selection
    
    if track_type == "TextTrack":
        if language:
            track_selection = ["-ss", f"lang={language}:for=all"]
        else:
            track_selection = ["-ss", "all"]
        if codec=="SRT" or codec=="VTT":
            track_selection.extend(["--sub-format", codec])
        return track_selection

def n_m3u8dl(url, track, output_dir, filename, headers=None, proxy=None):
    executable = shutil.which("m3u8re") or shutil.which("N_m3u8DL-RE")
    ffmpeg_executable = shutil.which("ffmpeg")
    if not executable:
        raise EnvironmentError("N_m3u8DL-RE executable not found...")
    if not ffmpeg_executable:
        raise EnvironmentError("Ffmpeg executable not found...")

    arguments = [
        executable,
        url,
        "--save-dir", output_dir,
        "--tmp-dir", output_dir,
        "--save-name", filename,
        "--ffmpeg-binary-path", ffmpeg_executable,
        "--thread-count", "32",
        "--log-level", "ERROR",
        "--no-log",
    ]

    if proxy is not None:
        arguments.extend(["--custom-proxy", proxy])

    if headers is not None:
        header_args = [arg for k, v in headers.items() for arg in ("-H", f"{k}: {v}")]
        arguments.extend(header_args)

    if track.descriptor == track.descriptor.MPD:
        selected_track = track_selection(track)
        arguments.extend(selected_track)

    try:
        subprocess.run(arguments, check=True)
    except subprocess.CalledProcessError:
        raise ValueError("N_m3u8DL-RE failed too many times, aborting")
    
    if track.descriptor == track.descriptor.MPD:
        for file in os.listdir(output_dir):
            if langs:
                if file == f"{filename}.{langs}.m4a":
                    audiopath = os.path.join(output_dir, file)
                    os.rename(audiopath, audiopath.replace(f".{langs}", ""))