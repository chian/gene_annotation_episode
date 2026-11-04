"""Lossless native/generic codec; fixture provenance is in P's inputs manifest."""
from copy import deepcopy
import hashlib

import pytest

from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.bvbrc_comparative_systems_publication import (
    encode_comparative_publication_result, decode_comparative_publication_result)
from gene_annotation_episode.bvbrc_comparative_systems_bundle_projection import assemble_projection, validate_saved_comparative_systems_projection
from gene_annotation_episode.execution_contracts import canonical
from test_bvbrc_comparative_systems_bundle import arguments, adapter


EMPTY_CONTEXT = {'retained_requirements': [], 'retained_diagnostics': [], 'failure_status': None}


def save_validate(result,args,context):
    validate_saved_comparative_systems_projection(result['sheet'],result['components'],
        **{key:result[key] for key in ('facts','status','missing_requirements','diagnostics')},
        **{key:args[key] for key in ('requested_form','parameters','bundle')},
        original_task=args['bundle']['original_task'],failure_context=context)


def stored(result, *, failure_context=EMPTY_CONTEXT):
    encoded = encode_comparative_publication_result(result, failure_context=failure_context)
    saved = {key: value for key, value in encoded.items() if key not in {'sheet', 'components'}}
    for key in ('sheet', 'components'):
        value = encoded[key]
        raw = canonical(value).encode()
        sha = hashlib.sha256(raw).hexdigest()
        saved[key + '_content'] = None if value is None else {'source_ref': 'source_' + sha[:24],
            'artifact_field': 'artifact_ref', 'artifact_ref': 'artifact_' + sha,
            'sha256': sha, 'byte_count': len(raw)}
    validate_contract('AdapterResult', saved)
    return saved, encoded['sheet'], encoded['components']


@pytest.mark.parametrize('missing', [False, True])
def test_full_native_arrays_round_trip_with_real_provider_and_saved_validation(missing, monkeypatch):
    args = arguments('families')
    if missing:
        args['bundle']['artifacts'] = []
    result = adapter.consume_bundle(**args)
    saved, sheet, components = stored(result)
    # Forbidden provider construction cannot be substituted by round-trip validation.
    def forbidden(*args, **kwargs): raise AssertionError('codec/saved validation recomputed science')
    monkeypatch.setattr(adapter, 'consume_bundle', forbidden)
    recovered, context = decode_comparative_publication_result(saved, sheet=sheet, components=components)
    assert recovered == result
    assert recovered['missing_requirements'] == result['missing_requirements']
    assert recovered['diagnostics'] == result['diagnostics']
    save_validate(recovered, args, context)
    assert components['calculations'] == result['components']
    for index, row in enumerate(saved['diagnostics']):
        assert row['path'] == '/diagnostics/' + str(index)
        assert row['evidence_refs'] == result['diagnostics'][index]['source_refs']


@pytest.mark.parametrize('state', ['partial', 'invalid'])
def test_null_numerical_objects_retain_native_failures_and_pass_saved_semantics(state):
    args = arguments('families')
    result = adapter.consume_bundle(**args)
    original_context = {**EMPTY_CONTEXT, 'failure_status': state}
    result = assemble_projection(None, None, requested_form=args['requested_form'],
        failure_context=original_context)
    # Null semantics retain no fabricated scientific values. P validates the
    # original form, task and parameters independently of this storage codec.
    saved, sheet, components = stored(result, failure_context=original_context)
    recovered, context = decode_comparative_publication_result(saved, sheet=sheet, components=components)
    assert recovered == result and sheet is None and components['calculations'] is None
    assert context == original_context
    save_validate(recovered, args, context)


@pytest.mark.parametrize('mutation', ['native_requirement', 'native_diagnostic', 'generic_requirement', 'generic_diagnostic', 'unknown_wrapper'])
def test_codec_rejects_native_or_summary_loss_and_relabeling(mutation):
    args = arguments('families')
    args['bundle']['artifacts'] = []
    saved, sheet, components = stored(adapter.consume_bundle(**args))
    saved, components = deepcopy(saved), deepcopy(components)
    if mutation == 'native_requirement': components['missing_requirements'][0]['code'] = 'invented'
    elif mutation == 'native_diagnostic': components['diagnostics'][0]['source_refs'] = ['substituted']
    elif mutation == 'generic_requirement': saved['missing_requirements'][0]['role'] = 'substituted'
    elif mutation == 'generic_diagnostic': saved['diagnostics'][0]['path'] = '/other/0'
    else: components['native_records_dropped'] = True
    with pytest.raises(ValueError):
        decode_comparative_publication_result(saved, sheet=sheet, components=components)


def test_sheet_without_calculations_retains_exact_original_failure_context():
    args=arguments('families')
    original=adapter.consume_bundle(**args)
    result=assemble_projection(original['sheet'],None,requested_form=args['requested_form'],failure_context=EMPTY_CONTEXT)
    saved,sheet,components=stored(result)
    recovered,context=decode_comparative_publication_result(saved,sheet=sheet,components=components)
    assert sheet==original['sheet'] and components['calculations'] is None
    assert context==EMPTY_CONTEXT and recovered==result
    save_validate(recovered,args,context)


def test_original_failure_records_equal_to_generated_records_survive_round_trip(monkeypatch):
    args=arguments('families')
    generated=assemble_projection(None,None,requested_form=args['requested_form'],failure_context=EMPTY_CONTEXT)
    original_context={'retained_requirements':deepcopy(generated['missing_requirements']),
        'retained_diagnostics':deepcopy(generated['diagnostics']),'failure_status':'partial'}
    result=assemble_projection(None,None,requested_form=args['requested_form'],failure_context=original_context)
    saved,sheet,components=stored(result,failure_context=original_context)
    from test_bvbrc_comparative_systems_episode_flow import forbid_science
    forbid_science(monkeypatch)
    recovered,context=decode_comparative_publication_result(saved,sheet=sheet,components=components)
    assert recovered==result and context==original_context
    assert context['retained_requirements']
    save_validate(recovered,args,context)
    context['failure_status']='invalid'
    with pytest.raises(ValueError): save_validate(recovered,args,context)


@pytest.mark.parametrize('change',['absent','unknown_key','bad_status','bad_requirement','old_version'])
def test_original_failure_context_and_explicit_wrapper_version_required(change):
    args=arguments('families')
    saved,sheet,components=stored(adapter.consume_bundle(**args))
    if change=='absent': components.pop('failure_context')
    elif change=='unknown_key': components['failure_context']['guessed_original']=True
    elif change=='bad_status': components['failure_context']['failure_status']='ok'
    elif change=='bad_requirement': components['failure_context']['retained_requirements']=[{'invented':True}]
    else:
        components['version']='bvbrc_comparative_systems_published_components_v1'
        components.pop('failure_context')
    with pytest.raises(ValueError): decode_comparative_publication_result(saved,sheet=sheet,components=components)
