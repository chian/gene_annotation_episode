"""Live v3 reading custody, staged-call misuse and reported-uncertainty unit conflicts.

Constructed source text and pixels only (the v3 constructed selections, with
appended constructed sentences); no paper, model or native execution. Every live
read that succeeds is also revalidated from its saved record.
"""
from copy import deepcopy as cp
import errno
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence import literature_controlled_response_v3_inputs as source
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence import literature_controlled_response_inputs as shared
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_controlled_response_v3_inputs import Fixture, CASES
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_controlled_response_v3_stages import fixture as staged, read_arm, stages
ROLES = shared.PRIMITIVE_ORDER
A, B1, C, B0 = ROLES
IMAGE_REF = 'source_979d278d85fd521cd4113e07'
UNKNOWN_REF = 'source_' + 'e' * 24


def primary(role):
    return {'role': role, 'reading_key': None}


def read_and_resave(f, read_source=None):
    result = source.read_controlled_response_v3_inputs(f.args, read_source=read_source or f.source)
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result
    return result


def codes(record):
    return [d['code'] for d in record['diagnostics']]


def test_one_artifact_reference_cannot_name_two_contents():
    f = Fixture(0)

    def aliased(reference, representation):
        return {'artifact_ref': 'artifact_constructed_alias', 'content': f.source(reference, representation)['content']}
    with pytest.raises(ExperimentalContractError, match='artifact_content_conflict'):
        source.read_controlled_response_v3_inputs(f.args, read_source=aliased)


def test_open_context_serves_only_its_nominated_closure_and_nothing_after_close():
    f = staged()
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        assert context.read_source(f.main_ref, 'original')['content'] == f.data[f.main_ref]
        with pytest.raises(ExperimentalContractError, match='unselected_source_read'):
            context.read_source(UNKNOWN_REF, 'original')
        arm = context.arguments['arms'][A]
    with pytest.raises(ExperimentalContractError, match='source_context_closed'):
        context.read_source(f.main_ref, 'original')
    with pytest.raises(ExperimentalContractError, match='source_context_closed'):
        shared.read_controlled_response_arm_science(context, arm, reading_selector=primary(A))


def test_image_witness_of_an_unavailable_image_is_a_dependency_partial():
    f = Fixture(0)
    witness = {'kind': 'image', 'image_id': 'constructed', 'region': [20, 10, 30, 20], 'quote': 'constructed bar region'}
    f.args['arms'][A]['intended_factor_level'] = witness
    available = read_and_resave(f)
    assert available['arms'][A]['intended_factor_level']['authentication'] == 'image_bytes_and_geometry_only'

    def missing_image(reference, representation):
        if reference == IMAGE_REF:
            raise FileNotFoundError(errno.ENOENT, 'constructed missing image')
        return f.source(reference, representation)
    result = read_and_resave(f, missing_image)
    record = result['arms'][A]['intended_factor_level']
    assert record['canonical_locator'] is None and record['authentication'] == 'unavailable'
    assert record['diagnostics'] == [{'code': 'source_dependency_unavailable', 'field': 'arms.protein_condition1.intended_factor_level', 'domain': 'dependency', 'source_refs': [IMAGE_REF]}]
    assert result['arms'][B0]['measurement']['reading_status'] == 'dependency_unavailable'


def test_endpoint_that_was_not_read_in_this_context_is_refused():
    f = staged()
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        arm = context.arguments['arms'][A]
        science = shared.read_controlled_response_arm_science(context, arm, reading_selector=primary(A))
        with pytest.raises(ExperimentalContractError, match='source_stage_context_mismatch'):
            shared.read_controlled_response_text_measurement(context, arm['measurement'], endpoint=cp(science['meanings']['endpoint']), reading_selector=primary(A))


def test_text_and_graph_readers_refuse_the_other_measurement_kind():
    f = staged()
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        bar, text = (context.arguments['arms'][B0], context.arguments['arms'][A])
        bar_science = shared.read_controlled_response_arm_science(context, bar, reading_selector=primary(B0))
        with pytest.raises(ExperimentalContractError, match='source_text_measurement_required'):
            shared.read_controlled_response_text_measurement(context, bar['measurement'], endpoint=bar_science['meanings']['endpoint'], reading_selector=primary(B0))
        text_science = shared.read_controlled_response_arm_science(context, text, reading_selector=primary(A))
        with pytest.raises(ExperimentalContractError, match='source_graph_measurement_required'):
            shared.read_controlled_response_graph_measurement(context, primary(A), endpoint=text_science['meanings']['endpoint'])


