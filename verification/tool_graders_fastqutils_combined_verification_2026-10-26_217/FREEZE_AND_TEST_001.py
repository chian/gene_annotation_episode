"""Verify exact composed bytes, relocate retained fixtures, run all 20 suites once."""
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
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'verification/tool_graders_fastqutils_combined_2026-10-25_216'
SOURCE = BASE / 'candidate_003'
FROZEN = HERE / 'candidate'
PREVIOUS = ROOT / 'verification/tool_graders_fastqutils_cutadapt_verification_2026-10-25_208'
NATIVE_TREES = ('native_examples_001', 'parser_205/native_examples_001',
                'parser_205/native_examples_002', 'parser_205/native_examples_003')
MEMORY = 20 * 1024**3
SCRATCH = 4 * 1024**3


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def usage():
    return sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY, MEMORY))
    resource.setrlimit(resource.RLIMIT_FSIZE, (SCRATCH, SCRATCH))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    started = time.monotonic()
    before = json.loads((BASE / 'combined_source_before_003.json').read_text())
    tracked = {}
    receipt = dict(passed=False, started_at=datetime.now(timezone.utc).isoformat(),
        source_manifest_sha256=sha(BASE / 'combined_source_before_003.json'),
        memory_limit_bytes=MEMORY, aggregate_scratch_limit_bytes=SCRATCH, wall_time_limit=None,
        live_acquisition=False, native_producer_executed=False, host_or_Workflow_verified=False,
        suite_runs=0, deselections=[])
    try:
        assert len(before) == 1176 and snapshot(SOURCE) == before
        save('source_before.json', before)
        FROZEN.mkdir(exist_ok=False)
        for name, digest in before.items():
            src = SOURCE / name
            dest = FROZEN / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            assert sha(dest) == digest
        relocations = []
        for tree in NATIVE_TREES:
            for src in sorted((PREVIOUS / tree).rglob('*')):
                if not src.is_file():
                    continue
                assert not src.is_symlink()
                dest = HERE / src.relative_to(PREVIOUS)
                dest.parent.mkdir(parents=True, exist_ok=True)
                digest = sha(src)
                shutil.copyfile(src, dest)
                assert sha(dest) == digest
                tracked[str(src)] = tracked[str(dest)] = digest
                relocations.append(dict(source=str(src), destination=str(dest), sha256=digest))
        for relative in (
            'verification/tool_graders_bvbrc_fastqutils_remaining_formats_2026-10-25_204/native_examples_001/trimgalore_single',
            'verification/tool_graders_bvbrc_fastqutils_implementation_2026-10-25_198/evidence_c/integration_handoff_002',
        ):
            for src in sorted((ROOT / relative).rglob('*')):
                if src.is_file() and '__pycache__' not in src.parts:
                    tracked[str(src)] = sha(src)
        save('native_fixture_relocation.json', relocations)
        save('all_inputs_before.json', tracked)
        tests = sorted(FROZEN.glob('tests/test_bvbrc_fastqutils*.py'))
        assert len(tests) == 20
        (HERE / 'runtime_tmp').mkdir(exist_ok=False)
        (HERE / 'test_tmp').mkdir(exist_ok=False)
        # Isolated Python with only this exact verified candidate injected.
        code = ('import sys,json,pathlib,pytest; '
                'sys.path.insert(0,sys.argv.pop(1)); '
                'out=pathlib.Path(sys.argv.pop(1)); '
                'status=pytest.main(sys.argv[1:]); '
                'origins={n:str(pathlib.Path(m.__file__).resolve()) for n,m in sys.modules.items() '
                'if n.split(".")[0] in ("gene_annotation_episode","method_loop") and getattr(m,"__file__",None)}; '
                'out.write_text(json.dumps(origins,indent=2,sort_keys=True)+"\\n"); '
                'raise SystemExit(status)')
        argv = [sys.executable, '-I', '-B', '-c', code, str(FROZEN), str(HERE / 'suite_import_origins.json'),
                '-v', '-p', 'no:cacheprovider', '--basetemp', str(HERE / 'test_tmp'),
                '--junitxml', str(HERE / 'suite_results.xml'), *map(str, tests)]
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                           PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', TMPDIR=str(HERE / 'runtime_tmp'))
        environment.pop('PYTHONPATH', None)
        save('suite_command.json', dict(argv=argv, cwd=str(FROZEN), test_files=[p.name for p in tests],
            environment_overrides={key: environment.get(key) for key in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE',
                'PYTEST_DISABLE_PLUGIN_AUTOLOAD', 'TMPDIR')},
            memory_limit_bytes=MEMORY, aggregate_scratch_limit_bytes=SCRATCH, wall_time_limit=None))
        peak = usage()
        assert peak < SCRATCH
        with (HERE / 'suite_stdout.log').open('x') as stdout, (HERE / 'suite_stderr.log').open('x') as stderr:
            process = subprocess.Popen(argv, cwd=FROZEN, env=environment, stdout=stdout, stderr=stderr, preexec_fn=limits)
            receipt['suite_runs'] = 1
            save('suite_started.json', dict(pid=process.pid, started_at=receipt['started_at']))
            while process.poll() is None:
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    peak = max(peak, usage())
                    if peak >= SCRATCH:
                        process.terminate()
                        process.wait()
                        raise RuntimeError('aggregate scratch limit exceeded')
        receipt.update(exit_code=process.returncode, peak_observed_scratch_bytes=max(peak, usage()))
        origins = json.loads((HERE / 'suite_import_origins.json').read_text())
        wrong = {n: p for n, p in origins.items() if not Path(p).is_relative_to(FROZEN / n.split('.')[0])}
        assert not wrong, wrong
        cases = []
        for node in ET.parse(HERE / 'suite_results.xml').getroot().iter('testcase'):
            failures = [dict(kind=c.tag, message=c.attrib.get('message'), text=c.text) for c in node
                        if c.tag in ('failure', 'error', 'skipped')]
            cases.append(dict(classname=node.attrib['classname'], name=node.attrib['name'],
                              seconds=float(node.attrib.get('time', 0)), outcomes=failures))
        save('distinct_test_cases.json', cases)
        identities = {(row['classname'], row['name']) for row in cases}
        assert len(identities) == len(cases)
        receipt.update(distinct_test_cases=len(cases), test_files=len(tests),
            failures=sum(any(o['kind'] == 'failure' for o in r['outcomes']) for r in cases),
            errors=sum(any(o['kind'] == 'error' for o in r['outcomes']) for r in cases),
            skipped=sum(any(o['kind'] == 'skipped' for o in r['outcomes']) for r in cases),
            imported_modules=len(origins), passed=process.returncode == 0)
    except BaseException as error:
        receipt.update(passed=False, error_type=type(error).__name__, error=str(error))
        (HERE / 'suite_error.log').write_text(traceback.format_exc())
    finally:
        source_after = snapshot(SOURCE)
        candidate_after = snapshot(FROZEN)
        tracked_after = {name: sha(Path(name)) if Path(name).is_file() else None for name in tracked}
        save('source_after_suite.json', source_after)
        save('candidate_after_suite.json', candidate_after)
        save('all_inputs_after_suite.json', tracked_after)
        changed = {kind: sorted(name for name in first.keys() | last.keys() if first.get(name) != last.get(name))
                   for kind, first, last in [('source', before, source_after), ('candidate', before, candidate_after),
                                             ('inputs', tracked, tracked_after)]}
        receipt.update(changed=changed, source_count=len(before), scratch_bytes=usage(),
            child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            elapsed_seconds=time.monotonic() - started, ended_at=datetime.now(timezone.utc).isoformat(),
            harness_sha256=sha(Path(__file__)))
        receipt['passed'] = receipt['passed'] and not any(changed.values()) and receipt['scratch_bytes'] < SCRATCH
        save('suite_receipt.json', receipt)
        print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
