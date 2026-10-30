"""Root-owned mechanical review of immutable 059 generation010.

No model, scientific source, action execution, or historical run is opened.
"""
import ast
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[1]
STAGE = BASE / 'a105_contract_information_design_059/connected_stage_004'
PIN = STAGE / 'pin_010'
sys.path.insert(0, str(PIN))


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class Sink:
    def __init__(self):
        self.raw = []

    def write(self, raw):
        self.raw.append(raw)

    async def drain(self):
        pass


async def verify_wire():
    from gene_annotation_episode.providers import _SessionConnection
    expected = json.loads((STAGE / 'checks_010/EXACT_WIRE_SERIALIZATION_010.json').read_text())
    results = []
    for row in expected:
        turn = json.loads((STAGE / row['capture']).read_text())
        sink = Sink()
        connection = _SessionConnection.__new__(_SessionConnection)
        connection.process = SimpleNamespace(stdin=sink)
        await connection._send({'id': 2, 'method': 'turn/start', 'params': turn})
        assert len(sink.raw) == 1
        raw = sink.raw[0]
        assert len(raw) == row['turn_start_rpc_bytes_including_newline']
        assert hashlib.sha256(raw).hexdigest() == row['turn_start_rpc_sha256']
        assert json.loads(raw)['params'] == turn
        results.append({'case': row['case'], 'exact_bytes': len(raw)})
    assert len(results) == 6
    return results


def main():
    manifest_path = STAGE / 'MANIFEST_010.json'
    assert fingerprint(manifest_path)['sha256'] == 'e1803d714cb736a2a6daf062ed7ede12eb0af4a97a39c3949fa19669b239bd59'
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest.items():
        assert fingerprint(STAGE / name) == expected, name
    pin_manifest = json.loads((PIN / 'PIN_MANIFEST.json').read_text())
    for name, expected in pin_manifest.items():
        assert fingerprint(PIN / name) == expected, name
    sources = json.loads((STAGE / 'SOURCE_RECEIPT_010.json').read_text())
    rebuilt = HERE / 'root_reconstructed_010'
    rebuilt.mkdir()
    baseline = json.loads((STAGE / 'BASELINE_004.json').read_text())
    for name, expected in baseline.items():
        original = STAGE / 'baseline' / name
        assert fingerprint(original) == expected, name
        destination = rebuilt / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(original.read_bytes())
    applied = subprocess.run(['patch', '-p1', '--batch', '-i', str(STAGE / 'IMPLEMENTATION_010.patch')],
                             cwd=rebuilt, capture_output=True, text=True)
    assert applied.returncode == 0, applied.stdout + applied.stderr
    for name, expected in sources['files'].items():
        for base in (rebuilt, PIN, STAGE / 'snapshot_010', ROOT):
            assert fingerprint(base / name) == expected, (str(base), name)
    assert fingerprint(STAGE / 'IMPLEMENTATION_010.patch') == sources['patch']
    # Independently compare every original scientific TASK constant with its
    # current definition. Imported TASK source modules are outside this patch.
    constants = {}
    for name in ('literature_experimental_prompt.py', 'literature_reference_parent_prompt.py'):
        def tasks(base):
            tree = ast.parse((base / 'gene_annotation_episode' / name).read_text())
            return {node.targets[0].id: node.value.value for node in tree.body
                    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id.endswith('_TASK') and isinstance(node.value, ast.Constant)}
        before, after = tasks(STAGE / 'baseline'), tasks(PIN)
        assert before and before == after, name
        constants[name] = {key: hashlib.sha256(value.encode()).hexdigest() for key, value in before.items()}
    wire = asyncio.run(verify_wire())
    imports = {name: str(Path(module.__file__).resolve().relative_to(PIN.resolve()))
               for name, module in tuple(sys.modules.items())
               if name.startswith(('gene_annotation_episode', 'method_loop')) and getattr(module, '__file__', None)}
    receipt = {'scope': 'Mechanical source/package/constant/wire verification only; no configured model or scientific source.',
               'manifest_entries': len(manifest), 'pin_entries': len(pin_manifest),
               'source_files_reconstructed_independently': len(sources['files']),
               'live_owned_source_matches_frozen_generation': True,
               'scientific_TASK_constants': constants, 'exact_wire_cases': wire,
               'imports_from_pin': len(imports), 'historical_run_opened': False}
    with (HERE / 'CONNECTED_DELIVERY_ROOT_RECEIPT_010.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