def test_scope_binding_takes_exactly_the_scope_readings_in_original_order():
    f = staged(joint=False, local=False)
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        rows = {role: read_arm(context, primary(role)) for role in ROLES}
        base = {'kind': 'base', 'index': None}
        document = shared.read_controlled_response_covariance_document(context, base)
        readings = [(primary(role), rows[role]) for role in ROLES]
        with pytest.raises(ExperimentalContractError, match='source_covariance_reading_roster_mismatch'):
            shared.bind_controlled_response_covariance_scope(context, base, document, readings=readings[:3])
        with pytest.raises(ExperimentalContractError, match='source_covariance_reading_roster_mismatch'):
            shared.bind_controlled_response_covariance_scope(context, base, document, readings=readings[::-1])
        bound = shared.bind_controlled_response_covariance_scope(context, base, document, readings=readings)
        assert bound['whole_projection']['projection_state'] == 'available'
        with pytest.raises(ExperimentalContractError, match='source_covariance_scope_roster_mismatch'):
            shared.finish_controlled_response_inputs(context, arms=rows, companion_arms=[], covariance_scopes=[])
        with pytest.raises(ExperimentalContractError, match='source_companion_roster_mismatch'):
            shared.finish_controlled_response_inputs(context, arms=rows, companion_arms=[(primary(A), rows[A])], covariance_scopes=[bound])


def test_unnominated_arm_cannot_be_bound_into_a_scope():
    f = staged(joint=False, local=False)
    f.args['arms'][A] = None
    f.args['covariance']['bindings'][A] = None
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        rows = {role: read_arm(context, primary(role)) for role in ROLES[1:]}
        base = {'kind': 'base', 'index': None}
        document = shared.read_controlled_response_covariance_document(context, base)
        readings = [(primary(A), rows[C])] + [(primary(role), rows[role]) for role in ROLES[1:]]
        with pytest.raises(ExperimentalContractError, match='source_stage_arm_mismatch'):
            shared.bind_controlled_response_covariance_scope(context, base, document, readings=readings)


def test_scope_without_a_nominated_document_cannot_take_one():
    f = staged(joint=False)
    f.args['covariance'] = None
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        rows = {role: read_arm(context, primary(role)) for role in ROLES}
        base, local = ({'kind': 'base', 'index': None}, {'kind': 'local', 'index': 0})
        assert shared.read_controlled_response_covariance_document(context, base) is None
        other = shared.read_controlled_response_covariance_document(context, local)
        with pytest.raises(ExperimentalContractError, match='source_covariance_document_mismatch'):
            shared.bind_controlled_response_covariance_scope(context, base, other, readings=[(primary(role), rows[role]) for role in ROLES])


def test_saved_context_reads_only_saved_documents_and_nothing_after_close():
    f = Fixture(0)
    result = f.read()
    selected = source.validate_controlled_response_v3_selection(f.args)
    context = shared._SavedV3SourceContext(selected, result)
    assert context.source(f.cov_ref, 'original')['content'] == f.data[f.cov_ref]
    with pytest.raises(ExperimentalContractError, match='unselected_source_read'):
        context.source(f.main_ref, 'original')
    with pytest.raises(ExperimentalContractError, match='saved_witness_missing'):
        context.witness({'kind': 'text', 'source_ref': f.main_ref, 'representation': 'original', 'start': 0, 'end': 3, 'quote': '<p>'}, 'probe')
    context.arguments['relationships']['nonintended_conditions']['value'] = 'unknown'
    with pytest.raises(ExperimentalContractError, match='source_context_nomination_mismatch'):
        shared._reading_entry(context, primary(A))
    context.close()
    with pytest.raises(ExperimentalContractError, match='source_context_closed'):
        shared._reading_entry(context, primary(A))


def with_sd(f, quote=None):
    """Reported SD for the A text reading (10 nmol/min); `quote` replaces the SD sentence."""
    uncertainty = cp(CASES[6]['selection']['arms'][A]['reported_uncertainty'])
    if quote is not None:
        f.append(quote)
        uncertainty['magnitude'] = f.number(quote, '1.2')
        uncertainty['statistic'] = f.interp('sd', quote)
    f.args['arms'][A]['reported_uncertainty'] = uncertainty
    return uncertainty


def with_ci(f, quote, lower='8', upper='12'):
    uncertainty = cp(CASES[7]['selection']['arms'][A]['reported_uncertainty'])
    f.append(quote)
    uncertainty.update(statistic=f.interp('ci', quote), interval={'witness': f.witness(quote, tagged=False), 'lower_start': quote.index(lower), 'lower_end': quote.index(lower) + len(lower), 'upper_start': quote.index(upper), 'upper_end': quote.index(upper) + len(upper)}, confidence_level=None, count=None)
    f.args['arms'][A]['reported_uncertainty'] = uncertainty
    return uncertainty


def conflicted(result):
    uncertainty = result['arms'][A]['reported_uncertainty']
    assert 'source_uncertainty_unit_conflicting' in codes(uncertainty)
    assert uncertainty['effective_unit'] is None
    return uncertainty['canonical']


def test_reported_sd_round_trips_in_the_response_unit():
    f = Fixture(0)
    with_sd(f)
    canonical = read_and_resave(f)['arms'][A]['reported_uncertainty']['canonical']
    # 1.2 nmol/min in canonical umol/min: 1.2 / 1000 = 0.0012.
    assert canonical['magnitude'] == 0.0012 and canonical['count'] == 3


def test_conflicting_uncertainty_unit_relationship_has_no_unit():
    f = Fixture(0)
    uncertainty = with_sd(f)
    uncertainty['unit_relationship'] = {'value': 'conflicting', 'witnesses': [f.witness('Plot unit: nmol/min.'), f.witness('Reported SD: 1.2 nmol/min.')]}
    canonical = conflicted(read_and_resave(f))
    assert canonical['magnitude'] is None and canonical['statistic'] == 'sd'


