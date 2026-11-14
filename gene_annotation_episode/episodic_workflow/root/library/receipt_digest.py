"""Original private root receipt and finite-record digests."""
import hashlib
import json
from .record_values import plain, finite_canonical


def digest(value):
    encoded = json.dumps(plain(value), sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def content_digest(value):
    return hashlib.sha256(finite_canonical(value).encode('utf-8')).hexdigest()
