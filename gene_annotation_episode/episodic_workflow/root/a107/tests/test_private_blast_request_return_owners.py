"""Actual BLAST request/return boundaries with controlled source-service ports."""
from __future__ import annotations
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
AXIS = 'gene_annotation_episode.episodic_workflow.root.a107'
PREFIXES = ('', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution', 'scientific_process', 'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution')
HOMES = [('/'.join(filter(None, (prefix, suffix))), role) for prefix in PREFIXES for suffix, role in (('execution_job_submission/api_job_execution', 'launch_api'), ('execution_result_acquisition', 'results'))]

def capture(call):
    try: return {'value': call()}
    except (ValueError, TypeError, KeyError) as error:
        return {'exception': type(error).__module__ + '.' + type(error).__name__, 'message': str(error)}

def observations(home, role):
    from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import BLAST_GRADED_REQUEST_VERSION
    owner = object.__new__(importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.episode').ExecutionEpisode)
    assert owner.roles == (role,)
    events, values = [], {}
    if role == 'launch_api':
        scope = {'subject_refs': ['subject_original']}
        request = {'version': BLAST_GRADED_REQUEST_VERSION, 'query_subject_ref': 'subject_original', 'database': 'original-db'}
        selected = {'resource_id': 'original-resource', 'service': 'ncbi_blast', 'request': {'database': 'original-db'}}
        def checked(subject, supplied): events.append(['sequence_operand', subject, supplied])
        def molecule(subject): events.append(['molecule', subject]); return 'DNA'
        def sequence(subject, molecule_model): events.append(['sequence', subject, molecule_model]); return 'ACGT'
        result_digest = hashlib.sha256(b'ACGT').hexdigest()
        def prepare(name, supplied, known, **kwargs):
            events.append(['prepare', name, supplied, known, kwargs]); return {'sequence_sha256': result_digest}
        owner.tool_registry = SimpleNamespace(_check_sequence_operand=checked, _sequence=sequence)
        owner.store = SimpleNamespace(subject_molecule=molecule)
        owner.api_execution = SimpleNamespace(services={'original-resource': SimpleNamespace(prepare=prepare)})
        owner._permitted = lambda launch, resource: resource == 'original-resource'
        for case in ('no_request', 'wrong_service', 'query_conflict', 'database_conflict', 'valid'):
            events.clear()
            result_digest = '0' * 64 if case == 'query_conflict' else hashlib.sha256(b'ACGT').hexdigest()
            current = {**selected, 'service': 'other-service' if case == 'wrong_service' else 'ncbi_blast', 'request': {'database': 'other-db' if case == 'database_conflict' else 'original-db'}}
            launch = {'requests': {} if case == 'no_request' else {'original-resource': request}}
            values[case] = {'outcome': capture(lambda: owner._validate_blast_api_parent_request(launch, current, scope)), 'events': list(events)}
        assert values['no_request'] == {'outcome': {'value': None}, 'events': []}
        assert values['wrong_service']['outcome']['message'] == 'blast_grader_selected_service_conflict'
        assert values['query_conflict']['outcome']['message'] == 'blast_grader_selected_query_conflict'
        assert values['database_conflict']['outcome']['message'] == 'blast_grader_selected_database_conflict'
        assert values['valid']['outcome'] == {'value': None}
    else:
        target = {'resource_kind': 'api', 'assignment': {'service': 'ncbi_blast'}, 'origin_episode_id': 'original-api-child'}
        current_rows = []
        def execute(query, args):
            events.append({'query': query, 'args': list(args)})
            assert current_rows
            row = current_rows.pop(0)
            return SimpleNamespace(fetchone=lambda: row)
        owner.store = SimpleNamespace(db=SimpleNamespace(execute=execute)); owner.run_id = 'original-run'
        for case in ('non_api_target', 'missing_origin', 'invalid_origin_path', 'missing_parent'):
            events.clear()
            current_rows = [None] if case == 'missing_origin' else [{'path': json.dumps([['launch_api', 'no-parent']])}] if case == 'invalid_origin_path' else [{'path': json.dumps([['launch', 'parent'], ['launch_api', 'child']])}, None]
            value = {**target, 'resource_kind': 'local'} if case == 'non_api_target' else target
            values[case] = {'outcome': capture(lambda: owner._blast_target_requirement(value, {})), 'events': list(events)}
        assert values['non_api_target'] == {'outcome': {'value': None}, 'events': []}
        for case, code in [('missing_origin', 'blast_grader_original_launch_missing'), ('invalid_origin_path', 'blast_grader_original_launch_path_invalid'), ('missing_parent', 'blast_grader_original_parent_missing')]:
            assert values[case]['outcome']['message'] == code
        context = SimpleNamespace(scope={}, assignment={'handoff_ref': 'original-handoff'})
        for case in ('empty_results', 'other_service_result', 'handoff_conflict'):
            events.clear()
            def read(reference, scope):
                events.append(['read_result', reference, scope])
                return {'target': {'assignment': {'service': 'other-service' if case == 'other_service_result' else 'ncbi_blast'}, 'handle': 'different-handoff'}}
            owner.api_execution = SimpleNamespace(read_result=read)
            values[case] = {'outcome': capture(lambda: owner._blast_grader_rows(context, [] if case == 'empty_results' else ['result_original'], {})), 'events': list(events)}
        assert values['empty_results'] == {'outcome': {'value': []}, 'events': []}
        assert values['other_service_result']['outcome'] == {'value': []}
        assert values['handoff_conflict']['outcome']['message'] == 'blast_grader_result_handoff_conflict'
    return values

@pytest.mark.parametrize('home,role', HOMES)
def test_private_blast_request_and_return_boundaries(home, role):
    golden = json.loads((Path(__file__).parent / 'fixtures/organization_original/a107_blast_request_return_baseline.json').read_text())
    assert observations(home, role) == golden['observations'][home]
