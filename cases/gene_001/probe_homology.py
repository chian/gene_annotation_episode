"""Empirical job inspection, not an episodic workflow or annotation conclusion.

One gene is queried against reference proteins. Measurements are raw observations;
none is scientific credit, a controller observation, or percent complete.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
JOB = ROOT / 'jobs' / 'homology_001'
SKILL = Path('/home/chia/.codex/plugins/cache/openai-curated-remote/life-science-research/1.0.3/skills/uniprot-skill/scripts/rest_request.py')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def clock():
    return datetime.now(timezone.utc).isoformat()


def measurements():
    """Find only the native service whose recorded ExecStart binds this job.

    CPU, memory and I/O are execution measurements, not inferred search coverage.
    """
    result = subprocess.run(['systemctl', '--user', 'list-units', 'gene-local-job-*',
        '--plain', '--no-legend', '--no-pager'], capture_output=True, text=True, check=True)
    found = []
    for line in result.stdout.splitlines():
        words = line.split()
        unit = next((w for w in words if w.startswith('gene-local-job-') and w.endswith('.service')), None)
        if unit is None:
            continue
        details = subprocess.run(['systemctl', '--user', 'show', unit,
            '--property=ExecStart', '--property=MainPID', '--property=ControlGroup'],
            capture_output=True, text=True, check=True)
        props = dict(line.split('=', 1) for line in details.stdout.splitlines() if '=' in line)
        if str(JOB) not in props.get('ExecStart', ''):
            continue
        row = {'service': unit, 'pid': int(props['MainPID'])}
        try:
            proc = Path('/proc') / str(row['pid'])
            stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
            import os
            row['cpu_seconds'] = (int(stat[11]) + int(stat[12])) / os.sysconf('SC_CLK_TCK')
            status = dict(line.split(':', 1) for line in (proc / 'status').read_text().splitlines() if ':' in line)
            row['resident_bytes'] = int(status['VmRSS'].split()[0]) * 1024
            io = dict(line.split(':', 1) for line in (proc / 'io').read_text().splitlines())
            row['logical_read_bytes'] = int(io['rchar'])
            row['storage_read_bytes'] = int(io['read_bytes'])
            group = Path('/sys/fs/cgroup') / props['ControlGroup'].lstrip('/')
            row['cgroup_memory_bytes'] = int((group / 'memory.current').read_text())
        except (FileNotFoundError, ProcessLookupError, KeyError):
            row['process_measurement_available'] = False
        found.append(row)
    return found


def execute(phase, command, *, stdin=None):
    stdout, stderr = JOB / (phase + '.stdout'), JOB / (phase + '.stderr')
    start = time.monotonic()
    with (JOB / 'observations.jsonl').open('a') as log, ThreadPoolExecutor(max_workers=1) as pool:
        log.write(json.dumps({'event': 'phase_started', 'phase': phase, 'at': clock(), 'command': command}) + '\n')
        log.flush()
        future = pool.submit(run_local_job, command, cwd=JOB, policy=LocalJobPolicy.from_config(),
            stdout_path=stdout, stderr_path=stderr, stdin_path=stdin)
        while not future.done():
            row = {'event': 'sample', 'phase': phase, 'at': clock(),
                'elapsed_seconds': time.monotonic()-start, 'processes': measurements(),
                'files': {p.name: p.stat().st_size for p in JOB.iterdir()
                    if p.is_file() and p.suffix in ('.fasta', '.tbl', '.stdout', '.stderr')}}
            log.write(json.dumps(row) + '\n'); log.flush()
            # Sampling cadence belongs to this empirical probe, not an episode
            # policy, work timeout, or proposed future polling default.
            if not future.done():
                time.sleep(1)
        result = future.result()
        row = {'event': 'phase_returned', 'phase': phase, 'at': clock(),
            'elapsed_seconds': time.monotonic()-start, 'returncode': result.returncode,
            'native_metadata': result.metadata}
        log.write(json.dumps(row) + '\n'); log.flush()
    print(json.dumps({'phase': phase, 'returncode': result.returncode,
        'elapsed_seconds': row['elapsed_seconds']}), flush=True)
    if result.returncode != 0:
        raise RuntimeError(f'{phase}_exit_{result.returncode}')
    return row


def main():
    JOB.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(ROOT / 'target.faa', JOB / 'target.faa')
    request = {'base_url': 'https://rest.uniprot.org', 'path': 'uniprotkb/stream',
        'params': {'query': 'reviewed:true', 'format': 'fasta'}, 'response_format': 'text',
        'save_raw': True, 'raw_output_path': str(JOB / 'reviewed.fasta')}
    request_path = JOB / 'reference-request.json'
    request_path.write_text(json.dumps(request, indent=2) + '\n')
    download = execute('reference_acquisition', [sys.executable, str(SKILL)], stdin=request_path)
    reply = json.loads((JOB / 'reference_acquisition.stdout').read_text())
    if not reply.get('ok'):
        raise RuntimeError('reference_acquisition_did_not_return_success')
    count = residues = 0
    with (JOB / 'reviewed.fasta').open() as stream:
        for line in stream:
            if line.startswith('>'):
                count += 1
            else:
                residues += len(line.strip())
    if count == 0:
        raise RuntimeError('reference_database_contains_no_records')
    program = PROJECT / 'resources/software/infernal-1.1.5/hmmer/src/phmmer'
    command = [str(program), '--cpu', '1', '--tblout', 'hits.tbl', '--domtblout',
        'domains.tbl', 'target.faa', 'reviewed.fasta']
    manifest = {'case_ref': 'gene_001', 'job_kind': 'single_query_protein_homology',
        'annotation_question': 'Do homologous reviewed proteins discriminate possible activities of YbhP, or support only a broad family?',
        'command': command, 'query_count': 1, 'query_sha256': digest(JOB / 'target.faa'),
        'database_records': count, 'database_residues': residues,
        'database_sha256': digest(JOB / 'reviewed.fasta'), 'executable_sha256': digest(program),
        'database_query': request, 'native_policy': LocalJobPolicy.from_config().to_dict(),
        'mode': 'empirical_inspection_not_episodic_execution',
        'reference_acquisition': download, 'search': None, 'annotation_conclusion': None,
        'credit_assigned': False}
    (JOB / 'job.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'reference_records': count, 'reference_residues': residues}), flush=True)
    manifest['search'] = execute('homology_search', command)
    manifest['outputs'] = {name: {'bytes': (JOB / name).stat().st_size,
        'sha256': digest(JOB / name)} for name in ('hits.tbl', 'domains.tbl', 'homology_search.stdout', 'homology_search.stderr')}
    (JOB / 'job.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
