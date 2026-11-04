"""Only218 focused cases, immutable candidate imports, read-before hashes."""
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
RUN = Path(sys.argv[1]).resolve()
FROZEN = HERE / 'candidate'
sys.path[:0] = [str(FROZEN), str(FROZEN / 'tests'), str(HERE / 'helpers'), str(HERE)]
read_inputs, reading = {}, False
def audit(event, args):
    global reading
    if reading or event != 'open' or not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    path = Path(os.fsdecode(args[0])).resolve()
    flags = args[2]
    if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
        return
    if path.is_relative_to(RUN) or not path.is_file() or str(path) in read_inputs:
        return
    resume = os.environ.get('SAMSTAT_RESUME_CHECKPOINT')
    if resume and path.is_relative_to(Path(resume).resolve().parents[2]):
        return
    reading = True
    try:
        read_inputs[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    finally:
        reading = False

sys.addaudithook(audit)
import pytest
result = None
try:
    result = pytest.main(['-v', '-s', '-p', 'no:cacheprovider', '--basetemp', str(RUN / 'tmp'),
        '--junitxml', str(RUN / 'results.xml'), *[str(HERE / arg) for arg in sys.argv[2:]]])
finally:
    reading = True
    modules = []
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename is None or not Path(filename).is_file():
            continue
        path = Path(filename).resolve()
        if name.split('.', 1)[0] in ('gene_annotation_episode', 'method_loop'):
            assert path.is_relative_to(FROZEN), (name, path)
        modules.append(dict(module=name, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    after = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() if Path(name).is_file() else None
             for name in read_inputs}
    for name, value in (('read_inputs_before', read_inputs), ('read_inputs_after', after), ('import_origins', modules)):
        (RUN / (name + '.json')).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    changed = [name for name in read_inputs if read_inputs[name] != after[name]]
    (RUN / 'read_input_check.json').write_text(json.dumps(dict(input_count=len(read_inputs), changed=changed,
        timing='SHA256 captured before each dependency read'), indent=2, sort_keys=True) + '\n')
    if changed and result == 0:
        result = 1
raise SystemExit(result)
