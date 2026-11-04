"""Infernal selection through the real launch/local composition, without execution.

Requests are retained Infernal/HMMER contracts. Alternate software identities
are explicitly declared selection fixtures, not verified deployments. No native
program, acquisition, parser, score calculator or model is run by these tests.
Workflow execution and authenticated numerical returns have separate coverage.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, LAUNCH_VERSION
from gene_annotation_episode.infernal_native_result_views import (
    FAMILY_SOURCES, NATIVE_INFERNAL_METRICS, native_infernal_fact_sources,
    row_schema, validate_native_infernal_result_selector,
)
from gene_annotation_episode.native_hmmer_contracts import requested_job_from_native
from gene_annotation_episode.native_infernal_contracts import requested_job_from_infernal
from gene_annotation_episode.native_infernal_tool_info import native_infernal_tool_contracts
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / 'tests/fixtures/native_infernal_result_worker'
HMMER = ROOT / 'verification/tool_graders_native_hmmer_producer_2026-10-24/runs'
PROGRAMS = ('cmsearch', 'cmscan', 'cmalign')
POLICY = {'memory_bytes': 20 * 1024**3, 'scratch_bytes': 4 * 1024**3,
          'wall_seconds': None}

# These are the requested receiver quantities, independently pinned here so a
# contract regression cannot disappear by comparing a schema with its own list.
METRICS = {
    'search_hit': ('bitscore', 'evalue', 'bias_bits', 'gc_fraction',
        'model_span_length', 'model_span_fraction', 'sequence_span_length',
        'sequence_span_fraction', 'consensus_length', 'sequence_length'),
    'search_sequence': ('hit_count', 'union_numerator', 'union_denominator',
        'union_span_fraction', 'unselected_hit_count', 'unknown_selection_count',
        'invalid_geometry_count'),
    'alignment_sequence': ('native_bit_score', 'native_avg_pp', 'original_length',
        'model_length', 'retained_nucleotides', 'model_match_nucleotides',
        'model_gap_positions', 'missing_model_positions', 'nonresidue_model_positions',
        'retained_insert_nucleotides', 'retained_local_end_nucleotides',
        'deleted_model_positions', 'local_end_skipped_model_positions',
        'total_insert_nucleotides', 'total_local_end_nucleotides', 'omitted_nucleotides',
        'model_occupancy', 'sequence_matched_coverage', 'posterior_available_count',
        'posterior_unavailable_count', 'posterior_lower_mean', 'posterior_upper_mean'),
    'alignment_column': ('row_count', 'occupancy_numerator', 'occupancy_denominator',
        'occupancy', 'missing_rows', 'nonresidue_rows', 'unavailable_rows'),
    'alignment_pair': ('row_count', 'observed_two_nucleotide_pairs', 'canonical_pairs',
        'noncanonical_pairs', 'unambiguous_pair_denominator', 'canonical_pair_fraction',
        'excluded_gap_rows', 'excluded_missing_rows', 'excluded_ambiguous_rows',
        'excluded_nonresidue_rows', 'excluded_unavailable_rows'),
}


def infernal_request(program):
    retained = json.loads((INPUTS / program / 'bundle.json').read_text())['requested_job']
    assert requested_job_from_infernal(retained['native_infernal']) == retained
    return retained


def hmmer_request():
    retained = json.loads((HMMER / 'hmmsearch_search_ordinary' / 'plan.json').read_text())['requested_job']
    assert requested_job_from_native(retained['native_hmmer']) == retained
    return retained


def binding_for(request):
    key = 'native_infernal' if 'native_infernal' in request else 'native_hmmer'
    fields = ('program', 'software') if key == 'native_infernal' else ('program', 'mode', 'software')
    return {field: deepcopy(request[key][field]) for field in fields}


def assignment(workspace, request, resource='here'):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'infernal-selection',
        'resource_id': resource, 'resource_kind': 'local', 'workspace': str(workspace),
        'endpoint': 'usable_handoff', 'requested_job': deepcopy(request),
        'progress_requirements': [{'key': 'handoff', 'credit': 7,
            'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0,
            'cwd': str(workspace), 'environment': {'PREPARATION_CONTEXT': 'separate-from-job'}},
        'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}


def launch_assignment(*requests, versions=None, constraints=None):
    return {'version': LAUNCH_VERSION,
        'requests': {request['resource_id']: deepcopy(request) for request in requests},
        'immutable_input_versions': [] if versions is None else deepcopy(versions),
        'constraints': deepcopy(constraints if constraints is not None else {
            'allowed_resource_ids': [request['resource_id'] for request in requests],
            'allowed_kinds': ['local'], 'allocation': deepcopy(POLICY)})}


def family_for(host, resources=None, suffix='default'):
    return ExecutionEpisodes(None, store=host.store, directory=host.tmp_path / ('run-' + suffix),
        run_id=host.journal.run_id, resources=resources or {'here': host.configuration},
        initial_information={}, tool_registry=ToolRegistry(host.store),
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=['stdout', 'stderr'])


@pytest.fixture
def host(tmp_path):
    workspace = tmp_path / 'project'
    workspace.mkdir()
    store = Store(tmp_path / 'store')
    bundle = json.loads((INPUTS / 'cmsearch' / 'bundle.json').read_text())
    sequence = next(row for row in bundle['inputs'] if row['role'] == 'sequences')
    subjects = store.create_problem(INPUTS / 'cmsearch' / sequence['relative_path'],
        molecule='rna', format='fasta')['subject_refs']
    configuration = {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
        'native_infernal': [binding_for(infernal_request(program)) for program in PROGRAMS],
        'native_hmmer': [binding_for(hmmer_request())]}
    host = SimpleNamespace(store=store, journal=Journal(store, 'infernal-binding-229'),
        workspace=workspace, configuration=configuration, scope={'subject_refs': subjects},
        tmp_path=tmp_path)
    host.family = family_for(host)
    try:
        yield host
    finally:
        store.close()


def context(host, role, value, episode_id, *, parent=None, scope=None):
    scope = host.scope if scope is None else scope
    path = ((role, episode_id),) if parent is None else (*parent.path, (role, episode_id))
    message = {'message': {'scope': deepcopy(scope), 'episode_assignment': deepcopy(value)}}
    result = BindingContext(host.journal.run_id, episode_id, role, path, scope, value, message)
    with host.store.transaction():
        host.journal.save('runtime_episodes', {'episode_id': episode_id, 'path': canonical(path),
            'request': canonical(message), 'initial_credit': 0, 'state': 'running'})
    return result


def commission(host, family, selected, *, name, launch=None):
    original = launch or launch_assignment(selected)
    scientific = context(host, 'scientific_process', {}, name + '-scientific')
    accepted_launch = family.prepare_assignment(scientific, 'launch', original, host.scope, name + '-launch')
    assert accepted_launch == original
    parent = context(host, 'launch', accepted_launch, name + '-parent', parent=scientific)
    family.initialize(parent)
    assert family.allowed_children(parent, ()) == ('launch_local',)
    accepted = family.prepare_assignment(parent, 'launch_local', selected, host.scope, name + '-local')
    assert accepted == selected
    child = context(host, 'launch_local', accepted, name + '-child', parent=parent)
    state = family.initialize(child)
    assert isinstance(family._practical[selected['resource_id']], PracticalResourceEpisodes)
    assert state.assignment == selected
    assert state.receipts() == []
    assert state.completion_proof() is None
    assert family.state(child).assignment == selected
    return parent, child


@pytest.mark.parametrize('program', PROGRAMS)
def test_retained_requests_cross_actual_mixed_launch_and_local_boundaries(host, program):
    request = infernal_request(program)
    original = deepcopy(request)
    selected = assignment(host.workspace, request)
    declaration, = native_infernal_tool_contracts([binding_for(request)],
        resource_kind='local', resource_id='here')
    assert set(declaration) == {'name', 'description', 'resources', 'instructions',
        'input_schema', 'invocation_route'}
    assert all(declaration[key] for key in ('name', 'description', 'resources', 'instructions'))
    assert declaration['name'] == 'native.' + program
    assert declaration['resources'] == 'local'
    assert declaration['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'here', 'resource_role': 'launch_local'}]}
    assert Draft202012Validator(declaration['input_schema']).is_valid(request)
    entry, = [row for row in host.family.resource_tool_contracts() if row['name'] == 'native.' + program]
    assert entry == declaration
    assert Draft202012Validator(host.family.assignment_schema('launch')).is_valid(launch_assignment(selected))
    assert Draft202012Validator(host.family.assignment_schema('launch_local')).is_valid(selected)
    LocalPracticalOperations(host.configuration).validate_assignment(selected)
    _, child = commission(host, host.family, selected, name=program)
    assert 'practical.job.start' in {row['name'] for row in host.family.catalog(child)}
    assert request == original
    assert not list(host.workspace.rglob('native.json'))


def test_hmmer_and_infernal_callable_alternatives_coexist_without_substitution(host):
    requests = [hmmer_request(), *(infernal_request(program) for program in PROGRAMS)]
    entries = {row['name']: row for row in host.family.resource_tool_contracts()
        if row['name'].startswith('native.')}
    assert set(entries) == {'native.hmmsearch', 'native.cmsearch', 'native.cmscan', 'native.cmalign'}
    schema = host.family.assignment_schema('launch_local')
    for request in requests:
        branch = 'native_infernal' if 'native_infernal' in request else 'native_hmmer'
        program = request[branch]['program']
        selected = assignment(host.workspace, request)
        assert Draft202012Validator(schema).is_valid(selected)
        assert [name for name, row in entries.items()
            if Draft202012Validator(row['input_schema']).is_valid(request)] == ['native.' + program]
        LocalPracticalOperations(host.configuration).validate_assignment(selected)
        commission(host, host.family, selected, name='mixed-' + program)
    original = assignment(host.workspace, infernal_request('cmsearch'))
    parent = context(host, 'launch', launch_assignment(original), 'mixed-original')
    replacement = assignment(host.workspace, hmmer_request())
    assert Draft202012Validator(schema).is_valid(replacement)
    with pytest.raises(ValueError, match='execution_original_request_conflict'):
        host.family.prepare_assignment(parent, 'launch_local', replacement, host.scope, 'substitution')


@pytest.mark.parametrize('infernal_setting', ['absent', 'empty'])
def test_unconfigured_infernal_is_not_an_available_operation(host, infernal_setting):
    configuration = deepcopy(host.configuration)
    configuration.pop('native_infernal')
    if infernal_setting == 'empty':
        configuration['native_infernal'] = []
    family = family_for(host, {'here': configuration}, suffix=infernal_setting)
    assert family.native_infernal_results is None
    assert family.native_infernal_returns is None
    entries = {row['name'] for row in family.resource_tool_contracts()}
    assert entries & {'native.' + program for program in PROGRAMS} == set()
    assert 'native.hmmsearch' in entries
    for program in PROGRAMS:
        selected = assignment(host.workspace, infernal_request(program))
        assert not Draft202012Validator(family.assignment_schema('launch_local')).is_valid(selected)
        with pytest.raises(ValueError, match='native_infernal_program_software_not_bound'):
            LocalPracticalOperations(configuration).validate_assignment(selected)
        parent = context(host, 'launch', launch_assignment(selected), infernal_setting + '-' + program)
        with pytest.raises(ValueError, match='invalid_execution_assignment'):
            family.prepare_assignment(parent, 'launch_local', selected, host.scope, 'unbound')
        child = context(host, 'launch_local', selected, infernal_setting + '-' + program + '-child')
        with pytest.raises(ValueError, match='native_infernal_program_software_not_bound'):
            family.initialize(child)
    selected = assignment(host.workspace, hmmer_request())
    commission(host, family, selected, name='still-hmmer-' + infernal_setting)


@pytest.mark.parametrize('program', PROGRAMS)
def test_two_explicit_local_deployments_preserve_each_software_identity(host, program):
    first = infernal_request(program)
    job = deepcopy(first['native_infernal'])
    job['software'] = {'executable': '/declared-other-install/bin/' + program,
        'sha256': 'a' * 64, 'engine_version': 'declared-other-build-not-executed'}
    second = requested_job_from_infernal(job)
    other_workspace = host.tmp_path / 'other-project'
    other_workspace.mkdir()
    configurations = {
        'here': {**deepcopy(host.configuration), 'native_infernal': [binding_for(first)]},
        'there': {'kind': 'local', 'workspace': str(other_workspace), 'policy': deepcopy(POLICY),
            'native_infernal': [binding_for(second)]}}
    family = family_for(host, configurations, suffix='two-' + program)
    requests = [assignment(host.workspace, first), assignment(other_workspace, second, 'there')]
    original = launch_assignment(*requests)
    entry, = [row for row in family.resource_tool_contracts() if row['name'] == 'native.' + program]
    assert entry['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'here', 'resource_role': 'launch_local'},
        {'entry_role': 'launch', 'resource_id': 'there', 'resource_role': 'launch_local'}]}
    assert len(entry['input_schema']['anyOf']) == 2
    for index, request in enumerate(requests):
        assert Draft202012Validator(entry['input_schema']).is_valid(request['requested_job'])
        LocalPracticalOperations(configurations[request['resource_id']]).validate_assignment(request)
        commission(host, family, request, name=program + '-deployment-' + str(index), launch=original)
        swapped = deepcopy(request)
        swapped['requested_job'] = deepcopy(requests[1 - index]['requested_job'])
        assert not Draft202012Validator(family.assignment_schema('launch_local')).is_valid(swapped)
        with pytest.raises(ValueError, match='native_infernal_program_software_not_bound'):
            LocalPracticalOperations(configurations[request['resource_id']]).validate_assignment(swapped)
        parent = context(host, 'launch', original, program + '-cross-parent-' + str(index))
        with pytest.raises(ValueError, match='invalid_execution_assignment'):
            family.prepare_assignment(parent, 'launch_local', swapped, host.scope, 'cross-resource')
        child = context(host, 'launch_local', swapped, program + '-cross-child-' + str(index), parent=parent)
        with pytest.raises(ValueError, match='execution_original_request_conflict'):
            family.initialize(child)
    assert family.as_record()['configuration']['resources'] == configurations
    assert all(row['availability'] == 'unknown' for row in family.capabilities())


def altered_assignment(host, original, change):
    selected = deepcopy(original)
    job = selected['requested_job']['native_infernal']
    if change == 'program':
        selected['requested_job'] = infernal_request('cmscan')
    elif change in {'executable', 'hash', 'version'}:
        field = {'executable': 'executable', 'hash': 'sha256', 'version': 'engine_version'}[change]
        job['software'][field] = {'executable': '/unbound/cmsearch', 'sha256': 'b' * 64,
            'engine_version': 'unbound-version'}[field]
        selected['requested_job'] = requested_job_from_infernal(job)
    elif change == 'resource':
        selected['resource_id'] = 'not-bound'
    elif change == 'compiled_argv':
        selected['requested_job']['argv'] = ['/bin/true']
    elif change == 'original_options':
        job['options'] = ['--cpu', '2']
        selected['requested_job'] = requested_job_from_infernal(job)
    elif change == 'environment':
        job['environment']['SELECTED_JOB'] = 'changed'
        selected['requested_job'] = requested_job_from_infernal(job)
    elif change == 'allocation':
        selected['constraints']['allocation']['memory_bytes'] -= 1
    else:
        raise AssertionError(change)
    return selected


@pytest.mark.parametrize('change', ['program', 'executable', 'hash', 'version', 'resource',
    'compiled_argv', 'original_options', 'environment', 'allocation'])
def test_changed_selected_job_is_rejected_at_preparation_and_durable_initialization(host, change):
    original = assignment(host.workspace, infernal_request('cmsearch'))
    parent = context(host, 'launch', launch_assignment(original), 'original-parent')
    selected = altered_assignment(host, original, change)
    with pytest.raises(ValueError):
        host.family.prepare_assignment(parent, 'launch_local', selected, host.scope, 'changed-selection')
    # This also tests an attempted bypass of prepare_assignment: initialize must
    # compare the stored parent's original request before creating practical state.
    child = context(host, 'launch_local', selected, 'changed-child', parent=parent)
    with pytest.raises(ValueError):
        host.family.initialize(child)
    only_original = {**host.configuration, 'native_infernal': [binding_for(original['requested_job'])]}
    if change in {'program', 'executable', 'hash', 'version'}:
        with pytest.raises(ValueError, match='native_infernal_program_software_not_bound'):
            LocalPracticalOperations(only_original).validate_assignment(selected)
    elif change == 'compiled_argv':
        with pytest.raises(ValueError, match='native_infernal_requested_job_compiler_mismatch'):
            LocalPracticalOperations(only_original).validate_assignment(selected)
    elif change == 'allocation':
        with pytest.raises(ValueError, match='practical_local_allocation_constraint_mismatch'):
            LocalPracticalOperations(only_original).validate_assignment(selected)
    else:
        # Binding validation permits valid options and a supplied resource ID;
        # the execution parent, above, owns their exact original selection.
        LocalPracticalOperations(only_original).validate_assignment(selected)
    assert not list(host.workspace.rglob('native.json'))


def test_parent_resource_constraints_are_enforced_among_valid_local_choices(host):
    configurations = {'here': host.configuration, 'there': deepcopy(host.configuration)}
    family = family_for(host, configurations, suffix='restricted')
    request = infernal_request('cmsearch')
    here, there = assignment(host.workspace, request), assignment(host.workspace, request, 'there')
    original = launch_assignment(here, there, constraints={'allowed_resource_ids': ['here'],
        'allowed_kinds': ['local'], 'allocation': deepcopy(POLICY)})
    parent = context(host, 'launch', original, 'constrained-parent')
    assert family.allowed_children(parent, ()) == ('launch_local',)
    assert Draft202012Validator(family.assignment_schema('launch_local')).is_valid(there)
    with pytest.raises(ValueError, match='execution_resource_selection_conflict'):
        family.prepare_assignment(parent, 'launch_local', there, host.scope, 'excluded-resource')
    commission(host, family, here, name='permitted-resource', launch=original)
    original['constraints']['allowed_kinds'] = ['api']
    parent = context(host, 'launch', original, 'constrained-kind-parent')
    assert family.allowed_children(parent, ()) == ()
    with pytest.raises(ValueError, match='execution_resource_selection_conflict'):
        family.prepare_assignment(parent, 'launch_local', here, host.scope, 'excluded-kind')


@pytest.mark.parametrize('change', ['scope', 'content_sha256', 'version'])
def test_declared_immutable_inputs_are_checked_against_child_scope_and_original_versions(host, change):
    reference = host.scope['subject_refs'][0]
    record = host.store.get(reference)
    version = {'reference': reference, 'version': str(record.get('revision')),
        'content_sha256': hashlib.sha256(host.store.get_artifact(record['sequence_ref'])).hexdigest()}
    selected = assignment(host.workspace, infernal_request('cmsearch'))
    original = launch_assignment(selected, versions=[version])
    parent = context(host, 'launch', original, 'input-parent')
    assert host.family.prepare_assignment(parent, 'launch_local', selected, host.scope, 'valid') == selected
    scope = host.scope
    if change == 'scope':
        scope = {'subject_refs': host.scope['subject_refs'][1:]}
        expected = 'execution_input_outside_assigned_scope'
    else:
        original['immutable_input_versions'][0][change] = '0' * 64 if change == 'content_sha256' else 'wrong-version'
        parent = context(host, 'launch', original, 'changed-input-parent')
        expected = 'execution_input_version_conflict'
    with pytest.raises(ValueError, match=expected):
        host.family.prepare_assignment(parent, 'launch_local', selected, scope, 'changed-input')
    child = context(host, 'launch_local', selected, 'changed-input-child', parent=parent, scope=scope)
    with pytest.raises(ValueError, match=expected):
        host.family.initialize(child)


def test_parent_and_resource_identity_are_required_at_their_actual_boundaries(host):
    selected = assignment(host.workspace, infernal_request('cmsearch'))
    parent = context(host, 'scientific_process', {}, 'not-a-launch')
    with pytest.raises(ValueError, match='resource_child_role_owned_by_launch'):
        host.family.prepare_assignment(parent, 'launch_local', selected, host.scope, 'wrong-owner')
    selected.pop('resource_id')
    with pytest.raises(ValueError, match='native_infernal_resource_identity_required'):
        LocalPracticalOperations(host.configuration).validate_assignment(selected)


@pytest.mark.parametrize('kind', ['api', 'hmmer_api', 'pbs_ssh'])
def test_unsupported_resource_bindings_reject_before_claiming_deployment(host, kind):
    expected_kind = 'hpc' if kind == 'pbs_ssh' else 'api'
    config = {key: value for key, value in host.configuration.items() if key != 'native_hmmer'}
    config['kind'] = kind
    with pytest.raises(ValueError, match='native_infernal_resource_execution_binding_unfinished:' + expected_kind):
        family_for(host, {'unavailable': config}, suffix='unsupported-' + kind)
    with pytest.raises(ValueError, match='native_infernal_resource_binding_unfinished:' + expected_kind):
        native_infernal_tool_contracts(config['native_infernal'], resource_kind=expected_kind,
            resource_id='unavailable')


def test_capability_information_does_not_acquire_execute_parse_or_calculate(host, monkeypatch):
    from gene_annotation_episode import (cmalign_grader, cmalign_inputs,
        infernal_search_grader, infernal_search_inputs, local_jobs,
        native_infernal_acquisition, native_infernal_driver, native_infernal_local,
        native_infernal_result_publication, native_infernal_result_worker,
        native_infernal_results, native_lifecycle)
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError('capability information performed acquisition, execution or grading')

    targets = [(socket, 'socket'), (subprocess, 'Popen'),
        (local_jobs, 'run_local_job'), (native_lifecycle, 'prepare_job'),
        (native_lifecycle, 'start_prepared'), (native_lifecycle, 'status'),
        (native_infernal_driver, 'run_native_infernal'),
        (native_infernal_local, 'prepare_local_infernal'),
        (native_infernal_acquisition, 'capture_local_bundle'),
        (native_infernal_results, 'capture_local_bundle'),
        (native_infernal_result_publication, 'prepare_native_infernal_grading'),
        (native_infernal_result_publication, 'publish_selected_native_infernal_rows'),
        (native_infernal_result_worker, 'run'),
        (infernal_search_inputs, 'populate_infernal_search_sheet'),
        (infernal_search_grader, 'calculate_infernal_search_scores'),
        (cmalign_inputs, 'parse_cmalign_stockholm'),
        (cmalign_inputs, 'populate_cmalign_sheet'), (cmalign_grader, 'calculate_cmalign_scores')]
    for module, name in targets:
        monkeypatch.setattr(module, name, forbidden)
    selected = assignment(host.workspace, infernal_request('cmsearch'))
    parent = context(host, 'launch', launch_assignment(selected), 'information-only')
    family = family_for(host, suffix='information-only')
    assert len([row for row in family.resource_tool_contracts() if row['name'].startswith('native.')]) == 4
    assert all(row['availability'] == 'unknown' for row in family.capabilities())
    information = family.initial_decision_context(parent)
    assert information['execution_resource_capabilities'][0]['policy'] == POLICY
    assert family.assignment_schema('launch')
    assert family.assignment_schema('launch_local')
    assert set(native_infernal_fact_sources()) <= set(family.fact_sources('results'))
    assert calls == []
    assert not list(host.workspace.rglob('native.json'))


def selector(family, rows):
    return {'version': 'native_infernal_result_selector_v1', 'acquisition': 'complete_bound_bundle',
        'projection': {'family': family, 'rows': deepcopy(rows), 'metrics': list(METRICS[family])}}


@pytest.mark.parametrize('program', PROGRAMS)
def test_result_consumer_preserves_explicit_family_metrics_and_row_selection(host, program):
    families = ('alignment_sequence', 'alignment_column', 'alignment_pair') if program == 'cmalign' else (
        'search_hit', 'search_sequence')
    target = {'resource_kind': 'local', 'assignment': assignment(host.workspace, infernal_request(program))}
    for family in families:
        for rows in ({'offset': 0, 'limit': 3}, {'record_keys': ['exact-retained-row-key']}):
            selected = selector(family, rows)
            original = deepcopy(selected)
            assert host.family._selector({'selector': selected}, target) == original
            assert validate_native_infernal_result_selector(selected, program=program) == original
            assert selected == original


@pytest.mark.parametrize('change', ['family', 'foreign_metric', 'unknown_metric', 'missing_metrics',
    'duplicate_metrics', 'empty_metrics', 'missing_rows', 'two_row_selectors', 'extra_field',
    'float_offset', 'unknown_acquisition', 'extra_mode'])
def test_invalid_result_choices_do_not_become_default_selections(host, change):
    selected = selector('search_hit', {'offset': 0, 'limit': 1})
    projection = selected['projection']
    if change == 'family':
        selected = selector('alignment_sequence', {'offset': 0, 'limit': 1})
    elif change == 'foreign_metric':
        projection['metrics'] = ['native_avg_pp']
    elif change == 'unknown_metric':
        projection['metrics'] = ['annotation_confidence']
    elif change == 'missing_metrics':
        projection.pop('metrics')
    elif change == 'duplicate_metrics':
        projection['metrics'] = ['bitscore', 'bitscore']
    elif change == 'empty_metrics':
        projection['metrics'] = []
    elif change == 'missing_rows':
        projection.pop('rows')
    elif change == 'two_row_selectors':
        projection['rows']['record_keys'] = ['row-key']
    elif change == 'extra_field':
        projection['take_best_hit'] = True
    elif change == 'float_offset':
        projection['rows']['offset'] = 0.0
    elif change == 'unknown_acquisition':
        selected['acquisition'] = 'first_hit_only'
    else:
        selected['mode'] = 'default'
    target = {'resource_kind': 'local', 'assignment': assignment(host.workspace, infernal_request('cmsearch'))}
    before = deepcopy(selected)
    with pytest.raises(ValueError, match='native_infernal_result_selector_'):
        host.family._selector({'selector': selected}, target)
    assert selected == before
    with pytest.raises(ValueError, match='native_infernal_result_program_unsupported'):
        validate_native_infernal_result_selector(selector('search_hit', {'offset': 0, 'limit': 1}),
            program='unknown-mode')


@pytest.mark.parametrize('family', METRICS)
def test_five_report_contracts_are_closed_and_keep_sequence_model_associations(host, family):
    assert NATIVE_INFERNAL_METRICS == METRICS
    source = FAMILY_SOURCES[family]
    descriptor = native_infernal_fact_sources()[source]
    schema = descriptor['report_schema']['items']
    assert schema == row_schema(family)
    assert host.family.fact_sources('results')[source] == descriptor
    assert host.family.received_report_sources('scientific_process')[source] == descriptor
    assert schema['additionalProperties'] is False
    assert set(schema['required']) == set(schema['properties'])
    properties = schema['properties']
    for field in ('measurements', 'unavailable'):
        item = properties[field]['items']
        assert item['additionalProperties'] is False
        assert item['properties']['name']['enum'] == list(METRICS[family])
    assert properties['sequence_name']['x-reference-namespace'] == 'native_infernal_sequence_name'
    assert properties['model_name']['x-reference-namespace'] == 'native_infernal_model_name'
    assert properties['subject_ref']['x-reference-namespace'] == 'subject'
    assert properties['reference_refs']['items']['x-reference-namespace'] == 'execution_result'
    # Shape-only placeholders are not published scientific measurements.
    row = {'record_key': 'declared-row-key', 'source_ref': 'declared-source', 'observation_ref': None,
        'subject_ref': None, 'reference_refs': [], 'sequence_name': 'physical-sequence',
        'model_name': 'covariance-model', 'strand': None, 'origin': None, 'population': None,
        'column_index': None, 'pair_columns': None, 'status': 'unbound', 'measurements': [],
        'unavailable': [{'name': metric, 'reason': 'missing_input'} for metric in METRICS[family]]}
    validator = Draft202012Validator(schema)
    assert validator.is_valid(row)
    extra = {**deepcopy(row), 'annotation_probability': 1}
    assert not validator.is_valid(extra)
    renamed = deepcopy(row)
    renamed['query_name'] = renamed.pop('sequence_name')
    assert not validator.is_valid(renamed)
    foreign = deepcopy(row)
    foreign['unavailable'][0]['name'] = 'annotation_confidence'
    assert not validator.is_valid(foreign)
