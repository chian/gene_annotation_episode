"""Freeze accepted054 and replay original051001 nominations in a fresh generation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
EXPECTED = {
    'gene_annotation_episode/literature_episodes.py': '49781a1f2990fea993e391b72e9d02c455e94d40c8aba32e1b40962bdc57ce51',
    'gene_annotation_episode/literature_kinetic_calculations.py': '1ca423165e40b99140bb1a1b431081e240d1ae788f7b5d933823817a6c397f50',
    'gene_annotation_episode/literature_kinetic_inputs.py': '1176033e44bb7e2ff065aecd6f1d335fbcab531069e99490cd293dd8a8edb844',
    'gene_annotation_episode/literature_kinetic_storage.py': '599606c6e40f00e587934b0a7fcd1c550b46253974dd5b123cfdde228245759e',
    'gene_annotation_episode/literature_kinetic_validation.py': '2f21acdab795ba3917d3ce8202d0621c5c222e64cc75f7823a1f31a92d6e71c2',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preserved_files():
    names = set(json.loads((OUT / 'FINAL_MANIFEST_001.json').read_bytes()))
    names.add('FINAL_MANIFEST_001.json')
    names.update(p.relative_to(OUT).as_posix() for p in (OUT / 'controlled_005').rglob('*') if p.is_file())
    return {name: digest(OUT / name) for name in sorted(names)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_name')
    args = parser.parse_args()
    assert args.run_name.startswith('controlled_long_') and '/' not in args.run_name
    run = OUT / args.run_name
    run.mkdir(exist_ok=False)
    original_preserved = preserved_files()
    pin = run / 'pin'
    pin.mkdir()
    files = {}
    def capture(source, relative):
        raw = source.read_bytes()
        target = pin / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        files[relative] = {'source': str(source), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    for directory in ('gene_annotation_episode', 'method_loop'):
        for path in sorted((ROOT / directory).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                capture(path, path.relative_to(ROOT).as_posix())
    for source, relative in (
        (ROOT / 'tests/test_runtime.py', 'test_runtime.py'),
        (OUT / 'controlled_005/pin/run_example.py', 'baseline_worker_005.py'),
        (OUT / 'controlled_001/SOURCE_SELECTIONS.json', 'original_source_selections_001.json'),
        (OUT / 'run_long_witness_002.py', 'run_long_witness_002.py'),
        (Path(__file__), 'launch_long_witness_002.py')):
        capture(source, relative)
    assert files['baseline_worker_005.py']['sha256'] == '8426e1cf2e2e607811223bed9b3cbc932e226fcc3a826ce81130be19ea5caefb'
    assert files['original_source_selections_001.json']['sha256'] == '1e73fb702008af86c36edc64444b346e150cb1d541594d316f0e228e4e29bb9f'
    for relative, expected in EXPECTED.items():
        assert files[relative]['sha256'] == expected, relative
    for relative, row in files.items():
        assert digest(Path(row['source'])) == row['sha256'], relative
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(), 'files': files,
        'meaning': 'Controlled same-case original-long-witness publication verification with accepted054; not configured-model science'}
    (run / 'PIN_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (run / 'PRESERVATION_BEFORE.json').write_text(json.dumps(original_preserved, indent=2) + '\n')
    command = [sys.executable, '-B', str(pin / 'run_long_witness_002.py'),
               '--repository-root', str(ROOT), '--run-directory', str(run)]
    environment = {**os.environ, 'PYTHONPATH': str(pin), 'PYTHONDONTWRITEBYTECODE': '1'}
    started = datetime.now(timezone.utc).isoformat()
    with (run / 'TERMINAL.log').open('xb') as log:
        result = subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
    for relative, row in files.items():
        assert digest(pin / relative) == row['sha256'], relative
    assert preserved_files() == original_preserved
    receipt = {'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'command': command, 'exit_code': result.returncode, 'pin_manifest_sha256': digest(run / 'PIN_MANIFEST.json'),
        'pin_files_verified': len(files), 'pin_unchanged': True,
        'old_manifest_001_and_controlled005_files_verified': len(original_preserved),
        'old_manifest_and_controlled005_preserved': True, 'configured_model_run': False}
    (run / 'TERMINAL_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'run_directory': str(run), 'exit_code': result.returncode,
                      'pin_files_verified': len(files), 'old_files_preserved': len(original_preserved)}))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
