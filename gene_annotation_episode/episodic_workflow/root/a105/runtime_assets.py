"""Required packaged runtime data; excludes generated records and ownership metadata."""
import hashlib
from pathlib import Path

_SHARED_ASSETS = (
    'library/retained_input_authority/bvbrc_appservice_schemas.json',
)


def required_runtime_asset_fingerprints():
    """Fingerprint actual static loaders' inputs without touching saved records."""
    root = Path(__file__).parent
    paths = _SHARED_ASSETS
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}
