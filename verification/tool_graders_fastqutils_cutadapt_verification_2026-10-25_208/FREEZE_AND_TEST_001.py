"""Freeze the contracted inputs and run the unchanged FastqUtils suite once."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUT = ROOT / 'verification/tool_graders_bvbrc_fastqutils_remaining_formats_2026-10-25_204'
SOURCE = INPUT / 'candidate'
FROZEN = HERE / 'candidate'
OVERLAYS = ['communication.py', 'episode_return_records.py', 'bvbrc_proteome_returns.py', 'bvbrc_genome_alignment_sheet.py']
NATIVE = ['native_examples_001', 'parser_205/native_examples_001', 'parser_205/native_examples_002', 'parser_205/native_examples_003']
ORACLES = ROOT / 'verification/tool_graders_bvbrc_fastqutils_implementation_2026-10-25_198/evidence_c/integration_handoff_002'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def transient(path):
    return any(part in ('__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'build', 'dist')
               or part.endswith('.egg-info') for part in path.parts) or path.suffix in ('.pyc', '.pyo')


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))


def main():
    started = time.monotonic()
    receipt = dict(started_at=datetime.now(timezone.utc).isoformat(), passed=False,
        no_wall_time_limit=True, memory_limit_bytes=20 * 1024**3, scratch_budget_bytes=4 * 1024**3,
        live_bvbrc_verified=False, episode_host_custody_verified=False,
        qualification='Unmodified candidate test suite; retained native producers and synthetic/provider/codec fixtures remain distinct.')
    tracked = {}
    frozen = {}
    try:
        FROZEN.mkdir(exist_ok=False)
        source_paths = [p for p in sorted(SOURCE.rglob('*')) if p.is_file() and not transient(p.relative_to(SOURCE))]
        save('excluded_transients.json', [str(p.relative_to(SOURCE)) for p in sorted(SOURCE.rglob('*'))
            if p.is_file() and transient(p.relative_to(SOURCE))])
        source_before = {str(p.relative_to(SOURCE)): sha(p) for p in source_paths}
        save('input_candidate_before.json', source_before)
        for path in source_paths:
            name = path.relative_to(SOURCE)
            target = FROZEN / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            assert sha(target) == source_before[str(name)], str(name)
            tracked[str(path)] = source_before[str(name)]
        overlay_rows = []
        for name in OVERLAYS:
            path = ROOT / 'gene_annotation_episode' / name
            target = FROZEN / 'gene_annotation_episode' / name
            before = sha(target)
            tracked[str(path)] = sha(path)
            shutil.copyfile(path, target)
            overlay_rows.append(dict(path=str(target.relative_to(FROZEN)), source=str(path),
                before_sha256=before, after_sha256=sha(target)))
        save('overlays.json', overlay_rows)
        assert sha(FROZEN / 'gene_annotation_episode/bvbrc_fastqutils_cutadapt_reader.py') == '1237535586dfc9f08510586901f09f01d78c6064fb0da78f8e736fea679da882'
        assert sha(FROZEN / 'tests/test_bvbrc_fastqutils_cutadapt_reader.py') == 'bf75b0a89543006afc3fe2edb854f77ff8e777ba4caf810dc7768f0d845dbd47'
        native_rows = []
        for tree in NATIVE:
            for path in sorted((INPUT / tree).rglob('*')):
                if not path.is_file():
                    continue
                assert not path.is_symlink()
                target = HERE / path.relative_to(INPUT)
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = sha(path)
                shutil.copyfile(path, target)
                assert sha(target) == digest
                tracked[str(path)] = digest
                tracked[str(target)] = digest
                native_rows.append(dict(source=str(path), destination=str(target), sha256=digest))
        save('native_fixture_relocation.json', native_rows)
        for path in sorted(ORACLES.rglob('*')):
            if path.is_file() and not transient(path.relative_to(ORACLES)):
                tracked[str(path)] = sha(path)
        for path in sorted(FROZEN.rglob('*')):
            if path.is_file():
                frozen[str(path.relative_to(FROZEN))] = sha(path)
                tracked[str(path)] = sha(path)
        save('source_before.json', frozen)
        save('all_inputs_before.json', tracked)
        tests = sorted(FROZEN.glob('tests/test_bvbrc_fastqutils_*.py'))
        assert len(tests) == 14, [p.name for p in tests]
        receipt.update(source_count=len(frozen), native_fixture_files=len(native_rows),
            tracked_input_files=len(tracked), test_files=[str(p.relative_to(FROZEN)) for p in tests],
            harness_sha256=sha(Path(__file__)))
        for directory in ('test_tmp', 'runtime_tmp'):
            (HERE / directory).mkdir(exist_ok=False)
        argv = [sys.executable, '-I', '-B', '-c',
            'import sys,pytest; sys.path.insert(0,sys.argv.pop(1)); raise SystemExit(pytest.main(sys.argv[1:]))',
            str(FROZEN), '-v', '-p', 'no:cacheprovider', '--basetemp', str(HERE / 'test_tmp'),
            '--junitxml', str(HERE / 'suite_results.xml'), *[str(p) for p in tests]]
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(HERE / 'runtime_tmp'))
        environment.pop('PYTHONPATH', None)
        save('suite_command.json', dict(argv=argv, cwd=str(FROZEN), environment_overrides={
            'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(HERE / 'runtime_tmp'), 'PYTHONPATH': None},
            limits={'address_space_bytes': 20 * 1024**3, 'file_size_bytes': 4 * 1024**3, 'wall_seconds': None}))
        save('suite_started.json', receipt)
        with (HERE / 'suite_stdout.log').open('x') as stdout, (HERE / 'suite_stderr.log').open('x') as stderr:
            result = subprocess.run(argv, cwd=FROZEN, env=environment, stdout=stdout, stderr=stderr, preexec_fn=limits)
        receipt.update(exit_code=result.returncode, passed=result.returncode == 0)
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error), passed=False)
        (HERE / 'freeze_or_suite_error.log').write_text(traceback.format_exc())
    finally:
        after = {name: sha(Path(name)) if Path(name).is_file() else None for name in tracked}
        save('all_inputs_after_suite.json', after)
        changed = [name for name in tracked if tracked[name] != after[name]]
        receipt.update(changed_inputs=changed, ended_at=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=time.monotonic() - started,
            scratch_bytes=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file()))
        receipt['passed'] = receipt['passed'] and not changed and receipt['scratch_bytes'] < 4 * 1024**3
        save('suite_receipt.json', receipt)
        print(json.dumps(receipt))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
