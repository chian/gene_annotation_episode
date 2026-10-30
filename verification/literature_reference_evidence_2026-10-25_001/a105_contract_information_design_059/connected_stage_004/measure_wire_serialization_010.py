"""Measure actual _send serialization of complete captured synthetic RPCs."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

STAGE = Path(__file__).absolute().parent
PIN = STAGE / 'pin_010'
sys.path.insert(0, str(PIN))
from gene_annotation_episode.providers import _SessionConnection

class Sink:
    def __init__(self): self.raw = []
    def write(self, value): self.raw.append(value)
    async def drain(self): pass

async def main():
    rows = []
    for path in sorted((STAGE / 'checks_010/measurements').glob('*/ACTUAL_TURN_START.json')):
        turn = json.loads(path.read_text())
        # The controlled wire creates one thread then one turn. Params and
        # original dictionary insertion order are the actual complete capture.
        sink = Sink()
        connection = _SessionConnection.__new__(_SessionConnection)
        connection.process = SimpleNamespace(stdin=sink)
        await connection._send({'id': 2, 'method': 'turn/start', 'params': turn})
        raw = sink.raw[0]
        assert json.loads(raw)['params'] == turn
        rows.append({'case': path.parent.name, 'turn_start_rpc_bytes_including_newline': len(raw),
            'turn_start_rpc_sha256': hashlib.sha256(raw).hexdigest(),
            'serializer': 'actual pinned _SessionConnection._send with JSON defaults and allow_nan=False',
            'capture': str(path.relative_to(STAGE)), 'real_transport_or_model_started': False})
    assert len(rows) == 6
    with (STAGE / 'checks_010/EXACT_WIRE_SERIALIZATION_010.json').open('x') as stream:
        json.dump(rows, stream, indent=2); stream.write('\n')
    print(json.dumps(rows))

asyncio.run(main())
