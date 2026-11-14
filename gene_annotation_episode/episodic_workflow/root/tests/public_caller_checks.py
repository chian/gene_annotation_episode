"""Actual public Store/case setup; only workflow/provider dispatch is controlled."""
from pathlib import Path
from types import SimpleNamespace
import json
import hashlib

from gene_annotation_episode.state import Store

FIXTURES = Path(__file__).parent / 'fixtures' / 'public_callers'
PARAMETERS = {'kind': 'public_case_fixture_v1'}


def forbidden(*args, **kwargs):
    raise AssertionError('native/provider dispatch is outside public caller controls')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def create_workspace(path, *, protein=False):
    with Store(path) as store:
        problem = store.create_problem(raw_sequence='MKT' if protein else 'ATGAAATAA',
            molecule='protein' if protein else 'dna', role='protein' if protein else 'gene')
        target, = store.targets()
        assert problem['subject_refs'] == [target['id']]
    return target['id'], problem['id']


def prepare_case(directory):
    from gene_annotation_episode import case_execution as case
    workspace = directory / 'store'
    target, problem = create_workspace(workspace)
    case_dir = directory / 'case'
    case_dir.mkdir()
    sequence = case_dir / 'target.fna'
    sequence.write_text('>controlled_gene\nATGAAATAA\n')
    (case_dir / 'case.json').write_text(json.dumps({
        'case_ref': 'controlled-public-case', 'target_kind': 'single_gene',
        'target_ref': target, 'problem_ref': problem,
        'target_files': {'target.fna': sha(sequence)},
        'scientific_question': 'Retain this explicit caller question without executing it.'}))
    settings = {'workspace': str(workspace), 'history': str(directory / 'history.sqlite3'),
        'resource_id': 'controlled-public-host', 'max_cpu': 1,
        'executable': {'path': str(FIXTURES / 'inert_native'), 'sha256': sha(FIXTURES / 'inert_native')},
        'reference_database': {'path': str(FIXTURES / 'references.faa'), 'sha256': sha(FIXTURES / 'references.faa')},
        'local_jobs': {'memory_bytes': 128 * 1024 ** 2, 'scratch_bytes': 8 * 1024 ** 2},
        'models': {'FAST': {'model': 'unexecuted-model', 'reasoning_effort': 'low'},
                   'REASONING': {'model': 'unexecuted-model', 'reasoning_effort': 'low'}},
        'public': {'ncbi_email': None}, 'restoration': {'preview_size': 2}}
    run = directory / 'case-run'
    manifest = case.prepare_case_run(case_dir, run, settings, focus='Controlled public construction.')
    return SimpleNamespace(workspace=workspace, target=target, problem=problem,
        case_dir=case_dir, settings=settings, run=run, manifest=manifest,
        policy=FIXTURES / 'policy.py', parameters=PARAMETERS)
