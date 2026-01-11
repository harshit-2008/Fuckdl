# FuckDL - Complete Usage Guide

## Table of Contents
1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Basic Usage](#basic-usage)
4. [Command Options](#command-options)
5. [Service-Specific Examples](#service-specific-examples)
6. [Advanced Usage](#advanced-usage)

---

## Installation

1. **Install Python 3.9.x - 3.14.x**
   - Make sure to add Python to PATH during installation

2. **Install Microsoft Visual C++ Redistributable**
   ```
   https://aka.ms/vs/17/release/vc_redist.x64.exe
   ```

3. **Install Dependencies**
   ```bash
   poetry install
   ```

4. **Install Firefox Cookie Extension**
   - Install: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt-one-click/
   - This extension is needed to export cookies from streaming services

---

## Configuration

### 1. Cookies Setup

For each service, export cookies using the Firefox extension and save them as `default.txt` in the appropriate folder:

```
fuckdl/cookies/[SERVICE_NAME]/default.txt
```

**Example Cookie Locations:**
- **HBO Max**: `fuckdl/cookies/HBOMax/default.txt`
- **Amazon Prime Video**: `fuckdl/cookies/Amazon/default.txt`
- **Apple TV Plus**: `fuckdl/cookies/AppleTVPlus/default.txt`
- **iTunes**: `fuckdl/cookies/iTunes/default.txt`
- **Netflix**: `fuckdl/cookies/Netflix/default.txt`
- **Disney Plus**: `fuckdl/cookies/DisneyPlus/default.txt`
- **Hulu**: `fuckdl/cookies/Hulu/default.txt`
- And so on for other services...

### 2. Credentials Setup

For services requiring credentials (DisneyPlus, Videoland, ParamountPlus, All4, RakutenTV, BritBox), add them to `fuckdl/config/fuckdl.yml`:

```yaml
credentials:
  DisneyPlus:
    email: your_email@example.com
    password: your_password
```

### 3. CDM Device Setup

For Playready devices (SL2000/SL3000):
1. Create a folder in `fuckdl/devices/` (e.g., `fuckdl/devices/my_device_sl3000/`)
2. Add `bgroupcert.dat` and `zgpriv.dat` files
3. Edit `fuckdl.yml` to add the folder name
4. FuckDL will create PRD files and reprovision every hour automatically

---

## Basic Usage

### General Command Structure

```bash
poetry run fuckdl dl [OPTIONS] SERVICE [SERVICE_OPTIONS] [URL or TITLE_ID]
```

### Get Help

```bash
# General help
poetry run fuckdl dl --help

# Service-specific help
poetry run fuckdl dl Amazon --help
poetry run fuckdl dl Netflix --help
poetry run fuckdl dl DisneyPlus --help
```

---

## Command Options

### Video Quality & Codec Options

```bash
# Set video quality/resolution
-q, --quality TEXT          # Options: SD, HD720, 1080, 2160, 4K
                            # Example: -q 1080, -q 4K, -q SD

# Set video codec
-v, --vcodec TEXT           # Options: H264, H265, HEVC, VP9, AV1
                            # Default: H264
                            # Example: -v H265, -v VP9

# Set audio codec
-a, --acodec TEXT           # Options: AAC, AC3, EC3, OPUS, VORB
                            # Example: -a AAC, -a EC3

# Set video bitrate
-vb, --vbitrate INTEGER     # Example: -vb 5000

# Set audio bitrate
-ab, --abitrate INTEGER     # Example: -ab 192

# Set color range/HDR
-r, --range TEXT            # Options: SDR, HDR, HDR10, HLG, DV, DVHDR
                            # Default: SDR
                            # Example: -r HDR, -r DV

# Prefer Atmos audio
-aa, --atmos                # Example: -aa

# Set audio channels
-ch, --channels TEXT        # Options: 2.0, 5.1, 7.1, 16/JOC, atmos
                            # Example: -ch 5.1, -ch atmos
```

### Language Options

```bash
# Audio language
-al, --alang TEXT           # Default: orig (original)
                            # Examples: -al en, -al en,es,fr
                            # Multiple: -al "en,es,fr"

# Subtitle language
-sl, --slang TEXT           # Default: all
                            # Examples: -sl en, -sl "en,es,fr"
                            # Use "all" for all available subtitles
```

### Episode Selection

```bash
# Wanted episodes
-w, --wanted TEXT           # Examples:
                            # Single episode: -w S01E01
                            # Season range: -w S01-S05
                            # Episode range: -w S01E01-S01E10
                            # Multiple: -w S01-S03,S05
                            # Exclude: -w S01-S05,-S03
                            # Complex: -w S01E01-S02E03
```

### Track Selection

```bash
# Download only specific tracks
-A, --audio-only            # Download only audio tracks
-V, --video-only            # Download only video tracks
-S, --subs-only             # Download only subtitles
-C, --chapters-only         # Download only chapters

# Exclude specific tracks
-ns, --no-subs              # Don't download subtitles
-na, --no-audio             # Don't download audio
-nv, --no-video             # Don't download video
-nc, --no-chapters          # Don't download chapters

# Additional subtitle options
-ad, --audio-description    # Download audio description tracks
-nf, --no-forced            # Don't download forced subtitles
--no-sdh                    # Don't download SDH subtitles
--no-cc                     # Don't download CC subtitles
--no-ccextractor            # Don't use ccextractor
```

### Muxing Options

```bash
-nm, --no-mux               # Don't mux tracks together
--mux                        # Force muxing (useful with --audio-only/--subs-only)
```

### CDM & Keys Options

```bash
# Override CDM
--cdm TEXT                  # Example: --cdm device_name

# Key retrieval options
--keys                      # Only retrieve keys, don't download
--cache                     # Use only Key Vaults (skip CDM)
--no-cache                  # Use only CDM (skip Key Vaults)
```

### Proxy Options

```bash
--proxy TEXT                # Proxy URI or 2-letter country code
                            # Example: --proxy US, --proxy http://proxy:8080
--no-proxy                  # Force disable proxy
--force-proxy               # Force use proxy even if region matches
```

### Other Options

```bash
-p, --profile TEXT         # Use specific profile
--list                      # List available tracks without downloading
--selected                  # List selected tracks
--worst                     # Choose worst quality instead of best
--delay INTEGER             # Delay between title processing (seconds)
--second                    # Download second video (if available)
-nt, --no-title             # Remove episode name from filename
```

---

## Service-Specific Examples

### Amazon Prime Video

```bash
# Download single episode
poetry run fuckdl dl -al en -sl en -w S01E01 Amazon https://www.primevideo.com/region/eu/detail/0KRGHGZCHKS920ZQGY5LBRF7MA/

# Download entire season
poetry run fuckdl dl -al en -sl en -w S01 Amazon https://www.primevideo.com/region/eu/detail/0KRGHGZCHKS920ZQGY5LBRF7MA/

# Download multiple seasons
poetry run fuckdl dl -al en -sl en -w S01-S03 Amazon https://www.primevideo.com/region/eu/detail/0KRGHGZCHKS920ZQGY5LBRF7MA/

# Download in 4K HDR
poetry run fuckdl dl -al en -sl en -r HDR -v H265 Amazon https://www.primevideo.com/region/eu/detail/0KRGHGZCHKS920ZQGY5LBRF7MA/

# Download SD quality
poetry run fuckdl dl -al en -sl en -q SD Amazon https://www.primevideo.com/region/eu/detail/0KRGHGZCHKS920ZQGY5LBRF7MA/
```

### Apple TV Plus

```bash
# Download episode
poetry run fuckdl dl -al en -sl en -w S01E01 AppleTVPlus https://tv.apple.com/us/show/big-beasts/umc.cmc.7d9yulmth1rvkwpij477qsqsk

# Download season
poetry run fuckdl dl -al en -sl en -w S01 AppleTVPlus https://tv.apple.com/us/show/big-beasts/umc.cmc.7d9yulmth1rvkwpij477qsqsk

# Download in 4K Dolby Vision
poetry run fuckdl dl -al en -sl en -r DV -v H265 AppleTVPlus https://tv.apple.com/us/show/big-beasts/umc.cmc.7d9yulmth1rvkwpij477qsqsk
```

### iTunes

```bash
# Download movie/show
poetry run fuckdl dl -al tr -sl tr iTunes -m umc.cmc.2lj6d47e7094s6ss83j0uppdm

# Download in 4K
poetry run fuckdl dl -al en -sl en -v H265 iTunes -m umc.cmc.2lj6d47e7094s6ss83j0uppdm

# Download in HDR
poetry run fuckdl dl -al en -sl en -r HDR iTunes -m umc.cmc.2lj6d47e7094s6ss83j0uppdm

# Download in Dolby Vision
poetry run fuckdl dl -al en -sl en -r DV iTunes -m umc.cmc.2lj6d47e7094s6ss83j0uppdm

# Download SD quality
poetry run fuckdl dl -al en -sl en -q SD iTunes -m umc.cmc.2lj6d47e7094s6ss83j0uppdm
```

### Netflix

```bash
# Download using Netflix URL
poetry run fuckdl dl -al en -sl en Netflix https://www.netflix.com/watch/80192098

# Download specific season
poetry run fuckdl dl -al en -sl en -w S01 Netflix https://www.netflix.com/watch/80192098

# Download with Atmos audio
poetry run fuckdl dl -al en -sl en -aa Netflix https://www.netflix.com/watch/80192098
```

### Disney Plus

```bash
# Download episode (requires credentials in config)
poetry run fuckdl dl -al en -sl en -w S01E01 DisneyPlus https://www.disneyplus.com/video/...

# Download entire series
poetry run fuckdl dl -al en -sl en DisneyPlus https://www.disneyplus.com/video/...
```

### HBO Max

```bash
# Download episode
poetry run fuckdl dl -al en -sl en -w S01E01 HBOMax https://www.hbomax.com/...

# Download season
poetry run fuckdl dl -al en -sl en -w S01 HBOMax https://www.hbomax.com/...
```

### Hulu

```bash
# Download episode
poetry run fuckdl dl -al en -sl en -w S01E01 Hulu https://www.hulu.com/...
```

### BBC iPlayer

```bash
# Download episode
poetry run fuckdl dl -al en -sl en BBCiPlayer https://www.bbc.co.uk/iplayer/episode/...
```

### Paramount Plus

```bash
# Download (requires credentials)
poetry run fuckdl dl -al en -sl en ParamountPlus https://www.paramountplus.com/...
```

### Peacock

```bash
# Download episode
poetry run fuckdl dl -al en -sl en Peacock https://www.peacocktv.com/...
```

### All4

```bash
# Download (requires credentials)
poetry run fuckdl dl -al en -sl en All4 https://www.channel4.com/...
```

### BritBox

```bash
# Download (requires credentials)
poetry run fuckdl dl -al en -sl en BritBox https://www.britbox.com/...
```

### Other Services

Similar patterns work for:
- **Crave**: `poetry run fuckdl dl -al en -sl en Crave [URL]`
- **Discovery Plus (DSCP)**: `poetry run fuckdl dl -al en -sl en DSCP [URL]`
- **ITV**: `poetry run fuckdl dl -al en -sl en ITV [URL]`
- **MY5**: `poetry run fuckdl dl -al en -sl en MY5 [URL]`
- **NowTVIT/NowTVUK**: `poetry run fuckdl dl -al en -sl en NowTVIT [URL]`
- **Pluto TV**: `poetry run fuckdl dl -al en -sl en PLUTO [URL]`
- **RakutenTV**: `poetry run fuckdl dl -al en -sl en RakutenTV [URL]`
- **Roku**: `poetry run fuckdl dl -al en -sl en ROKU [URL]`
- **Skyshowtime**: `poetry run fuckdl dl -al en -sl en Skyshowtime [URL]`
- **Stan**: `poetry run fuckdl dl -al en -sl en Stan [URL]`
- **TUBI**: `poetry run fuckdl dl -al en -sl en TUBI [URL]`
- **Videoland**: `poetry run fuckdl dl -al en -sl en Videoland [URL]`
- **WowTV**: `poetry run fuckdl dl -al en -sl en WowTV [URL]`
- **MoviesAnywhere**: `poetry run fuckdl dl -al en -sl en MoviesAnywhere [URL]`

---

## Advanced Usage

### List Available Tracks Without Downloading

```bash
# List all available tracks
poetry run fuckdl dl --list Amazon https://www.primevideo.com/...

# List selected tracks
poetry run fuckdl dl --selected Amazon https://www.primevideo.com/...
```

### Retrieve Keys Only (No Download)

```bash
# Get decryption keys without downloading
poetry run fuckdl dl --keys Amazon https://www.primevideo.com/...
```

### Use Specific Profile

```bash
# Use a different profile
poetry run fuckdl dl -p profile_name Amazon https://www.primevideo.com/...
```

### Download Only Audio

```bash
# Download audio tracks only
poetry run fuckdl dl -A -al en Amazon https://www.primevideo.com/...

# Download audio with muxing
poetry run fuckdl dl -A --mux -al en Amazon https://www.primevideo.com/...
```

### Download Only Subtitles

```bash
# Download subtitles only
poetry run fuckdl dl -S -sl en Amazon https://www.primevideo.com/...
```

### Use Proxy

```bash
# Use proxy by country code
poetry run fuckdl dl --proxy US Amazon https://www.primevideo.com/...

# Use specific proxy URL
poetry run fuckdl dl --proxy http://proxy.example.com:8080 Amazon https://www.primevideo.com/...
```

### Delay Between Downloads

```bash
# Add 5 second delay between episodes
poetry run fuckdl dl --delay 5 -w S01 Amazon https://www.primevideo.com/...
```

### Download Worst Quality

```bash
# Download worst available quality (useful for testing)
poetry run fuckdl dl --worst Amazon https://www.primevideo.com/...
```

### Complex Episode Selection

```bash
# Download seasons 1-3, but exclude season 2
poetry run fuckdl dl -w S01-S03,-S02 Amazon https://www.primevideo.com/...

# Download specific episodes across seasons
poetry run fuckdl dl -w S01E01-S01E05,S02E01-S02E03 Amazon https://www.primevideo.com/...

# Download season 1, episodes 1-10 of season 2, and all of season 3
poetry run fuckdl dl -w S01,S02E01-S02E10,S03 Amazon https://www.primevideo.com/...
```

### Multiple Languages

```bash
# Download with multiple audio languages
poetry run fuckdl dl -al "en,es,fr" Amazon https://www.primevideo.com/...

# Download with multiple subtitle languages
poetry run fuckdl dl -sl "en,es,fr,de" Amazon https://www.primevideo.com/...
```

### Complete Example with Multiple Options

```bash
# Download season 1-2, 4K HDR, H265, Atmos audio, English/Spanish, with delay
poetry run fuckdl dl \
  -w S01-S02 \
  -q 2160 \
  -r HDR \
  -v H265 \
  -aa \
  -al "en,es" \
  -sl "en,es" \
  --delay 3 \
  Amazon https://www.primevideo.com/region/eu/detail/0KRGHGZCHKS920ZQGY5LBRF7MA/
```

---

## Troubleshooting

### Check Service-Specific Options

Each service may have additional options. Check them with:

```bash
poetry run fuckdl dl [SERVICE_NAME] --help
```

### Common Issues

1. **"No cookies found"**: Make sure cookies are exported and placed in the correct folder
2. **"No credentials"**: Add credentials to `fuckdl.yml` for services that require them
3. **"CDM not found"**: Ensure CDM device files are in `fuckdl/devices/`
4. **"Downloader not specified"**: Check `fuckdl.yml` for downloader configuration

---

## Notes

- Default download location: `downloads/` folder
- Logs are saved in: `fuckdl/logs/`
- Temporary files: `temp/` folder
- Configuration file: `fuckdl/config/fuckdl.yml`

---

## Created By

**Barbie DRM**  
https://t.me/barbiedrm

---

For more information and updates, visit: https://github.com/chromedecrypt/Fuckdl
