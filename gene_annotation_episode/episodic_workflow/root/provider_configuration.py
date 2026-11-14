"""Original packaged configuration path; no provider process or stopping policy."""
from pathlib import Path

def default_config_path():
    """The single packaged default; callers can supply their own full config."""
    return Path(__file__).with_name("defaults.toml")

