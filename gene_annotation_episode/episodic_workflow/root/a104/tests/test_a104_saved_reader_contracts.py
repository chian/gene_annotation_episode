"""Typed original forms and historical worker controls; no producer execution.

These focused contract tests do not establish grant authority. The separate
30-owner retained protein/fluorescence suites exercise actual receipt readers,
typed grants, denied siblings/roots, both resolvers, immutable inputs and reopen.
"""
from copy import deepcopy
from importlib import import_module
import json

import pytest

from gene_annotation_episode.episodic_workflow.root.a104.communication import validate_closed_schema
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_records import validate_assignment
from gene_annotation_episode.episodic_workflow.root.a104.tests.retained_fluorescence_fixture import unpack as unpack_fluorescence
from gene_annotation_episode.episodic_workflow.root.a104.tests.retained_protein_fixture import unpack as unpack_protein

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104.'


@pytest.fixture(scope='module')
def cases(tmp_path_factory):
    fluorescence = unpack_fluorescence(tmp_path_factory.mktemp('original049-contracts'))
    protein = unpack_protein(tmp_path_factory.mktemp('original336-contracts'))
    result = {case.manifest['operation']: case for case in fluorescence}
    result['protein_original336'] = protein
    yield result
    for case in result.values():
        case.verify_unchanged()


def receipts(store, case):
    version = ('native_protein_structure_acquired_result_v1' if case.manifest.get('operation') is None
        else 'native_fluorescence_acquired_result_v1')
    rows = store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND result IS NOT NULL "
        "AND json_extract(result,'$.result.version')=? ORDER BY rowid",
        (case.manifest['original_run_id'], version)).fetchall()
    values = [json.loads(row['result'])['result'] for row in rows]
    assert len(values) == 3
    return values


@pytest.mark.parametrize('case_name', ('perform_facs_cell_sorting',
    'analyze_cytokine_production_in_cd4_tcells', 'protein_original336'))
def test_original_typed_forms_rows_and_practical_assignments(cases, case_name):
    case = cases[case_name]
    family = 'protein' if case_name == 'protein_original336' else 'fluorescence'
    comm = import_module(PREFIX + 'communication')
    fluor = import_module(PREFIX + 'library.fluorescence_return_views')
    with case.open_store() as store:
        values = receipts(store, case)
        counts = {'nonempty_fact_sources': 0, 'practical_assignments': 0, 'registered_forms': 0}
        for value in values:
            intent = value['body']['intent'] if family == 'protein' else value['intent']
            facts = value['publication']['facts'] if family == 'protein' else value['facts']
            episode = store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                (case.manifest['original_run_id'], intent['episode_id'])).fetchone()
            form = json.loads(episode['request'])['report_contract']['measurements']['schema']
            assert validate_closed_schema(form) == form
            counts['registered_forms'] += 1
            for source, rows in facts.items():
                if family == 'protein':
                    comm._validate_protein_structure_fact_rows(rows, source, 'retained_rows')
                else:
                    assert fluor.validate_fluorescence_fact_values(source, rows) == rows
                counts['nonempty_fact_sources'] += int(bool(rows))
                if rows:
                    malformed = deepcopy(rows)
                    malformed[0]['unexpected_retained_field'] = True
                    with pytest.raises((ValueError, comm.ReportBoundaryError)):
                        if family == 'protein':
                            comm._validate_protein_structure_fact_rows(malformed, source, 'retained_rows')
                        else:
                            fluor.validate_fluorescence_fact_values(source, malformed)
            # Stored practical assignments are read directly from original
            # commissioning records. No new task selection or live operation.
        for row in store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=?',
                (case.manifest['original_run_id'],)):
            message = json.loads(row['request']).get('message', {})
            assignment = message.get('episode_assignment', message.get('assignment'))
            if not isinstance(assignment, dict) or assignment.get('version') != 'practical_assignment_v1':
                continue
            wanted = 'native_protein_structure' if family == 'protein' else 'native_fluorescence'
            if wanted not in assignment.get('requested_job', {}):
                continue
            assert validate_assignment(assignment) == assignment
            counts['practical_assignments'] += 1
            wrong = deepcopy(assignment)
            wrong['resource_kind'] = 'hpc'
            with pytest.raises(ValueError, match='local_resource_required'):
                validate_assignment(wrong)
            wrong = deepcopy(assignment)
            wrong.pop('resource_id')
            with pytest.raises(ValueError, match='resource_identity_required'):
                validate_assignment(wrong)
        assert counts['registered_forms'] == 3 and counts['nonempty_fact_sources'] > 0
        assert counts['practical_assignments'] > 0


@pytest.mark.parametrize('operation', ('perform_facs_cell_sorting', 'analyze_cytokine_production_in_cd4_tcells'))
def test_original_worker_controls_are_read_without_live_policy_construction(cases, operation, monkeypatch):
    module = import_module(PREFIX + 'library.native_fluorescence_preparation')
    local_jobs = import_module(PREFIX + 'local_jobs')
    def forbidden(*args, **kwargs):
        raise AssertionError('Historical read constructed a live LocalJobPolicy')
    monkeypatch.setattr(local_jobs, 'LocalJobPolicy', forbidden)
    case = cases[operation]
    with case.open_store() as store:
        values = receipts(store, case)
        for value in values:
            execution, plan = value['worker_execution'], value['worker_plan']
            assert execution is not None and plan is not None
            before = deepcopy(execution)
            assert execution['policy']['wall_seconds'] is None
            assert execution['metadata']['verified_cgroup']['runtime_max'] == 'infinity'
            assert module.validate_fluorescence_worker_execution(execution,
                plan=plan, plan_file=execution['plan_file']) == execution
            assert execution == before


@pytest.mark.parametrize('operation', ('perform_facs_cell_sorting', 'analyze_cytokine_production_in_cd4_tcells'))
@pytest.mark.parametrize('change', ('mixed_policy', 'missing_cgroup_field', 'extra_cgroup_field',
    'changed_request_bytes', 'unknown_source_path', 'changed_memory'))
def test_worker_reader_rejects_changed_or_mixed_historical_controls(cases, operation, change):
    module = import_module(PREFIX + 'library.native_fluorescence_preparation')
    case = cases[operation]
    with case.open_store() as store:
        original = receipts(store, case)[0]
        execution = deepcopy(original['worker_execution'])
        if change == 'mixed_policy':
            execution['policy'].pop('wall_seconds')
        elif change == 'missing_cgroup_field':
            execution['metadata']['verified_cgroup'].pop('runtime_max')
        elif change == 'extra_cgroup_field':
            execution['metadata']['verified_cgroup']['unknown_limit'] = 1
        elif change == 'changed_request_bytes':
            execution['request_raw'] += ' '
        elif change == 'unknown_source_path':
            execution['intent']['source_pins'][0]['path'] = '/undeclared-source.py'
        elif change == 'changed_memory':
            execution['policy']['memory_bytes'] += 1
        with pytest.raises(ValueError):
            module.validate_fluorescence_worker_execution(execution, plan=original['worker_plan'],
                plan_file=execution['plan_file'])
