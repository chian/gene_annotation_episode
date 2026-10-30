"""Build/install exact composed source offline and verify independent wheel imports."""
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
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'verification/tool_graders_fastqutils_combined_2026-10-25_216/candidate_003'
FROZEN = HERE / 'candidate'
OUT = HERE / 'package_verification_001'
PREVIOUS = ROOT / 'verification/tool_graders_fastqutils_cutadapt_verification_2026-10-25_208'
LEGACY = ROOT / 'verification/tool_graders_bvbrc_fastqutils_implementation_2026-10-25_198/evidence_c/integration_handoff_002'
LEGACY_SCHEMA = ROOT / 'verification/tool_graders_bvbrc_fastqutils_implementation_2026-10-25_198/return_revision_002/candidate/gene_annotation_episode/bvbrc_fastqutils_schemas.json'
OLD208_SCHEMA = PREVIOUS / 'candidate/gene_annotation_episode/bvbrc_fastqutils_schemas.json'
SETUPTOOLS_WHEEL = PREVIOUS / 'package_verification_001/pip_cache/http-v2/6/f/5/8/3/6f58315105f89fee1362c31502969537488db877c79a9478a63bd668.body'
MEMORY = 20 * 1024**3
SCRATCH = 4 * 1024**3


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def usage():
    return sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY, MEMORY))
    resource.setrlimit(resource.RLIMIT_FSIZE, (SCRATCH, SCRATCH))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    OUT.mkdir(exist_ok=False)
    before = json.loads((HERE / 'source_before.json').read_text())
    scripts = [Path(__file__), PREVIOUS / 'PACKAGE_FIXTURE_001.py', PREVIOUS / 'PACKAGE_PROBE_001.py',
               HERE / 'EXTRA_PACKAGE_FIXTURE_001.py', HERE / 'EXTRA_PACKAGE_PROBE_001.py']
    tracked = json.loads((HERE / 'all_inputs_before.json').read_text())
    for p in [LEGACY_SCHEMA, OLD208_SCHEMA, SETUPTOOLS_WHEEL, *scripts,
              PREVIOUS / 'package_verification_001/specimen/provider_cases.json']:
        tracked[str(p)] = sha(p)
    save('all_inputs_before.json', tracked)
    receipt = dict(passed=False, started_at=datetime.now(timezone.utc).isoformat(),
        source_count=len(before), memory_limit_bytes=MEMORY, aggregate_scratch_limit_bytes=SCRATCH,
        wall_time_limit=None, live_acquisition=False, native_producer_executed=False,
        host_or_Workflow_verified=False, build_network_allowed=False, phase_runs={})
    started = time.monotonic()
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PIP_DISABLE_PIP_VERSION_CHECK='1',
        PIP_NO_INDEX='1', PIP_NO_CACHE_DIR='1', TMPDIR=str(OUT / 'tmp'), PIP_CACHE_DIR=str(OUT / 'pip_cache'))
    environment.pop('PYTHONPATH', None)
    (OUT / 'tmp').mkdir()
    peak = usage()

    def run(name, argv, cwd=OUT):
        nonlocal peak
        save(name + '_command.json', dict(argv=argv, cwd=str(cwd),
            environment_overrides={k: environment.get(k) for k in ('PYTHONDONTWRITEBYTECODE', 'PIP_DISABLE_PIP_VERSION_CHECK',
                'PIP_NO_INDEX', 'PIP_NO_CACHE_DIR', 'TMPDIR', 'PIP_CACHE_DIR', 'PYTHONPATH')},
            memory_limit_bytes=MEMORY, aggregate_scratch_limit_bytes=SCRATCH, wall_time_limit=None))
        tick = time.monotonic()
        assert usage() < SCRATCH
        with (OUT / (name + '_stdout.log')).open('x') as stdout, (OUT / (name + '_stderr.log')).open('x') as stderr:
            process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=stdout, stderr=stderr, preexec_fn=limits)
            receipt['phase_runs'][name] = 1
            save(name + '_started.json', dict(pid=process.pid, started_at=datetime.now(timezone.utc).isoformat()))
            while process.poll() is None:
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    peak = max(peak, usage())
                    if peak >= SCRATCH:
                        process.terminate()
                        process.wait()
                        raise RuntimeError('aggregate scratch limit exceeded')
        receipt[name + '_exit_code'] = process.returncode
        receipt[name + '_elapsed_seconds'] = time.monotonic() - tick
        assert process.returncode == 0, name + ' failed; exact logs retained'

    try:
        assert snapshot(SOURCE) == before == snapshot(FROZEN)
        assert {name: sha(Path(name)) for name in tracked} == tracked
        assert sha(FROZEN / 'gene_annotation_episode/bvbrc_fastqutils_legacy_v2_schemas.json') == sha(LEGACY_SCHEMA)
        assert sha(FROZEN / 'gene_annotation_episode/bvbrc_fastqutils_legacy_cutadapt_schemas.json') == sha(OLD208_SCHEMA)
        receipt['historical_schema_hashes'] = dict(original198=sha(LEGACY_SCHEMA), exact208=sha(OLD208_SCHEMA))
        build_source = OUT / 'build_source'
        for name, digest in before.items():
            dest = build_source / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(FROZEN / name, dest)
            assert sha(dest) == digest
        build_wheels = OUT / 'build_dependencies'
        build_wheels.mkdir()
        with zipfile.ZipFile(SETUPTOOLS_WHEEL) as archive:
            metadata_name, = [n for n in archive.namelist() if n.startswith('setuptools-') and n.endswith('.dist-info/METADATA')]
            version = metadata_name.split('/')[0].removeprefix('setuptools-').removesuffix('.dist-info')
        cached = build_wheels / ('setuptools-' + version + '-py3-none-any.whl')
        shutil.copyfile(SETUPTOOLS_WHEEL, cached)
        receipt['build_dependency'] = dict(source=str(SETUPTOOLS_WHEEL), sha256=sha(cached), version=version)
        specimen = OUT / 'specimen'
        specimen.mkdir()
        run('fixture208_approach', [sys.executable, '-I', '-B', str(PREVIOUS / 'PACKAGE_FIXTURE_001.py'),
            str(FROZEN), str(specimen), str(LEGACY)])
        fixture = json.loads((OUT / 'fixture208_approach_stdout.log').read_text())
        assert fixture['dependency_count'] == 36
        save('fixture_result.json', fixture)
        run('fixture_new_modes', [sys.executable, '-I', '-B', str(HERE / 'EXTRA_PACKAGE_FIXTURE_001.py'),
            str(FROZEN), str(specimen), str(PREVIOUS / 'package_verification_001/specimen')])
        specimen_before = snapshot(specimen)
        save('specimen_before.json', specimen_before)
        run('build', [sys.executable, '-I', '-B', '-m', 'pip', 'wheel', '--no-deps', '--no-index',
            '--find-links', str(build_wheels), '--wheel-dir', str(OUT / 'wheel'), str(build_source)])
        wheels = list((OUT / 'wheel').glob('*.whl'))
        assert len(wheels) == 1
        wheel = wheels[0]
        meta = json.loads((specimen / 'meta.json').read_text())
        required = {'gene_annotation_episode/' + n for n in meta['dependency_order']}
        required |= {'gene_annotation_episode/bvbrc_fastqutils_returns.py', 'gene_annotation_episode/bvbrc_fastqutils_tool_info.py'}
        assert len(meta['dependency_order']) == 36
        packaged = {}
        with zipfile.ZipFile(wheel) as archive:
            assert len(set(archive.namelist())) == len(archive.namelist())
            assert required <= set(archive.namelist())
            for name in archive.namelist():
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
                if name.startswith(('gene_annotation_episode/', 'method_loop/')) and not name.endswith('/'):
                    digest = hashlib.sha256(archive.read(name)).hexdigest()
                    assert before.get(name) == digest, name
                    packaged[name] = digest
        save('packaged_hashes.json', packaged)
        installed = OUT / 'installed_wheel'
        run('install', [sys.executable, '-I', '-B', '-m', 'pip', 'install', '--no-deps', '--no-index',
            '--no-compile', '--target', str(installed), str(wheel)])
        installed_hashes = {name: sha(installed / name) for name in packaged}
        assert installed_hashes == packaged
        save('installed_hashes.json', installed_hashes)
        receipt.update(wheel_sha256=sha(wheel), wheel_path=str(wheel),
            required_package_inputs=sorted(required), packaged_source_asset_count=len(packaged),
            provider_pin=fixture['provider_pin'], dependency_count=36)
        run('installed_original', [sys.executable, '-I', '-B', str(PREVIOUS / 'PACKAGE_PROBE_001.py'),
            str(installed), str(specimen)])
        original = json.loads((OUT / 'installed_original_stdout.log').read_text())
        save('installed_original_result.json', original)
        assert original['provider_pin'] == fixture['provider_pin']
        run('installed_new_modes', [sys.executable, '-I', '-B', str(HERE / 'EXTRA_PACKAGE_PROBE_001.py'),
            str(installed), str(specimen)])
        new = json.loads((OUT / 'installed_new_modes_stdout.log').read_text())
        save('installed_new_modes_result.json', new)
        assert new['provider_pin'] == fixture['provider_pin']
        specimen_after = snapshot(specimen)
        save('specimen_after.json', specimen_after)
        assert specimen_before == specimen_after
        assert {name: sha(installed / name) for name in packaged} == packaged
        receipt.update(passed=True, original_answers=original['legacy_numbers'],
            cutadapt_answers=original['native_numbers'],
            samstat_answers={family: [[r['numerator'], r['denominator']] for r in new['numerical'][family]['components']]
                            for family in ('legacy', 'current', 'changed_R1')},
            sra_answers={k: v['value'] for k, v in new['numerical']['sra']['measurements'].items()},
            forbidden_call_count=original['forbidden_call_count'] + new['forbidden_call_count'],
            isolated_import_count=len(set(original['isolated_origins']) | set(new['isolated_origins'])),
            same_parameter_saved_recalculation=True, changed_parameters_preserve_original=True,
            saved_return_without_calculators=True)
    except BaseException as error:
        receipt.update(passed=False, error_type=type(error).__name__, error=str(error))
        (OUT / 'error.log').write_text(traceback.format_exc())
    finally:
        after = {name: sha(Path(name)) if Path(name).is_file() else None for name in tracked}
        source_after, candidate_after = snapshot(SOURCE), snapshot(FROZEN)
        save('all_inputs_after.json', after)
        save('source_after.json', source_after)
        save('candidate_after.json', candidate_after)
        build_after = {name: sha(OUT / 'build_source' / name) if (OUT / 'build_source' / name).is_file() else None for name in before}
        save('build_source_after.json', build_after)
        changed = {kind: sorted(k for k in first.keys() | last.keys() if first.get(k) != last.get(k))
            for kind, first, last in [('inputs', tracked, after), ('source', before, source_after),
                                     ('candidate', before, candidate_after), ('build_source', before, build_after)]}
        receipt.update(changed=changed, peak_observed_scratch_bytes=max(peak, usage()), scratch_bytes=usage(),
            child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            elapsed_seconds=time.monotonic() - started, ended_at=datetime.now(timezone.utc).isoformat(),
            script_hashes={str(p): sha(p) for p in scripts})
        receipt['passed'] = receipt['passed'] and not any(changed.values()) and receipt['scratch_bytes'] < SCRATCH
        save('receipt.json', receipt)
        print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
