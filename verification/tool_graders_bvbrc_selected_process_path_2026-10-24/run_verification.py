"""Run only the selected-process seam tests and pin the complete local inputs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]


def sources():
    files = set()
    for folder in ('gene_annotation_episode', 'method_loop',
            'research/slotted_process_library/publications/2026-10-24-001'):
        files.update(path for path in (ROOT / folder).rglob('*')
            if path.is_file() and path.suffix in {'.py', '.md', '.json'}
            and '__pycache__' not in path.parts)
    files.update(ROOT / name for name in (
        'cases/gene_001/target.faa', 'tests/bvbrc_episode_fixture.py',
        'tests/bvbrc_selected_process_fixture.py', 'tests/test_bvbrc_selected_process_path.py',
        'verification/tool_graders_bvbrc_data_contract_2026-10-24/feature_count_solr.body',
        'verification/tool_graders_bvbrc_data_contract_2026-10-24/feature_count_solr.meta.json'))
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(files)}


def save(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


before = sources()
save('source_hashes_before.json', before)
command = [sys.executable, '-m', 'pytest', '-q', '-s',
    'tests/test_bvbrc_selected_process_path.py', '--tb=short',
    '--basetemp', str(EVIDENCE / 'pytest-tmp')]
started = datetime.now(timezone.utc).isoformat()
with (EVIDENCE / 'pytest.log').open('w') as log:
    completed = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
after = sources()
save('source_hashes_after.json', after)
changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
summaries = {str(path.relative_to(EVIDENCE)): json.loads(path.read_text())
    for path in sorted((EVIDENCE / 'pytest-tmp').rglob('verification_summary.json'))}
log_lines = (EVIDENCE / 'pytest.log').read_text().splitlines()
report = {'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
    'command': command, 'exit_code': completed.returncode,
    'pytest_summary': log_lines[-1] if log_lines else None,
    'source_file_count': len(before), 'changed_sources_during_tests': changed,
    'verified_runs': summaries,
    'limits': ['Scripted provider choices and engineering-only scientific continuation.',
        'Retained native response replayed at urllib HTTP boundary; no live API or configured model.',
        'Saved provider context verified; no new rendered TASK/STEERING correctness claim.',
        'One current A101/P01, genome_feature count-mode, configured API route only.',
        'No homology, annotation-support or biological-completion conclusion from acquisition.',
        'No literature/W05/formula, other collection/mode, independent-worker or HPC verification.']}
save('REPORT.json', report)
print(json.dumps({'exit_code': completed.returncode, 'pytest_summary': report['pytest_summary'],
    'source_file_count': len(before), 'changed_sources_during_tests': changed,
    'verified_values': [{'count': item['reported_count'], 'docs': item['returned_document_rows'],
        'http_requests': item['http_requests'], 'native_sha256': item['native_sha256']}
        for item in summaries.values()]}, sort_keys=True))
raise SystemExit(completed.returncode if not changed else 2)
