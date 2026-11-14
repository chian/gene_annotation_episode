"""Load only authenticated original own-axis methods for boundary comparison."""
import hashlib
from pathlib import Path
import textwrap
from .. import runtime

ORIGINAL_HASHES = {"_receive_form":"51eab4c1e4e21550e1bcaa61db5a4300eca05de6825c56aa0f83027ff437ebef","selected":"dd08d3d164ac38633f89dc11927654e3d3e422bf691c71ceab96514a0dcddb3c"}


def original_method(name):
    raw = (Path(__file__).parent / 'fixtures/recursive_scientific_parent' / (name + '.py.txt')).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORIGINAL_HASHES[name]
    namespace = dict(vars(runtime))
    exec(compile(textwrap.dedent(raw.decode('utf-8')), '<authenticated-original-' + name + '>', 'exec'), namespace)
    return namespace[name]


def original_selected():
    return original_method('selected')
