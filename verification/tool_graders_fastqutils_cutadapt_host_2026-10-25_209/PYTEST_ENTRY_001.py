"""Run only the new host test with isolated imports and input-read receipts."""
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
RUN = Path(sys.argv[1]).resolve()
FROZEN = HERE / 'candidate'
sys.path[:0] = [str(FROZEN), str(FROZEN / 'tests'), str(HERE)]
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
    # Capture the dependency bytes before the attempted read is performed.
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
                          '--junitxml', str(RUN / 'results.xml'), str(HERE / 'test_native_cutadapt_host.py')])
finally:
    reading = True
    after = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() if Path(name).is_file() else None
             for name in read_inputs}
    (RUN / 'read_inputs_before.json').write_text(json.dumps(read_inputs, indent=2, sort_keys=True) + '\n')
    (RUN / 'read_inputs_after.json').write_text(json.dumps(after, indent=2, sort_keys=True) + '\n')
    changed = [name for name in read_inputs if read_inputs[name] != after[name]]
    (RUN / 'read_input_check.json').write_text(json.dumps(dict(input_count=len(read_inputs),
        changed_inputs=changed, timing='Each SHA256 captured by audit hook before the corresponding read opens.'),
        indent=2, sort_keys=True) + '\n')
    if changed and result == 0:
        result = 1
raise SystemExit(result)
