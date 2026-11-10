"""Receipt-scoped projection against the resource information reader contract."""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.resource_operational_credit import ResourceOperationalCredit


RUN = 'resource-credit-run'
REGISTRY = 'execution_registry_fixture'
SCOPE = {'target_refs': ['input_gene'], 'problem_ref': 'problem_gene'}
INPUTS = [{'reference': 'product_query', 'version': '1', 'content_sha256': 'a' * 64}]
ALLOCATION = {'cpu': 2, 'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}


def selection(kind='local'):
    return {'resource_id': 'resource_' + kind, 'kind': kind,
        'allocation': deepcopy(ALLOCATION), 'capability_binding_ref': REGISTRY}


def launch(selected=None):
    return {'version': 'resource_launch_assignment_v1',
        'job_request': {'query_ref': 'product_query', 'cpu': 2, 'search_mode': 'maximum_sensitivity'},
        'immutable_input_versions': deepcopy(INPUTS),
        'constraints': {'allowed_kinds': ['local', 'api', 'hpc'], **deepcopy(ALLOCATION)},
        'resource_selection': deepcopy(selected), 'software_knowledge_refs': [],
        'resource_knowledge_refs': []}


def handoff(job='homology_job_one', kind='local', checked_at='2026-10-21T00:00:00+00:00'):
    return {'version': 'execution_handoff_v1', 'execution_handle': job,
        'resource_selection': selection(kind), 'submitted_input_versions': deepcopy(INPUTS),
        'monitoring': {'provider_id': 'resource_' + kind, 'target_handle': job,
            'contract_ref': 'homology.status.v1'},
        'results': {'provider_id': 'resource_' + kind, 'target_handle': job,
            'contract_ref': 'homology.results.v1'},
        'checked_at': checked_at, 'check_record_refs': ['handoff_receipt_' + job],
        'state': 'usable', 'failure': None}


def proof(value=None):
    value = handoff() if value is None else deepcopy(value)
    return {'version': 'resource_handoff_information_v1', 'run_id': RUN,
        'episode_id': 'episode_original_child', 'operation_key': 'selected_check',
        'tool_name': 'homology.check_handoff', 'arguments': {}, 'scope': deepcopy(SCOPE),
        'assignment_sha256': 'b' * 64, 'query_ref': 'product_query', 'registry_ref': REGISTRY,
        'job': {'job_ref': value['execution_handle'], 'query_ref': 'product_query',
            'cpu': value['resource_selection']['allocation']['cpu'], 'search_mode': 'maximum_sensitivity'},
        'execution_handoff': value,
        'outcome': {'status': 'completed', 'result': {'receipt_ref': value['check_record_refs'][0]},
            'record_refs': [], 'changed_record_refs': [], 'feedback': None}}


def results_assignment(*, selector=None, adapter=True):
    value = {'version': 'resource_results_assignment_v1', 'handoff': handoff(),
        'requested_data_selector': {} if selector is None else deepcopy(selector)}
    if adapter:
        value['adapter_assignment'] = {'job_ref': 'homology_job_one', 'query_ref': 'product_query',
            'cpu': 2, 'search_mode': 'maximum_sensitivity'}
    return value


def context(role='launch', assignment=None):
    if assignment is None:
        assignment = results_assignment() if role == 'results' else launch(
            selection(role.removeprefix('launch_')) if role != 'launch' else None)
    return BindingContext(RUN, 'episode_receiver', role, ((role, 'fixture'),), SCOPE, assignment, {})


def receipts(known=(), initial=(), **extras):
    return {'run_id': RUN, 'episode_id': 'episode_receiver',
        'known_record_refs': list(known), 'initial_known_record_refs': list(initial), **extras}


def publication(reference, ordinal=1, snapshot='source_snapshot'):
    return {'snapshot_ref': snapshot, 'query_ref': 'product_query',
        'execution_context': {'job_ref': 'homology_job_one', 'registry_ref': REGISTRY},
        'ordinal': ordinal, 'record_ref': reference, 'record_type': 'observation',
        'source_byte_spans': [{'role': 'native_text', 'artifact_ref': 'artifact_text',
            'byte_span': [10 * ordinal, 10 * ordinal + 8]}]}


class Reader:
    """Only the three agreed reader methods are available to the projector."""
    def __init__(self, proofs=None, rows=()):
        self.definition = {'version': 'resource_information_reader_v1',
            'run_id': RUN, 'registry_ref': REGISTRY}
        self.proofs = deepcopy(proofs or {})
        self.rows = deepcopy(list(rows))
        self.reads, self.extractions = [], []
        # This unrelated worker's publications must never become a data port.
        self.global_rows = [publication('observation_foreign_global')]

    def as_record(self):
        return deepcopy(self.definition)

    def read_handoff_source(self, reference, *, scope):
        self.reads.append((reference, deepcopy(scope)))
        value = self.proofs.get(reference)
        if isinstance(value, Exception):
            raise value
        return deepcopy(value)

    def own_result_rows(self, bound):
        self.extractions.append(bound)
        return deepcopy(self.rows)


def projector(reader=None, **units):
    return ResourceOperationalCredit(Reader() if reader is None else reader,
        **{'handoff_unit': 3, 'acquired_record_unit': 0.5, **units})


@pytest.mark.parametrize('role,kind', [('launch', 'local'), ('launch_api', 'api'),
    ('launch_local', 'local'), ('launch_hpc', 'hpc')])
def test_all_launch_roles_project_received_child_proof_without_execution(role, kind):
    reader = Reader({'source_received': proof(handoff(kind=kind)), 'source_unreceived': proof(handoff('other_job'))})
    bound, credit = context(role), projector(reader)
    actual = credit(bound, receipts(['source_received', 'product_query', 'source_received'],
        known_progress_refs=['progress_one'], monitoring_information_credit=800))
    assert actual == {'credit': 3, 'operational_credit': 3,
        'operational_credit_binding': credit.as_record(), 'new_handoff_count': 1,
        'new_acquired_record_count': 0}
    assert reader.reads == [('source_received', SCOPE), ('product_query', SCOPE)]
    assert reader.extractions == []
    assert 'scientific_credit' not in actual and 'monitoring_information_credit' not in actual


def test_binding_preserves_exact_caller_units_and_finite_reader_identity():
    reader = Reader()
    credit = projector(reader, handoff_unit=7.25, acquired_record_unit=2)
    definition = credit.as_record()
    assert definition['version'] == 'received_resource_operational_credit_v1'
    assert definition['reader'] == reader.as_record()
    assert definition['handoff_unit'] == 7.25 and definition['acquired_record_unit'] == 2
    assert credit.requires_episode_receipts is True
    definition['reader']['registry_ref'] = 'changed'
    reader.definition['registry_ref'] = 'also_changed'
    assert credit.as_record()['reader']['registry_ref'] == REGISTRY
    json.dumps(credit.as_record(), allow_nan=False)


@pytest.mark.parametrize('unit', [True, False, None, '1', 0, -1, float('inf'), float('-inf'), float('nan')])
@pytest.mark.parametrize('field', ['handoff_unit', 'acquired_record_unit'])
def test_caller_units_must_be_positive_finite_numbers(field, unit):
    with pytest.raises(ValueError, match='explicit_positive_operational_credit_units_required'):
        projector(**{field: unit})


def test_units_are_required_and_reader_must_implement_exact_port():
    with pytest.raises(TypeError):
        ResourceOperationalCredit(Reader())
    with pytest.raises(TypeError, match='explicit_resource_information_reader_required'):
        projector(SimpleNamespace(as_record=lambda: {}))
    for definition in ({}, {'version': 'reader', 'registry_ref': ''},
            {'version': 'reader', 'registry_ref': REGISTRY, 'nan': float('nan')}):
        reader = Reader()
        reader.definition = definition
        with pytest.raises(ValueError, match='finite_resource_information_reader_identity_required'):
            projector(reader)


@pytest.mark.parametrize('change,code', [
    ({'run_id': 'other_run'}, 'receiver_identity_mismatch'),
    ({'episode_id': 'other_episode'}, 'receiver_identity_mismatch'),
    ({'initial_known_record_refs': ['unreceived']}, 'initial_references_must_be_known'),
    ({'known_record_refs': None}, 'explicit_record_references'),
    ({'known_record_refs': ['']}, 'explicit_record_references'),
    ({'initial_known_record_refs': [1]}, 'explicit_record_references')])
def test_receiver_identity_and_original_known_relationship_are_required(change, code):
    reader = Reader({'source_one': proof()})
    with pytest.raises(ValueError, match=code):
        projector(reader)(context(), {**receipts(['source_one']), **change})
    assert reader.reads == reader.extractions == []


@pytest.mark.parametrize('field', ['run_id', 'episode_id', 'known_record_refs', 'initial_known_record_refs'])
def test_receiver_selection_cannot_omit_identity_or_record_fields(field):
    selected = receipts()
    selected.pop(field)
    with pytest.raises(ValueError, match='receiver_identity_mismatch|explicit_record_references'):
        projector()(context(), selected)


@pytest.mark.parametrize('role', ['annotation', 'job_launch', 'job_results', 'monitor'])
def test_other_roles_are_rejected(role):
    with pytest.raises(ValueError, match='supported_resource_role'):
        projector()(context(role, launch()), receipts())


def test_repeated_checks_source_representations_and_initial_physical_identity_do_not_repeat_credit():
    first = proof()
    later = proof(handoff(checked_at='2026-10-21T01:00:00+00:00'))
    later['execution_handoff']['check_record_refs'] = ['handoff_receipt_later']
    later['operation_key'] = 'later_check'
    reader = Reader({'source_initial': first, 'source_later': later,
        'source_representation': first, 'source_new_job': proof(handoff('homology_job_two'))})
    credit = projector(reader)
    all_refs = ['source_later', 'source_representation', 'source_initial', 'source_new_job']
    assert credit(context(), receipts(all_refs))['new_handoff_count'] == 2
    assert credit(context(), receipts(all_refs, ['source_initial']))['new_handoff_count'] == 1
    assert credit(context(), receipts(all_refs, ['source_later', 'source_new_job']))['credit'] == 0


def test_initial_other_job_identity_does_not_require_matching_new_assignment():
    inherited = proof(handoff('homology_job_old'))
    inherited['job']['query_ref'] = inherited['query_ref'] = 'product_old_query'
    reader = Reader({'source_old': inherited, 'source_new': proof()})
    value = projector(reader)(context(), receipts(['source_old', 'source_new'], ['source_old']))
    assert value['credit'] == 3


@pytest.mark.parametrize('field,value', [('query_ref', 'other_query'), ('cpu', 1),
    ('search_mode', 'native_defaults'), ('existing_job_ref', 'other_job')])
def test_actual_immutable_job_facts_must_match_original_request(field, value):
    assignment = launch()
    assignment['job_request'][field] = value
    with pytest.raises(ValueError, match='job_request_mismatch:' + field):
        projector(Reader({'source_one': proof()}))(context(assignment=assignment), receipts(['source_one']))


def test_existing_job_request_matches_physical_identity_without_replacement():
    assignment = launch()
    assignment['job_request'] = {'existing_job_ref': 'homology_job_one'}
    assert projector(Reader({'source_one': proof()}))(
        context(assignment=assignment), receipts(['source_one']))['credit'] == 3


@pytest.mark.parametrize('field,value', [('allowed_resource_ids', ['elsewhere']), ('allowed_kinds', ['api']),
    ('resource_id', 'elsewhere'), ('kind', 'hpc'), ('cpu', 1), ('memory_bytes', 1),
    ('scratch_bytes', 1), ('wall_seconds', 1)])
def test_original_parent_constraints_are_preserved(field, value):
    assignment = launch()
    assignment['constraints'][field] = value
    with pytest.raises(ValueError, match='constraint_mismatch:' + field):
        projector(Reader({'source_one': proof()}))(context(assignment=assignment), receipts(['source_one']))


@pytest.mark.parametrize('part', ['job_request', 'constraints'])
def test_unknown_original_operands_are_not_silently_claimed_verified(part):
    assignment = launch()
    assignment[part]['unknown_requirement'] = 'must_be_verified'
    with pytest.raises(ValueError, match='unsupported_resource_credit_'):
        projector()(context(assignment=assignment), receipts())


def test_changed_input_versions_and_explicit_selection_are_rejected():
    assignment = launch()
    assignment['immutable_input_versions'][0]['content_sha256'] = 'c' * 64
    with pytest.raises(ValueError, match='input_versions_mismatch'):
        projector(Reader({'source_one': proof()}))(context(assignment=assignment), receipts(['source_one']))
    assignment = launch(selection('api'))
    with pytest.raises(ValueError, match='selection_mismatch'):
        projector(Reader({'source_one': proof()}))(context(assignment=assignment), receipts(['source_one']))


def test_resource_role_requires_explicit_selection_of_its_own_kind():
    with pytest.raises(ValueError, match='requires_explicit_selection'):
        projector()(context('launch_local', launch()), receipts())
    with pytest.raises(ValueError, match='selection_mismatch'):
        projector()(context('launch_hpc', launch(selection('local'))), receipts())


def test_original_adapter_assignment_must_match_immutable_job():
    assignment = launch(selection())
    assignment['adapter_assignment'] = {'job_ref': 'substituted_job', 'query_ref': 'product_query', 'cpu': 2}
    with pytest.raises(ValueError, match='adapter_assignment_mismatch'):
        projector(Reader({'source_one': proof()}))(context('launch_local', assignment), receipts(['source_one']))


def test_own_assignment_digest_is_checked_but_child_identity_is_not_rewritten():
    assignment = launch()
    assignment['software_knowledge_refs'] = ['knowledge_é']
    bound = context(assignment=assignment)
    own = proof()
    own['episode_id'] = bound.episode_id
    own['assignment_sha256'] = hashlib.sha256(json.dumps(assignment,
        sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    reader = Reader({'source_own': own})
    assert projector(reader)(bound, receipts(['source_own']))['credit'] == 3
    reader.proofs['source_own']['assignment_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='assignment_identity_mismatch'):
        projector(reader)(bound, receipts(['source_own']))


def test_recognized_reader_proof_errors_stay_failures_not_zero_credit():
    reader = Reader({'source_broken': ValueError('resource_information_scope_mismatch')})
    with pytest.raises(ValueError, match='resource_information_scope_mismatch'):
        projector(reader)(context(), receipts(['source_broken']))


@pytest.mark.parametrize('field', ['run_id', 'registry_ref', 'query_ref', 'job'])
def test_proof_identity_relationships_are_checked(field):
    value = proof()
    if field == 'job':
        value['job']['job_ref'] = 'other_job'
    else:
        value[field] = 'other_value'
    with pytest.raises(ValueError, match='proof_identity_mismatch'):
        projector(Reader({'source_one': value}))(context(), receipts(['source_one']))


def test_results_count_only_received_own_partial_publications_and_not_global_witnesses():
    rows = [publication('observation_partial', 1), publication('reference_partial', 2),
        publication('observation_unreceived', 3)]
    rows[1]['record_type'] = 'reference'
    reader = Reader({'source_handoff': proof()}, rows)
    selected = receipts(['source_handoff', 'observation_partial', 'reference_partial',
        'observation_foreign_global'], ['source_handoff'])
    value = projector(reader)(context('results'), selected)
    assert value['credit'] == value['operational_credit'] == 1
    assert value['new_handoff_count'] == 0 and value['new_acquired_record_count'] == 2
    assert len(reader.extractions) == 1 and reader.extractions[0].role == 'results'
    assert reader.reads == []


def test_initial_handoff_alone_earns_no_results_credit():
    reader = Reader({'source_handoff': proof()})
    value = projector(reader)(context('results'), receipts(['source_handoff'], ['source_handoff']))
    assert value['credit'] == value['new_handoff_count'] == value['new_acquired_record_count'] == 0


def test_results_repeated_pages_snapshots_and_canonical_duplicates_count_once():
    rows = [publication('observation_one', 1), publication('observation_one', 1),
        publication('observation_one', 7, 'source_other_snapshot'), publication('observation_two', 2)]
    credit = projector(Reader(rows=rows))
    assert credit(context('results'), receipts(['observation_one', 'observation_two']))['credit'] == 1


def test_results_require_the_actual_canonical_publication_reference_without_alias_rewriting():
    credit = projector(Reader(rows=[publication('observation_canonical')]))
    assert credit(context('results'), receipts(['some_alias']))['credit'] == 0
    assert credit(context('results'), receipts(['observation_canonical']))['credit'] == 0.5


def test_inherited_canonical_identity_is_seeded_before_later_own_witnesses():
    reader = Reader(rows=[])
    credit, bound = projector(reader), context('results')
    selected = receipts(['observation_inherited', 'observation_new'], ['observation_inherited'])
    assert credit(bound, selected)['credit'] == 0
    reader.rows.extend([publication('observation_inherited'), publication('observation_new', 2)])
    assert credit(bound, selected)['credit'] == 0.5
    # Another witness of the inherited semantic record does not change value.
    reader.rows.append(publication('observation_inherited', 3, 'source_other_snapshot'))
    assert credit(bound, selected)['credit'] == 0.5


def test_projection_preserves_signed_changes_when_received_prefix_changes():
    credit = projector(Reader(rows=[publication('observation_one'), publication('observation_two', 2)]))
    bound = context('results')
    earlier = credit(bound, receipts(['observation_one', 'observation_two']))['credit']
    later = credit(bound, receipts(['observation_one']))['credit']
    assert later - earlier == -0.5
    # There is no private cumulative clamp or stale remembered seen set.
    assert credit(bound, receipts(['observation_one', 'observation_two']))['credit'] == earlier


@pytest.mark.parametrize('field,value', [('query_ref', 'other_query'),
    ('execution_context', {'job_ref': 'other_job', 'registry_ref': REGISTRY})])
def test_own_publications_must_match_original_result_assignment(field, value):
    row = publication('observation_one')
    row[field] = value
    with pytest.raises(ValueError, match='publication_assignment_mismatch'):
        projector(Reader(rows=[row]))(context('results'), receipts(['observation_one']))


@pytest.mark.parametrize('ordinal', [1, 5])
def test_own_publication_ordinals_respect_zero_based_requested_interval(ordinal):
    bound = context('results', results_assignment(selector={'offset': 1, 'limit': 3}))
    with pytest.raises(ValueError, match='publication_selector_mismatch'):
        projector(Reader(rows=[publication('observation_one', ordinal)]))(
            bound, receipts(['observation_one']))


def test_requested_interval_permits_partial_rows_and_missing_optional_adapter():
    bound = context('results', results_assignment(selector={'offset': 1, 'limit': 3}, adapter=False))
    value = projector(Reader(rows=[publication('observation_one', 2)]))(bound, receipts(['observation_one']))
    assert value['credit'] == 0.5


@pytest.mark.parametrize('selector', [{'offset': True}, {'limit': True}, {'offset': -1},
    {'limit': -1}, {'unknown_selector': 1}])
def test_invalid_requested_selector_is_rejected_before_own_rows(selector):
    reader = Reader()
    with pytest.raises(ValueError, match='invalid_resource_credit_selector'):
        projector(reader)(context('results', results_assignment(selector=selector)), receipts())
    assert reader.extractions == []


def test_explicit_units_cannot_overflow_the_projected_score():
    reader = Reader({'source_one': proof(), 'source_two': proof(handoff('homology_job_two'))})
    with pytest.raises(ValueError, match='finite_operational_credit_required'):
        projector(reader, handoff_unit=1e308)(context(), receipts(['source_one', 'source_two']))
