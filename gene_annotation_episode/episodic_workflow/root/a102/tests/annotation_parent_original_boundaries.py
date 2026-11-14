"""Authenticate original A102 methods and keep their actual live runtime globals."""
import hashlib
import json
from pathlib import Path
import textwrap
from .. import runtime

FIXTURE_SHA256 = 'c14059556069223c5873db739b4bd4814c3656d5786c22e9c10f0b861cc87185'

def original_method(name):
    raw = (Path(__file__).parent / 'fixtures/annotation_parent_boundaries/original_methods.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    body = json.loads(raw)['methods'][name]
    namespace = dict(vars(runtime))
    exec(compile(textwrap.dedent(body), '<authenticated-original-A102-' + name + '>', 'exec'), namespace)
    return namespace[name]
