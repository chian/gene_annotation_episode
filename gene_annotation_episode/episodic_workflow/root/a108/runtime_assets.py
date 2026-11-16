"""Exact packaged inputs of A108's retained incoming schema readers."""
import hashlib
import json
from pathlib import Path

_ASSETS = (
    'library/retained_input_authority/bvbrc_appservice_schemas.json',
)


def required_runtime_asset_fingerprints():
    root = Path(__file__).parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in _ASSETS}


def binding_runtime_asset_bytes():
    return json.dumps(required_runtime_asset_fingerprints(), sort_keys=True, separators=(',', ':')).encode('utf8')
