# FuckDL v1.2.0 Release Notes

## Release v1.2.0

This major release brings extensive new service support, DV+HDR capabilities, and numerous bug fixes.

## What's New in v1.2.0

### Core Features

#### DV+HDR Support
- 🎨 **New**: Dolby Vision + HDR function support
- ✨ Enhanced video quality options for supported services
- 🎬 Better handling of premium video formats

#### New Service Scripts
- ✨ **YouTube**: Full support for YouTube content downloads
- ✨ **Mubi**: Added Mubi streaming service support
- ✨ **Plex**: Plex service integration
- ✨ **AXN Player**: AXN Player support
- ✨ **BBC iPlayer**: BBC iPlayer service support
- ✨ **Bravia Core**: Sony Bravia Core integration
- ✨ **Discovery+**: Discovery Plus service support
- ✨ **Filmio**: Filmio streaming service
- ✨ **Flixole**: Flixole platform support
- ✨ **Google Play**: Google Play Movies & TV support
- ✨ **RTL**: RTL streaming service
- ✨ **Spectrum**: Spectrum TV support
- ✨ **TV Now**: TV Now service integration
- ✨ **TVNZ**: TVNZ On Demand support
- ✨ **Hotstar**: Disney+ Hotstar support

### Bug Fixes and Improvements

#### Service Script Fixes
- 🔧 **Fixed**: Disney script compatibility issues
- 🔧 **Fixed**: HBO Max script errors
- 🔧 **Fixed**: Apple TV Plus script bugs
- 🔧 **Fixed**: Amazon Prime Video script issues
- 🔧 **Fixed**: Crunchyroll script problems
- 🔧 **Fixed**: Disney Plus script errors

#### Core Fixes
- 🔧 **Fixed**: Track.py module issues
- 🔧 **Fixed**: API communication problems
- 🔧 **Fixed**: Vault management issues
- 🛡️ Improved overall stability and error handling

## Features

- ✅ Support for 40+ streaming services
- ✅ Playready and Widevine DRM decryption
- ✅ **DV+HDR support** (NEW)
- ✅ Multiple downloader support (N_m3u8DL-RE, Aria2c, saldl)
- ✅ CDM device support (SL2000/SL3000, WVD files)
- ✅ Comprehensive command-line interface
- ✅ Multiple quality and codec options
- ✅ Subtitle and audio track selection
- ✅ Episode range selection
- ✅ Proxy support
- ✅ Key vault integration

## Supported Services

- All4
- Amazon Prime Video
- Apple TV Plus
- AXN Player (NEW)
- BBC iPlayer (NEW)
- Bravia Core (NEW)
- BritBox
- Crave
- Crunchyroll
- CTV
- Discovery Plus (NEW)
- Disney Plus
- Filmio (NEW)
- Flixole (NEW)
- Google Play (NEW)
- HBO Max
- Hotstar (NEW)
- Hulu
- iTunes
- ITV
- Movies Anywhere
- Mubi (NEW)
- MY5
- Netflix
- Now TV (IT/UK)
- Paramount Plus
- Peacock
- Plex (NEW)
- Pluto TV
- Rakuten TV
- Roku
- RTL (NEW)
- Skyshowtime
- Spectrum (NEW)
- Stan
- TUBI
- TV Now (NEW)
- TVNZ (NEW)
- Videoland
- WowTV
- YouTube (NEW)

## Installation

```bash
poetry install
```

## Usage

```bash
poetry run fuckdl dl --help
```

## Configuration

1. Copy `fuckdl/config/fuckdl.yml` to your user config directory
2. Add your cookies to `fuckdl/cookies/[SERVICE]/[PROFILE].txt`
3. Add CDM devices to `fuckdl/devices/`
4. Configure credentials in `fuckdl.yml` for services that require them

## Created By

**Barbie DRM**  
https://t.me/barbiedrm

## Previous Versions

- [v1.1.1](RELEASE_NOTES_v1.1.1.md) - Amazon CDM device updates
- [v1.1.0](RELEASE_NOTES_v1.1.0.md) - 4K ISM support and bug fixes
- [v0.1.1](RELEASE_NOTES_v0.1.1.md) - Initial improvements
- [v0.1.0](RELEASE_NOTES_v0.1.0.md) - Initial release

## License

See LICENSE file for details.
