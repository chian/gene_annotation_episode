"""Private original PBS resource field readers."""
from datetime import datetime, timezone
import re

def timestamp(value):
    if type(value) in (int, float):
        return float(value)
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        # PBS observations are explicitly acquired with TZ=UTC.
        return datetime.strptime(value, '%a %b %d %H:%M:%S %Y').replace(tzinfo=timezone.utc).timestamp()


def memory_bytes(value):
    if value is None:
        return None
    match = re.fullmatch(r'([0-9.]+)([kmgt]?b)', str(value).lower())
    return float(match[1])*1024**{'b': 0, 'kb': 1, 'mb': 2, 'gb': 3, 'tb': 4}[match[2]] if match else None


