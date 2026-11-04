"""Pre-acquisition selection over real pure constructors; host tests are separate."""
from copy import deepcopy

import pytest

from gene_annotation_episode import bvbrc_proteome_bundle_contracts as c
from gene_annotation_episode.bvbrc_appservice_contracts import ContractValidationError, validate_contract
from gene_annotation_episode.bvbrc_proteome_bundle_projection import validate_saved_projection
from test_bvbrc_proteome_bundle_resolution import fixture, consume, codes
from test_bvbrc_appservice_bundle_values import fixture as acquisition_fixture, dependency, bundle
from test_api_bvbrc_appservice import harness


def selected_case():
    case = fixture(supplementary=False)
    document = case['parameters']['native_documents'][0]
    document.pop('source_ref')
    document.pop('raw_artifact_ref')
    document['requirement_id'] = 'native'
    case['bundle']['artifacts'][0]['requirement_ids'] = ['native']
    return case


def saved_check(case, result, **overrides):
    args = dict(facts=result['facts'], status=result['status'],
        missing_requirements=tuple(result['missing_requirements']), diagnostics=tuple(result['diagnostics']),
        requested_form=case['requested_form'], parameters=case['parameters'],
        original_task=case['bundle']['original_task'], bundle_sha256=c.digest(case['bundle']), bundle=case['bundle'])
    args.update(overrides)
    return validate_saved_projection(result['sheet'], result['components'], **args)


def test_requirement_selection_resolves_actual_content_and_retains_exact_source_compatibility():
    logical = selected_case()
    exact = fixture(supplementary=False)
    result, historical = consume(logical), consume(exact)
    assert result['facts'] == historical['facts']
    assert result['facts']['identity_mean']['cell']['value'] == .4375
    assert result['facts']['endpoint_mean']['cell']['value'] == .625
    assert result['sheet']['input_resolution'][0]['content'] == historical['sheet']['input_resolution'][0]['content']
    assert saved_check(logical, result)['facts'] == result['facts']
    assert saved_check(exact, historical, bundle=None)['facts'] == historical['facts']
    with pytest.raises(c.ProteomeBundleError, match='saved_identity_conflict'):
        saved_check(logical, result, bundle=None)


@pytest.mark.parametrize('change', ['both_variants', 'empty', 'unknown_field', 'missing_format'])
def test_document_union_is_closed_and_disjoint(change):
    case = selected_case()
    document = case['parameters']['native_documents'][0]
    if change == 'both_variants':
        document.update(source_ref='future', raw_artifact_ref='future')
    elif change == 'empty': document['requirement_id'] = ''
    elif change == 'unknown_field': document['fallback'] = 'latest'
    else: document.pop('declared_format')
    with pytest.raises(c.ProteomeBundleError, match='parameters_invalid'):
        c.validate_parameters(case['parameters'])


@pytest.mark.parametrize('change,code', [
    ('unknown', 'document_missing'), ('absent', 'document_missing'),
    ('role', 'artifact_binding_conflict'), ('format', 'artifact_format_incompatible'),
    ('multiple', 'document_ambiguous'), ('duplicate_selection', 'document_ambiguous'),
    ('duplicate_exact', 'document_ambiguous'), ('hash', 'artifact_digest_mismatch'),
    ('range', 'nonzero_range_unsupported')])
def test_requirement_selection_never_guesses_an_alternative(change, code):
    case = selected_case()
    member = case['bundle']['artifacts'][0]
    if change == 'unknown': case['parameters']['native_documents'][0]['requirement_id'] = 'unknown'
    elif change == 'absent': member.pop('requirement_ids')
    elif change == 'role': member['role'] = 'task_manifest'
    elif change == 'format': member['declared_format']['format'] = 'json'
    elif change == 'multiple': case['bundle']['artifacts'].append(deepcopy(member))
    elif change in {'duplicate_selection', 'duplicate_exact'}:
        other = deepcopy(case['parameters']['native_documents'][0])
        other['document_id'] = 'other'
        if change == 'duplicate_exact':
            other.pop('requirement_id')
            other.update(source_ref=member['source_ref'], raw_artifact_ref=member['raw_artifact_ref'])
        case['parameters']['native_documents'].append(other)
    elif change == 'hash': member['sha256'] = '0' * 64
    else: member['transfer'].update(object_complete='no', requested_range=[10, None], observed_range=None)
    result = consume(case)
    assert 'proteome_' + code in codes(result)
    assert result['facts']['identity_mean']['availability'] == 'unavailable'
    assert saved_check(case, result)['facts'] == result['facts']


