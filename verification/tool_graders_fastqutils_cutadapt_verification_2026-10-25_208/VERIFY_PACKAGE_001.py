"""Build the exact frozen candidate and verify the isolated extracted wheel."""
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
FROZEN = HERE / 'candidate'
OUT = HERE / 'package_verification_001'
LEGACY = ROOT / 'verification/tool_graders_bvbrc_fastqutils_implementation_2026-10-25_198/evidence_c/integration_handoff_002'
LEGACY_SCHEMA = ROOT / 'verification/tool_graders_bvbrc_fastqutils_implementation_2026-10-25_198/return_revision_002/candidate/gene_annotation_episode/bvbrc_fastqutils_schemas.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))


def main():
    OUT.mkdir(exist_ok=False)
    before = json.loads((HERE / 'source_before.json').read_text())
    tracked = json.loads((HERE / 'all_inputs_before.json').read_text())
    tracked[str(LEGACY_SCHEMA)] = sha(LEGACY_SCHEMA)
    scripts = [Path(__file__), HERE / 'PACKAGE_FIXTURE_001.py', HERE / 'PACKAGE_PROBE_001.py']
    tracked.update({str(p): sha(p) for p in scripts})
    save('all_inputs_before.json', tracked)
    save('source_before.json', before)
    receipt = dict(started_at=datetime.now(timezone.utc).isoformat(), passed=False,
        source_count=len(before), no_wall_time_limit=True,
        memory_limit_bytes=20 * 1024**3, scratch_budget_bytes=4 * 1024**3,
        host_custody_verified=False, live_service_execution_verified=False,
        qualification='Built wheel using isolated build dependencies; retained native bytes and synthetic provider/codec envelopes; no episode-host or live-service claim.')
    started = time.monotonic()
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PIP_DISABLE_PIP_VERSION_CHECK='1',
        TMPDIR=str(OUT / 'build_tmp'), PIP_CACHE_DIR=str(OUT / 'pip_cache'))
    environment.pop('PYTHONPATH', None)
    (OUT / 'build_tmp').mkdir()

    def run(name, argv):
        save(name + '_command.json', dict(argv=argv, cwd=str(OUT),
            environment_overrides={k: environment[k] for k in ('PYTHONDONTWRITEBYTECODE', 'PIP_DISABLE_PIP_VERSION_CHECK', 'TMPDIR', 'PIP_CACHE_DIR')},
            limits=dict(address_space_bytes=20 * 1024**3, file_size_bytes=4 * 1024**3, wall_seconds=None)))
        tick = time.monotonic()
        with (OUT / (name + '_stdout.log')).open('x') as stdout, (OUT / (name + '_stderr.log')).open('x') as stderr:
            result = subprocess.run(argv, cwd=OUT, env=environment, stdout=stdout, stderr=stderr, preexec_fn=limits)
        receipt[name + '_exit_code'] = result.returncode
        receipt[name + '_elapsed_seconds'] = time.monotonic() - tick
        assert result.returncode == 0, name + ' failed; see preserved logs'

    try:
        assert {name: sha(FROZEN / name) for name in before} == before
        assert {name: sha(Path(name)) for name in tracked} == tracked
        assert sha(FROZEN / 'gene_annotation_episode/bvbrc_fastqutils_legacy_v2_schemas.json') == sha(LEGACY_SCHEMA)
        receipt['legacy_schema_sha256'] = sha(LEGACY_SCHEMA)
        build_source = OUT / 'build_source'
        for name, digest in before.items():
            target = build_source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(FROZEN / name, target)
            assert sha(target) == digest, name
        specimen = OUT / 'specimen'
        specimen.mkdir()
        run('fixture', [sys.executable, '-I', '-B', str(HERE / 'PACKAGE_FIXTURE_001.py'), str(FROZEN), str(specimen), str(LEGACY)])
        fixture = json.loads((OUT / 'fixture_stdout.log').read_text())
        save('fixture_result.json', fixture)
        specimen_before = {str(p.relative_to(specimen)): sha(p) for p in sorted(specimen.rglob('*')) if p.is_file()}
        save('specimen_before.json', specimen_before)
        run('build', [sys.executable, '-I', '-B', '-m', 'pip', 'wheel', '--no-deps', '--wheel-dir', str(OUT / 'wheel'), str(build_source)])
        wheels = list((OUT / 'wheel').glob('*.whl'))
        assert len(wheels) == 1
        wheel = wheels[0]
        required = [name for name in before if name.startswith('gene_annotation_episode/bvbrc_fastqutils_')]
        for new in ('bvbrc_fastqutils_cutadapt_reader.py', 'bvbrc_fastqutils_cutadapt_specs.py', 'bvbrc_fastqutils_legacy_v2_schemas.json'):
            assert 'gene_annotation_episode/' + new in required
        packaged_hashes = {}
        installed = OUT / 'extracted_wheel'
        with zipfile.ZipFile(wheel) as archive:
            assert len(set(archive.namelist())) == len(archive.namelist())
            assert set(required) <= set(archive.namelist())
            for name in archive.namelist():
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
                if name.startswith(('gene_annotation_episode/', 'method_loop/')) and not name.endswith('/'):
                    digest = hashlib.sha256(archive.read(name)).hexdigest()
                    assert digest == before.get(name), name
                    packaged_hashes[name] = digest
            archive.extractall(installed)
        save('packaged_hashes.json', packaged_hashes)
        receipt.update(wheel_sha256=sha(wheel), required_packaged_files=required, fastqutils_asset_count=len(required),
            packaged_source_asset_count=len(packaged_hashes), provider_pin=fixture['provider_pin'], dependency_count=fixture['dependency_count'])
        run('installed', [sys.executable, '-I', '-B', str(HERE / 'PACKAGE_PROBE_001.py'), str(installed), str(specimen)])
        result = json.loads((OUT / 'installed_stdout.log').read_text())
        save('installed_result.json', result)
        assert result['provider_pin'] == fixture['provider_pin']
        specimen_after = {str(p.relative_to(specimen)): sha(p) for p in sorted(specimen.rglob('*')) if p.is_file()}
        save('specimen_after.json', specimen_after)
        assert specimen_before == specimen_after
        receipt.update(passed=True, installed_result_sha256=sha(OUT / 'installed_result.json'),
            native_numbers=result['native_numbers'], native_input_bases=result['native_input_bases'],
            direct_native_answers=result['direct_native_answers'], changed_quality_threshold_fractions=result['changed_quality_threshold_fractions'],
            legacy_numbers=result['legacy_numbers'], rejected_legacy_forms=result['rejected_legacy_forms'],
            import_origin_count=len(result['isolated_origins']), forbidden_call_count=result['forbidden_call_count'])
    except BaseException as error:
        receipt.update(passed=False, error_type=type(error).__name__, error=str(error))
        (OUT / 'error.log').write_text(traceback.format_exc())
    finally:
        after = {name: sha(Path(name)) if Path(name).is_file() else None for name in tracked}
        save('all_inputs_after.json', after)
        frozen_after = {name: sha(FROZEN / name) if (FROZEN / name).is_file() else None for name in before}
        save('source_after.json', frozen_after)
        build_source = OUT / 'build_source'
        build_after = {name: sha(build_source / name) if (build_source / name).is_file() else None for name in before}
        save('build_source_after.json', build_after)
        changes = [name for name in tracked if tracked[name] != after[name]]
        build_changes = [name for name in before if before[name] != build_after[name]]
        receipt.update(changed_inputs=changes, changed_build_sources=build_changes,
            source_manifest_sha256=sha(HERE / 'source_before.json'),
            script_hashes={p.name: sha(p) for p in scripts}, ended_at=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=time.monotonic() - started, max_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            scratch_bytes=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file()))
        receipt['passed'] = receipt['passed'] and not changes and not build_changes and receipt['scratch_bytes'] < 4 * 1024**3
        save('receipt.json', receipt)
        print(json.dumps(receipt))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
