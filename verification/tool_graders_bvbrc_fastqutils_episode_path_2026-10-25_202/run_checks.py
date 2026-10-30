"""Retain immutable run evidence; no time budget, live service, or production edit."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT.parent / 'tool_graders_bvbrc_fastqutils_implementation_2026-10-25_198/candidate'
PYTHON = Path('/home/chia/repos/gene_annotation_episode/.venv/bin/python')
RAM, SCRATCH = 20 * 1024**3, 4 * 1024**3
SOURCE_TREES = ('gene_annotation_episode', 'method_loop', 'tests', 'research/slotted_process_library')
PERFORMANCE_BOUNDARY = ROOT.parent / 'tool_graders_typed_return_performance_2026-10-25_197/APPLICATION_BOUNDARY.json'


def hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(path.rglob('*')) if p.is_file() and '__pycache__' not in p.parts
        and '.pytest_cache' not in p.parts and p.suffix != '.pyc'}


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def candidate_hashes():
    result = {'pyproject.toml': hashlib.sha256((CANDIDATE / 'pyproject.toml').read_bytes()).hexdigest()}
    for name in SOURCE_TREES:
        result.update({name + '/' + key: value for key, value in hashes(CANDIDATE / name).items()})
    return result


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (RAM, RAM))
    resource.setrlimit(resource.RLIMIT_FSIZE, (SCRATCH, SCRATCH))


def compose_performance(source):
    boundary = json.loads(PERFORMANCE_BOUNDARY.read_text())
    expected = {'gene_annotation_episode/' + name for name in
        ('communication.py', 'episode_return_records.py', 'bvbrc_proteome_returns.py')}
    rows = boundary['application_boundary']
    if {row['path'] for row in rows} != expected or len(rows) != 3:
        raise RuntimeError('unexpected performance application boundary')
    changes = []
    for row in rows:
        target, incoming = source / row['path'], Path(row['candidate_file'])
        before = hashlib.sha256(target.read_bytes()).hexdigest()
        after = hashlib.sha256(incoming.read_bytes()).hexdigest()
        if after != row['candidate_sha256'] or before not in {
                row['expected_baseline_sha256'], row['candidate_sha256']}:
            raise RuntimeError('performance composition source mismatch: ' + row['path'])
        shutil.copy2(incoming, target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != after:
            raise RuntimeError('performance source changed while copying: ' + row['path'])
        changes.append(dict(path=row['path'], before_sha256=before, after_sha256=after,
            copied_from=str(incoming), changed=before != after))
    return dict(boundary=str(PERFORMANCE_BOUNDARY),
        boundary_sha256=hashlib.sha256(PERFORMANCE_BOUNDARY.read_bytes()).hexdigest(), files=changes,
        qualification='Root-authorized exact verified197 overlay in this isolated run only; candidate and running snapshots are not modified.')


def add_integration_inputs(source, incoming):
    incoming = incoming.resolve()
    paths = [Path('tests/test_bvbrc_fastqutils_episode_flow.py')]
    for name, expected in (('tests/fixtures/bvbrc_fastqutils/integration', 8),
            ('research/slotted_process_library', 35)):
        files = list(hashes(incoming / name))
        if len(files) != expected:
            raise RuntimeError('integration dependency count changed: ' + name)
        paths.extend(Path(name) / name_in_tree for name_in_tree in files)
    rows = []
    for relative in paths:
        original, target = incoming / relative, source / relative
        value = hashlib.sha256(original.read_bytes()).hexdigest()
        exists = target.exists()
        if exists and hashlib.sha256(target.read_bytes()).hexdigest() != value:
            raise RuntimeError('integration input would overwrite a different base file: ' + str(relative))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != value:
            raise RuntimeError('integration input changed while copying: ' + str(relative))
        rows.append(dict(path=str(relative), incoming_path=str(original), sha256=value,
            bytes=target.stat().st_size, disposition='identical' if exists else 'added'))
    return rows


def dependency_files():
    paths = {PYTHON.resolve(), Path(__file__).resolve()}
    for root in (PYTHON.parent.parent / 'lib/python3.12/site-packages', Path('/usr/lib/python3.12')):
        paths.update(p.resolve() for p in root.rglob('*') if p.is_file()
            and p.suffix in {'.py', '.so'} and '__pycache__' not in p.parts)
    # ldd enumerates the linked dependency closure for each installed extension
    # and the interpreter. These are environment files, not downloaded binaries.
    linked = set()
    for binary in sorted(p for p in paths if p.suffix == '.so' or p == PYTHON.resolve()):
        listing = subprocess.run(['ldd', str(binary)], capture_output=True, text=True, check=False)
        for name in re.findall(r'(?:=>\s+|^\s*)(/\S+)\s+\(', listing.stdout, re.MULTILINE):
            path = Path(name).resolve()
            if path.is_file():
                linked.add(path)
    paths.update(linked)
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    global CANDIDATE
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    parser.add_argument('--select')
    parser.add_argument('--compose-performance', action='store_true')
    parser.add_argument('--base-candidate', type=Path, default=CANDIDATE)
    parser.add_argument('--base-manifest', type=Path)
    parser.add_argument('--integration-source', type=Path)
    args = parser.parse_args()
    CANDIDATE = args.base_candidate.resolve()
    target = ROOT / args.name
    target.mkdir(exist_ok=False)
    original_before = candidate_hashes()
    dump(target / 'candidate_before.json', original_before)
    base_manifest = None
    if args.base_manifest:
        expected = json.loads(args.base_manifest.read_text())
        if original_before != expected:
            raise RuntimeError('base candidate differs from its exact verified source manifest')
        base_manifest = dict(path=str(args.base_manifest.resolve()),
            sha256=hashlib.sha256(args.base_manifest.read_bytes()).hexdigest(), file_count=len(expected))
    dump(target / 'base_provenance.json', dict(candidate=str(CANDIDATE), manifest=base_manifest))
    source = target / 'source'
    source.mkdir()
    for name in SOURCE_TREES:
        if (CANDIDATE / name).exists():
            shutil.copytree(CANDIDATE / name, source / name,
                ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', '*.pyc'))
    shutil.copy2(CANDIDATE / 'pyproject.toml', source / 'pyproject.toml')
    copied = hashes(source)
    if original_before != copied:
        raise RuntimeError('candidate changed during snapshot construction; preserve this run and use a new name')
    supplements = add_integration_inputs(source, args.integration_source) if args.integration_source else []
    dump(target / 'supplementary_inputs.json', supplements)
    composition = compose_performance(source) if args.compose_performance else None
    dump(target / 'composition.json', composition)
    before = hashes(source)
    dump(target / 'source_before.json', before)
    dependencies_before = dependency_files()
    dump(target / 'dependencies_before.json', dependencies_before)
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(source),
        'FASTQUTILS_EXAMPLE_DIRECTORY': str(target / 'examples'), 'TMPDIR': str(target / 'tmp'),
        'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
    (target / 'tmp').mkdir()
    command = [str(PYTHON), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
        '--basetemp=' + str(target / 'pytest-tmp'), '--junitxml=' + str(target / 'junit.xml'),
        'tests/test_bvbrc_fastqutils_episode_flow.py']
    if args.select:
        command += ['-k', args.select]
    started = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    dump(target / 'command.json', dict(command=command, cwd=str(source), start_utc=started,
        environment={key: env[key] for key in ('PYTHONDONTWRITEBYTECODE', 'PYTHONPATH',
            'FASTQUTILS_EXAMPLE_DIRECTORY', 'TMPDIR', 'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS')},
        ram_limit_bytes=RAM, scratch_limit_bytes=SCRATCH, walltime_limit=None,
        scratch_enforcement='bounded fixture data plus final aggregate measurement; 4 GiB per-file process limit'))
    with (target / 'pytest.log').open('w') as log:
        process = subprocess.Popen(command, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT,
            preexec_fn=limits)
        dump(target / 'process.json', dict(pid=process.pid, start_utc=started, command=command))
        print('started', process.pid, target, flush=True)
        code = process.wait()
    after = hashes(source)
    dump(target / 'source_after.json', after)
    dependencies_after = dependency_files()
    dump(target / 'dependencies_after.json', dependencies_after)
    original_after = candidate_hashes()
    dump(target / 'candidate_after.json', original_after)
    changed = [name for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)]
    concurrent = [name for name in sorted(set(original_before) | set(original_after))
        if original_before.get(name) != original_after.get(name)]
    size = sum(p.stat().st_size for p in target.rglob('*') if p.is_file())
    suites = []
    if (target / 'junit.xml').exists():
        suites = [row.attrib for row in ET.parse(target / 'junit.xml').getroot().iter('testsuite')]
    receipt = dict(command=command, cwd=str(source), start_utc=started,
        end_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic()-start,
        exit_code=code, junit=suites, maximum_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        source_file_count=len(before), frozen_source_changes=changed, concurrent_candidate_changes=concurrent,
        verified_base=base_manifest, base_candidate=str(CANDIDATE),
        supplementary_input_count=len(supplements), supplementary_input_changes=[row['incoming_path']
            for row in supplements if not Path(row['incoming_path']).is_file()
            or hashlib.sha256(Path(row['incoming_path']).read_bytes()).hexdigest() != row['sha256']],
        source_composition=composition,
        dependency_file_count=len(dependencies_before), dependency_changes=[name for name in
            sorted(set(dependencies_before) | set(dependencies_after))
            if dependencies_before.get(name) != dependencies_after.get(name)],
        dependency_scope='All Python source and extension modules in the interpreter standard library and configured virtual environment; interpreter binary, verification harness, and ldd-resolved linked native dependencies of the interpreter and every installed extension. No external producer runtime executes.',
        scratch_bytes=size, scratch_within_limit=size <= SCRATCH,
        ram_limit_bytes=RAM, scratch_limit_bytes=SCRATCH, walltime_limit=None,
        no_live_qualification='Controlled native transport, episode choices, parent/scientific continuation and zero scientific-credit projection; actual execution endpoint estimator/controller. No remote task, credential, native producer or model execution.')
    dump(target / 'receipt.json', receipt)
    print(json.dumps(receipt, indent=2), flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
