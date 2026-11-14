"""Load only the authenticated original A103 selected method for comparison."""
import hashlib
from pathlib import Path
import textwrap
from .. import runtime

ORIGINAL_SELECTED_SHA256 = 'fb3a99fb0dbb69521d99e0cbeef48b68ed3e28fd0a9aa1c9331045f071caf674'


def original_selected():
    raw = (Path(__file__).parent / 'fixtures/scientific_parent_exchange/selected_original.py.txt').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORIGINAL_SELECTED_SHA256
    namespace = dict(vars(runtime))
    exec(compile(textwrap.dedent(raw.decode('utf-8')), '<authenticated-original-A103-selected>', 'exec'), namespace)
    return namespace['selected']
