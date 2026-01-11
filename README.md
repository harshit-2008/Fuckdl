# FuckDL

Playready and Widevine DRM downloader and decrypter

## Description

FuckDL is a command-line program to download videos from Playready and Widevine DRM-protected video platforms.

## Features

- Support for multiple streaming services
- Playready and Widevine DRM decryption
- Download and decrypt protected content
- Multiple downloader support (N_m3u8DL-RE, Aria2c, saldl)

## Installation

```bash
poetry install
```

## Usage

```bash
poetry run fuckdl dl --help
```

## Supported Services

- All4
- Amazon Prime Video
- Apple TV Plus
- BBC iPlayer
- BritBox
- Crave
- Disney Plus
- Discovery Plus
- HBO Max
- Hulu
- iTunes
- ITV
- Movies Anywhere
- MY5
- Netflix
- Now TV (IT/UK)
- Paramount Plus
- Peacock
- Pluto TV
- Rakuten TV
- Roku
- Skyshowtime
- Stan
- TUBI
- Videoland
- WowTV

## Configuration

1. Copy `fuckdl/config/fuckdl.yml` to your user config directory
2. Add your cookies to `fuckdl/cookies/[SERVICE]/[PROFILE].txt`
3. Add CDM devices to `fuckdl/devices/`
4. Configure credentials in `fuckdl.yml` for services that require them

## Created By

**Barbie DRM**  
https://t.me/barbiedrm

## License

See LICENSE file for details.
