"""Load only authenticated original own-axis methods for boundary comparison."""
import hashlib
from pathlib import Path
import textwrap
from .. import runtime

ORIGINAL_HASHES = {"_receive_form":"4093c9a631552eb6b581dd27c592e11a595602895c6154267238bfdb0246817a","selected":"dd08d3d164ac38633f89dc11927654e3d3e422bf691c71ceab96514a0dcddb3c"}


def original_method(name):
    raw = (Path(__file__).parent / 'fixtures/recursive_scientific_parent' / (name + '.py.txt')).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORIGINAL_HASHES[name]
    namespace = dict(vars(runtime))
    exec(compile(textwrap.dedent(raw.decode('utf-8')), '<authenticated-original-' + name + '>', 'exec'), namespace)
    return namespace[name]


def original_selected():
    return original_method('selected')