def test_same_as_response_with_a_different_explicit_unit_conflicts():
    f = Fixture(0)
    uncertainty = with_sd(f)
    f.append('Other unit: umol/min.')
    uncertainty['unit'] = f.witness('umol/min', tagged=False)
    canonical = conflicted(read_and_resave(f))
    assert canonical['magnitude'] is None


def test_sd_printed_in_another_unit_than_the_response_conflicts():
    f = Fixture(0)
    with_sd(f, 'Reported alternate SD: 1.2 umol/min.')
    canonical = conflicted(read_and_resave(f))
    assert canonical['magnitude'] is None


def test_ci_printed_in_another_unit_than_the_response_conflicts():
    f = Fixture(0)
    with_ci(f, 'Reported alternate CI: [8, 12] umol/min.')
    canonical = conflicted(read_and_resave(f))
    assert canonical['statistic'] == 'ci' and canonical['interval'] is None


def test_ci_bounds_that_collapse_in_double_precision_are_not_a_zero_width_interval():
    # Exact bounds 1.00000000000000001 and 1.00000000000000002 nmol/min differ, but both
    # become the same double after scaling to umol/min, so no interval is reported.
    f = Fixture(0)
    with_ci(f, 'Reported narrow CI: [1.00000000000000001, 1.00000000000000002] nmol/min.', '1.00000000000000001', '1.00000000000000002')
    uncertainty = read_and_resave(f)['arms'][A]['reported_uncertainty']
    assert uncertainty['interval']['status'] == 'parsed'
    assert uncertainty['canonical']['interval'] is None
    assert {'code': 'source_numeric_range', 'field': 'arms.protein_condition1.reported_uncertainty.interval', 'domain': 'reader_capability', 'source_refs': []} in uncertainty['diagnostics']


def test_registered_reading_whose_canonical_display_overflows_keeps_its_native_value():
    # 1e306 mmol/min is a finite double in its own unit; in umol/min it is 1e309, beyond double range.
    f = Fixture(0)
    f.text_measurement(A, 'A huge mean: 1e306 mmol/min.', '1e306', unit='mmol/min')
    arm = read_and_resave(f)['arms'][A]
    assert arm['measurement']['reading_status'] == 'exact'
    assert arm['measurement']['canonical_display']['value'] is None
    assert arm['measurement']['canonical_display']['diagnostics'] == [{'code': 'source_numeric_range', 'field': 'canonical_display', 'domain': 'reader_capability', 'source_refs': []}]
    assert arm['calculation_operand']['value'] == 1e306 and arm['calculation_operand']['unit'] == 'mmol/min'


@pytest.mark.parametrize('read_source,code', [
    (None, 'source_reader_required'),
    (lambda reference, representation: {'content': b'constructed'}, 'closed_fields_required'),
    (lambda reference, representation: {'artifact_ref': ' ', 'content': b'constructed'}, 'malformed_source_result'),
    (lambda reference, representation: {'artifact_ref': 'artifact_constructed', 'content': 'constructed'}, 'malformed_source_result'),
], ids=['not_callable', 'open_result', 'blank_artifact', 'text_content'])
def test_source_reader_result_contract(read_source, code):
    f = Fixture(0)
    with pytest.raises(ExperimentalContractError) as error:
        source.read_controlled_response_v3_inputs(f.args, read_source=read_source)
    assert error.value.code == code


def test_sd_statistic_with_an_interval_is_a_conflicting_uncertainty_meaning():
    f = Fixture(0)
    uncertainty = with_sd(f)
    uncertainty['interval'] = cp(CASES[7]['selection']['arms'][A]['reported_uncertainty']['interval'])
    result = read_and_resave(f)
    canonical = result['arms'][A]['reported_uncertainty']['canonical']
    assert canonical['statistic'] == 'conflicting'
    assert 'source_uncertainty_meaning_conflict' in codes(result['arms'][A]['reported_uncertainty'])


def test_finished_arms_must_match_the_nominated_roster():
    f = staged(joint=False, local=False)
    f.args['arms'][A] = None
    f.args['covariance']['bindings'][A] = None
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        rows = {role: read_arm(context, primary(role)) for role in ROLES[1:]}
        rows[A] = rows[C]
        with pytest.raises(ExperimentalContractError, match='source_stage_arm_mismatch'):
            shared.finish_controlled_response_inputs(context, arms=rows, companion_arms=[], covariance_scopes=[])
    g = staged(companion=True)
    with shared.open_controlled_response_sources(g.args, read_source=g.source) as context:
        rows, scopes = stages(context)
        arms = {role: rows[role, None] for role in ROLES}
        companion = rows[A, 'same-A']
        with pytest.raises(ExperimentalContractError, match='source_companion_roster_mismatch'):
            shared.finish_controlled_response_inputs(context, arms=arms, companion_arms=[({'role': A, 'reading_key': 'other-A'}, companion)], covariance_scopes=scopes)
