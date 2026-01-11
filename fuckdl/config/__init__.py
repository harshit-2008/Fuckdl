import os
import tempfile
from types import SimpleNamespace
from pathlib import Path

import yaml
from appdirs import AppDirs
from requests.utils import CaseInsensitiveDict

from fuckdl.objects.vaults import Vault
from fuckdl.utils.collections import merge_dict


class Config:
    @staticmethod
    def load_vault(vault):
        return Vault(**{
            "type_" if k == "type" else k: v for k, v in vault.items()
        })


class Directories:
    def __init__(self):
        self.app_dirs = AppDirs("fuckdl", False)
        self.package_root = Path(__file__).resolve().parent.parent
        self.configuration = self.package_root / "config"
        self.user_configs = self.package_root
        self.service_configs = self.user_configs / "services"
        self.data = self.package_root
        self.downloads = Path(__file__).resolve().parents[2] / "downloads"
        self.temp = Path(__file__).resolve().parents[2] / "temp"
        self.cache = self.package_root / "cache"
        self.cookies = self.data / "cookies"
        self.logs = self.package_root / "logs"
        self.devices = self.data / "devices"

class Filenames:
    def __init__(self):
        self.log = os.path.join(directories.logs, "fuckdl_{time}.log")
        # Support both fuckdl.yml and Fuck.yml (case-insensitive)
        self.root_config = self._find_config_file(directories.configuration, ["fuckdl.yml", "Fuck.yml", "fuck.yml"])
        self.user_root_config = self._find_config_file(directories.user_configs, ["fuckdl.yml", "Fuck.yml", "fuck.yml"])
        self.service_config = os.path.join(directories.configuration, "services", "{service}.yml")
        self.user_service_config = os.path.join(directories.service_configs, "{service}.yml")
        self.subtitles = os.path.join(directories.temp, "TextTrack_{id}_{language_code}.srt")
        self.chapters = os.path.join(directories.temp, "{filename}_chapters.txt")
    
    @staticmethod
    def _find_config_file(directory, possible_names):
        """Find config file with case-insensitive matching."""
        dir_path = Path(directory)
        if not dir_path.exists():
            # Return first option as default if directory doesn't exist
            return os.path.join(directory, possible_names[0])
        
        # Check for exact matches first
        for name in possible_names:
            file_path = dir_path / name
            if file_path.exists():
                return str(file_path)
        
        # Case-insensitive search
        for file_path in dir_path.iterdir():
            if file_path.is_file():
                file_lower = file_path.name.lower()
                for name in possible_names:
                    if file_lower == name.lower():
                        return str(file_path)
        
        # Return default if not found
        return os.path.join(directory, possible_names[0])


directories = Directories()
filenames = Filenames()

# Load config files (handle case-insensitive file names)
config = {}
if os.path.exists(filenames.root_config):
    with open(filenames.root_config) as fd:
        config = yaml.safe_load(fd) or {}

user_config = {}
if os.path.exists(filenames.user_root_config):
    with open(filenames.user_root_config) as fd:
        user_config = yaml.safe_load(fd) or {}
merge_dict(config, user_config)
config = SimpleNamespace(**config)
credentials = config.credentials

def setup_paths():
    downloads_path = config.directories.get('downloads')
    temp_path = config.directories.get('temp')

    if downloads_path and Path(downloads_path).is_dir():
        directories.downloads = Path(downloads_path)

    if temp_path and Path(temp_path).is_dir():
        directories.temp = Path(temp_path)
        filenames.subtitles = os.path.join(directories.temp, "TextTrack_{id}_{language_code}.srt")
        filenames.chapters = os.path.join(directories.temp, "{filename}_chapters.txt")


setup_paths()

# This serves two purposes:
# - Allow `range` to be used in the arguments section in the config rather than just `range_`
# - Allow sections like [arguments.Amazon] to work even if an alias (e.g. AMZN or amzn) is used.
#   CaseInsensitiveDict is used for `arguments` above to achieve case insensitivity.
# NOTE: The import cannot be moved to the top of the file, it will cause a circular import error.
from fuckdl.services import SERVICE_MAP  # noqa: E402

if "range_" not in config.arguments:
    config.arguments["range_"] = config.arguments.get("range_")
for service, aliases in SERVICE_MAP.items():
    for alias in aliases:
        config.arguments[alias] = config.arguments.get(service)
config.arguments = CaseInsensitiveDict(config.arguments)