def test_wrong_task_and_incomplete_bytes_keep_distinct_meanings():
    case = selected_case()
    case['bundle']['artifacts'][0]['task_association']['task_id'] = 'wrong'
    with pytest.raises(c.ProteomeBundleError, match='original_task_conflict'):
        consume(case)
    case = selected_case()
    case['bundle']['artifacts'][0]['transfer'].update(body_complete=False, object_complete='no')
    result = consume(case)
    assert result['facts']['identity_mean']['cell']['value'] == .4375
    assert result['sheet']['native_results'][0]['value']['source']['body_complete'] is False
    assert result['missing_requirements']
    saved_check(case, result)


@pytest.mark.parametrize('change', ['membership', 'source', 'primary', 'hash', 'task', 'complete', 'role', 'format', 'range'])
def test_saved_membership_identity_and_transfer_tampering_rejected(change):
    case = selected_case()
    result = consume(case)
    if change == 'membership': case['bundle']['artifacts'][0]['requirement_ids'] = ['other']
    elif change == 'source': result['sheet']['input_resolution'][0]['content']['source_ref'] = 'other'
    elif change == 'primary': result['sheet']['native_sheet_result']['value']['primary_source_ref'] = 'other'
    elif change == 'hash': case['bundle']['artifacts'][0]['sha256'] = '0' * 64
    elif change == 'task': case['bundle']['original_task']['task_id'] = 'other'
    elif change == 'role': case['bundle']['artifacts'][0]['role'] = 'wrong'
    elif change == 'format': case['bundle']['artifacts'][0]['declared_format']['format'] = 'json'
    elif change == 'range': case['bundle']['artifacts'][0]['transfer'].update(object_complete='no', requested_range=[10, None])
    else: case['bundle']['artifacts'][0]['transfer'].update(body_complete=False, object_complete='no')
    # Rehash the altered bundle as an adversarial shape-valid value. The pure
    # validator must check the relationship, not merely the earlier digest.
    result['sheet']['bundle_sha256'] = c.digest(case['bundle'])
    with pytest.raises(c.ProteomeBundleError): saved_check(case, result)


def test_actual_member_membership_survives_acquisition_and_bundle(harness):
    case = acquisition_fixture(harness)
    acquired = dependency(case)
    assert acquired['receipt']['artifact']['requirement_ids'] == ['r1']
    assert bundle(case, [acquired])['artifacts'][0]['requirement_ids'] == ['r1']
    acquired['receipt']['artifact'].pop('requirement_ids')
    historical = bundle(case, [acquired])
    assert 'requirement_ids' not in historical['artifacts'][0]


@pytest.mark.parametrize('change', ['member', 'receipt', 'selected'])
def test_acquisition_receipt_member_and_selected_membership_must_agree(harness, change):
    case = acquisition_fixture(harness)
    acquired = dependency(case)
    if change == 'member': acquired['receipt']['artifact']['requirement_ids'] = []
    elif change == 'receipt': acquired['receipt']['requirement_ids'] = []
    else:
        acquired['receipt']['snapshot']['selected_operands']['native_operands']['arguments']['requirement_ids'] = []
    with pytest.raises(ContractValidationError): bundle(case, [acquired])


@pytest.mark.parametrize('value', [['r1', 'r1'], [''], [2], 'r1'])
def test_membership_array_has_unique_nonempty_strings(value):
    member = selected_case()['bundle']['artifacts'][0]
    member['requirement_ids'] = value
    with pytest.raises(ContractValidationError): validate_contract('ArtifactMember', member)


def test_requirement_variant_requires_actual_bundle_even_for_empty_saved_projection():
    case = selected_case()
    args = dict(facts={}, status='invalid', missing_requirements=(), diagnostics=(),
        requested_form=case['requested_form'], parameters=case['parameters'],
        original_task=case['bundle']['original_task'], bundle_sha256=c.digest(case['bundle']))
    with pytest.raises(c.ProteomeBundleError, match='saved_identity_conflict'):
        validate_saved_projection(None, None, **args)
    assert validate_saved_projection(None, None, bundle=case['bundle'], **args)['status'] == 'invalid'


def test_missing_secondary_requirement_preserves_available_primary_facts():
    case = selected_case()
    other = deepcopy(case['parameters']['native_documents'][0])
    other.update(document_id='missing-secondary', requirement_id='not-acquired')
    case['parameters']['native_documents'].append(other)
    result = consume(case)
    assert result['facts']['identity_mean']['cell']['value'] == .4375
    assert 'proteome_document_missing' in codes(result)
    assert saved_check(case, result)['facts'] == result['facts']
