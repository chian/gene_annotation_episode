"""Historical manifest reconstruction; not a fresh root policy or execution.

The real Journal and Store retain explicit engineering settings. No task score,
private scientific assessment, returned unit, controller or provider is invoked.
"""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.default_scientific_binding import VERSION, bind_default_science
from gene_annotation_episode.episodic_workflow.root.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal, WorkflowError


def recorded_binding(store, directory):
    """Actual saved configuration fixture, not a claimed completed workflow."""
    directory.mkdir()
    run_id = 'run_historical_binding_fixture'
    target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
    scientific = ScientificFindingProgress(FindingProgressPolicy(7), 3)
    manifest = {'run_id': run_id,
        'binding_definitions': {'credit': {**scientific.as_record(), 'default_entrypoint': VERSION}},
        'scientific_knowledge': {'initial_known_record_refs': [target]}}
    marker = directory / 'run.json'
    marker.write_text(json.dumps(manifest))
    journal = Journal(store, run_id)
    journal.save('runtime_runs', {'settings': json.dumps({'directory': str(directory)}),
        'state': 'created', 'summary': None,
        'started_at': '2026-11-01T00:00:00+00:00', 'updated_at': '2026-11-01T00:00:00+00:00'})
    return scientific, manifest, journal


def options(directory):
    return {'run_dir': directory, 'resume': True, 'provider_config': None,
        'credit_policy': None, 'initial_known_record_refs': None,
        'project_child_credit': None, 'project_annotation_score': None,
        'binding_definitions': None}


def test_fresh_entrypoint_keeps_original_explicit_root_task_credit_refusal(tmp_path):
    with Store(tmp_path / 'store') as store:
        directory = tmp_path / 'never-created'
        with pytest.raises(ValueError, match='^explicit_root_task_credit_required$'):
            bind_default_science(store, **{**options(directory), 'resume': False})
        assert not directory.exists()
        assert store.db.execute("SELECT count(*) FROM sqlite_master WHERE name='runtime_runs'").fetchone()[0] == 0


@pytest.mark.parametrize('lookup_saved_directory', [False, True], ids=['explicit-directory', 'actual-journal-latest'])
def test_resume_reconstructs_exact_recorded_policy_without_new_defaults(tmp_path, lookup_saved_directory):
    with Store(tmp_path / 'store') as store:
        directory = tmp_path / 'saved'
        scientific, manifest, journal = recorded_binding(store, directory)
        before = (directory / 'run.json').read_bytes(), journal.row('runtime_runs')
        result = bind_default_science(store, **options(None if lookup_saved_directory else directory))
        assert result['run_dir'] == directory.resolve()
        assert type(result['project_credit']) is ScientificFindingProgress
        assert result['project_credit'].as_record() == scientific.as_record()
        assert result['initial_known_record_refs'] == manifest['scientific_knowledge']['initial_known_record_refs']
        assert result['binding_definitions'] == manifest['binding_definitions']
        assert result['project_child_credit'] is None and result['project_annotation_score'] is None
        assert result['credit_policy'] is None and result['provider_config'] is None
        assert ((directory / 'run.json').read_bytes(), journal.row('runtime_runs')) == before


@pytest.mark.parametrize('child', ['absent', 'recorded', 'explicit'])
def test_children_only_reconstruct_actual_saved_or_explicit_choice(tmp_path, child):
    with Store(tmp_path / 'store') as store:
        directory = tmp_path / 'saved'
        scientific, manifest, _ = recorded_binding(store, directory)
        selected = ScientificFindingProgress(FindingProgressPolicy(2), 1)
        kwargs = options(directory)
        if child == 'recorded':
            manifest['binding_definitions']['scientific_child_credit'] = scientific.as_record()
        elif child == 'explicit':
            kwargs['project_child_credit'] = selected
        (directory / 'run.json').write_text(json.dumps(manifest))
        result = bind_default_science(store, **kwargs)
        if child == 'absent':
            assert result['project_child_credit'] is None
            assert 'scientific_child_credit' not in result['binding_definitions']
        elif child == 'recorded':
            assert result['project_child_credit'] is result['project_credit']
            assert result['binding_definitions']['scientific_child_credit'] == scientific.as_record()
        else:
            assert result['project_child_credit'] is selected
            assert result['project_credit'].as_record() == scientific.as_record()
            assert 'scientific_child_credit' not in result['binding_definitions']


@pytest.mark.parametrize('defect,code', [
    ('version', 'resume_requires_original_scientific_binding_and_code_snapshot'),
    ('annotation', 'resume_requires_original_annotation_score_binding'),
    ('child', 'resume_requires_original_scientific_child_binding'),
    ('definition', 'default_scientific_binding_definition_conflict:credit'),
    ('policy', 'categorical_annotation_policy_retired_supply_explicit_numeric_scorer'),
    ('extra_progress', 'scientific_progress_requires_finding_unit_loss_preview_size_and_initial_known_record_refs'),
])
def test_original_reconstruction_failures_preserve_manifest_and_journal(tmp_path, defect, code):
    with Store(tmp_path / 'store') as store:
        directory = tmp_path / 'saved'
        scientific, manifest, journal = recorded_binding(store, directory)
        kwargs = options(directory)
        if defect == 'version':
            manifest['binding_definitions']['credit']['default_entrypoint'] = 'unrecognized'
        elif defect == 'annotation':
            manifest['binding_definitions']['annotation_score'] = {'explicit_fixture': 'not_a_bound_scorer'}
        elif defect == 'child':
            other = ScientificFindingProgress(FindingProgressPolicy(2), 1)
            manifest['binding_definitions']['scientific_child_credit'] = other.as_record()
        elif defect == 'definition':
            kwargs['binding_definitions'] = {'credit': {'not': 'the saved declaration'}}
        elif defect == 'policy':
            kwargs['credit_policy'] = {}
        else:
            kwargs['provider_config'] = {'scientific_progress': {'unexpected': 1}}
        (directory / 'run.json').write_text(json.dumps(manifest))
        before = (directory / 'run.json').read_bytes(), journal.row('runtime_runs'), deepcopy(kwargs)
        with pytest.raises(ValueError, match='^' + code + '$'):
            bind_default_science(store, **kwargs)
        assert ((directory / 'run.json').read_bytes(), journal.row('runtime_runs'), kwargs) == before


def test_consumed_progress_settings_do_not_become_model_settings(tmp_path):
    with Store(tmp_path / 'store') as store:
        directory = tmp_path / 'saved'
        scientific, _, _ = recorded_binding(store, directory)
        provider = {'models': {'fixture': 'opaque retained configuration'},
                    'scientific_progress': {'finding_unit': 7, 'loss_preview_size': 3}}
        before = deepcopy(provider)
        result = bind_default_science(store, **{**options(directory), 'provider_config': provider})
        assert result['project_credit'].as_record() == scientific.as_record()
        assert result['provider_config'] == {'models': provider['models']}
        assert provider == before


def test_missing_actual_saved_run_remains_original_workflow_error(tmp_path):
    with Store(tmp_path / 'store') as store:
        with pytest.raises(WorkflowError, match='^no saved run exists to resume$'):
            bind_default_science(store, **options(None))
