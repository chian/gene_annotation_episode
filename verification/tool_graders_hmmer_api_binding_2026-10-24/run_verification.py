"""Capture exact verification command, output, exit status and source hashes."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
FILES = [
    'gene_annotation_episode/tools.py', 'gene_annotation_episode/api_execution.py',
    'gene_annotation_episode/api_service_execution.py', 'gene_annotation_episode/execution_episodes.py',
    'gene_annotation_episode/execution_service_setup.py', 'gene_annotation_episode/execution_progress.py',
    'gene_annotation_episode/provider_jobs.py', 'gene_annotation_episode/acquisition.py',
    'gene_annotation_episode/hmmer_graders.py', 'gene_annotation_episode/hmmer_search_inputs.py',
    'gene_annotation_episode/hmmer_search_grader.py', 'gene_annotation_episode/tool_grading_artifacts.py',
    'gene_annotation_episode/runtime.py', 'gene_annotation_episode/communication.py',
    'gene_annotation_episode/episode_receipts.py', 'gene_annotation_episode/episode_bindings.py',
    'gene_annotation_episode/tool_knowledge.py', 'gene_annotation_episode/knowledge/hmmer-api-results.md',
    'gene_annotation_episode/knowledge/index.json',
    'tests/test_hmmer_grading_publication.py', 'tests/test_hmmer_grading_api_returns.py',
    'tests/api_execution_fixture.py', 'tests/test_api_execution.py', 'tests/test_public_search.py',
]


def hashes():
    return {p: sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES if (ROOT/p).is_file()}


def main():
    label = sys.argv[1]
    if re.fullmatch(r'[a-z0-9-]+', label) is None:
        raise ValueError('generation_label_required')
    output = Path(__file__).resolve().parent/label
    output.mkdir(exist_ok=False)
    if sys.argv[2:] not in ([], ['--focused']):
        raise ValueError('unknown_verification_option')
    command = [str(ROOT/'.venv/bin/python'), '-m', 'pytest',
        'tests/test_hmmer_grading_publication.py', 'tests/test_hmmer_grading_api_returns.py']
    if '--focused' not in sys.argv[2:]:
        command += ['tests/test_api_execution.py', 'tests/test_public_search.py']
    command += ['-q', '--disable-warnings']
    before = hashes()
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    elapsed = time.monotonic()-clock
    after = hashes()
    (output/'pytest.txt').write_text(result.stdout)
    metadata = {'command': command, 'cwd': str(ROOT), 'started_at': started,
        'completed_at': datetime.now(timezone.utc).isoformat(), 'elapsed_seconds': elapsed,
        'exit_code': result.returncode, 'source_hashes_before': before, 'source_hashes_after': after,
        'source_stable_during_run': before == after,
        'input_classification': 'retained_actual_phmmer_pages_and_explicit_synthetic_fixtures',
        'execution_classification': 'scripted_shared_method_loop_and_explicit_synthetic_HTTP_transport',
        'no_live_api_or_HPC_or_database_BLAST': True}
    (output/'VERIFICATION.json').write_text(json.dumps(metadata, indent=2, sort_keys=True)+'\n')
    print(result.stdout)
    print(json.dumps({'output': str(output.relative_to(ROOT)), 'exit_code': result.returncode,
                      'source_stable_during_run': before == after}))
    raise SystemExit(result.returncode or (0 if before == after else 2))


if __name__ == '__main__':
    main()
