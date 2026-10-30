"""Freeze this controlled verification's code, then execute its owned worker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
EXPECTED = {
    'gene_annotation_episode/literature_episodes.py': '49781a1f2990fea993e391b72e9d02c455e94d40c8aba32e1b40962bdc57ce51',
    'gene_annotation_episode/literature_kinetic_calculations.py': '1ca423165e40b99140bb1a1b431081e240d1ae788f7b5d933823817a6c397f50',
    'gene_annotation_episode/literature_kinetic_inputs.py': '1176033e44bb7e2ff065aecd6f1d335fbcab531069e99490cd293dd8a8edb844',
    'gene_annotation_episode/literature_kinetic_storage.py': '1af09288ff81d8839605f0c4cbfb063af2a831587676bb8d00af50d2bee49d16',
    'gene_annotation_episode/literature_kinetic_validation.py': '2f21acdab795ba3917d3ce8202d0621c5c222e64cc75f7823a1f31a92d6e71c2',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_name')
    args = parser.parse_args()
    assert args.run_name.startswith('controlled_') and '/' not in args.run_name
    run = OUT / args.run_name
    run.mkdir(exist_ok=False)
    pin = run / 'pin'
    pin.mkdir()
    files = {}
    for directory in ('gene_annotation_episode', 'method_loop'):
        for path in sorted((ROOT / directory).rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            relative = path.relative_to(ROOT).as_posix()
            raw = path.read_bytes()
            target = pin / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            files[relative] = {'source': str(path), 'bytes': len(raw), 'sha256': digest(raw)}
    for source, relative in ((ROOT / 'tests/test_runtime.py', 'test_runtime.py'),
                             (OUT / 'run_example.py', 'run_example.py'),
                             (Path(__file__), 'launch_example.py')):
        raw = source.read_bytes()
        (pin / relative).write_bytes(raw)
        files[relative] = {'source': str(source), 'bytes': len(raw), 'sha256': digest(raw)}
    for relative, expected in EXPECTED.items():
        assert files[relative]['sha256'] == expected, relative
    for relative, row in files.items():
        assert digest(Path(row['source']).read_bytes()) == row['sha256'], relative
        assert digest((pin / relative).read_bytes()) == row['sha256'], relative
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(), 'files': files,
                'meaning': 'Immutable code generation for controlled primary-source verification; not an actual configured-model run'}
    (run / 'PIN_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    command = [sys.executable, '-B', str(pin / 'run_example.py'),
               '--repository-root', str(ROOT), '--run-directory', str(run)]
    environment = {**os.environ, 'PYTHONPATH': str(pin), 'PYTHONDONTWRITEBYTECODE': '1'}
    started = datetime.now(timezone.utc).isoformat()
    with (run / 'TERMINAL.log').open('xb') as log:
        result = subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
    for relative, row in files.items():
        assert digest((pin / relative).read_bytes()) == row['sha256'], relative
    receipt = {'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
               'command': command, 'exit_code': result.returncode,
               'pin_manifest_sha256': digest((run / 'PIN_MANIFEST.json').read_bytes()),
               'pin_files_verified': len(files), 'pin_unchanged': True,
               'controlled_provider_and_controller': True, 'configured_model_run': False}
    (run / 'TERMINAL_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'run_directory': str(run), 'exit_code': result.returncode,
                      'pin_files_verified': len(files)}))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
