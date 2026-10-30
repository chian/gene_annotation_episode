"""Pure HMMER failure projection over native records and labeled synthetic faults."""
from copy import deepcopy

import pytest

from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.hmmer_preparation_result_views import preparation_fact_sources
from gene_annotation_episode.native_hmmer_preparation_failure_views import preparation_failure_facts
from test_native_hmmer_preparation_acquisition import RETAINED, read_native, selected_native


PREFIX = 'native_hmmer_preparation_'
BUNDLE_REF = 'artifact_' + 'a' * 64


def body_for(bundle):
    return {'assignment': {'handoff_ref': 'source_original_handoff'}, 'source_ref': 'source_original_result',
        'capture': {'bundle_artifact_ref': BUNDLE_REF}, 'prepared': {'occurrences': []},
        'failures': [{'code': row['code'], 'stage': row['stage'], 'record_key': BUNDLE_REF + '#/failures/' + str(index)}
            for index, row in enumerate(bundle['failures'])]}


def query_failure(line=7, *, role='queries', code='invalid_exactmatch_queries'):
    # Original native operand geometry; the injected failure explicitly tests
    # a later query line without claiming another native execution.
    _, bundle = selected_native('hmmerfm-exactmatch', 'count_only')
    bundle['failures'] = [{'stage': 'preflight', 'code': PREFIX + code, 'role': role,
        'detail': {'ordinal': line, 'reason': 'query_empty'}}]
    return body_for(bundle), bundle


def test_query_line7_is_not_input_artifact_ordinal0_and_no_new_work(monkeypatch):
    body, bundle = query_failure()
    before = deepcopy((body, bundle))
    def forbidden(*args, **kwargs):
        raise AssertionError('Failure projection attempted IO or new work')
    for name in ('builtins.open', 'socket.socket', 'subprocess.Popen'):
        monkeypatch.setattr(name, forbidden)
    row, = preparation_failure_facts(body, bundle=bundle)
    assert row['stage'] == 'preflight'
    assert row['code'] == PREFIX + 'invalid_exactmatch_queries'
    assert row['affected'] == {'direction': 'input', 'role': 'queries', 'ordinal': 0}
    assert row['record_key'] == BUNDLE_REF + '#/failures/0'
    schema = {'type': 'object', 'additionalProperties': False,
        'properties': {'failures': preparation_fact_sources()['execution_hmmer_preparation_failures']['report_schema']},
        'required': ['failures']}
    assert validate_form({'failures': [row]}, schema, lambda *_: True) == {'failures': [row]}
    assert (body, bundle) == before


@pytest.mark.parametrize('code,role,program,mode', [
    ('invalid_alimask_input', 'alignment', 'alimask', 'mask_alignment'),
    ('invalid_model_format', 'models', 'hmmconvert', 'binary'),
    ('incompatible_fm_abi', 'fm_database', 'hmmerfm-exactmatch', 'count_only'),
    ('source_binding_digest_mismatch', 'source_sequences', 'hmmerfm-exactmatch', 'count_only'),
])
def test_other_preflight_uses_only_actual_unique_selected_operand(code, role, program, mode):
    # Roles come from each retained invocation; only the failure is synthetic.
    if program == 'alimask':
        from gene_annotation_episode.native_hmmer_preparation_contracts import PROGRAM_MODES
        mode = next(iter(PROGRAM_MODES[program]))
    _, bundle = selected_native(program, mode)
    bundle['failures'] = [{'stage': 'preflight', 'code': PREFIX + code, 'role': role, 'detail': {'reason': 'fixture'}}]
    body = body_for(bundle)
    result, = preparation_failure_facts(body, bundle=bundle)
    matching = [r for r in bundle['inputs'] if r['role'] == role]
    expected = {'direction': 'input', 'role': role, 'ordinal': matching[0]['ordinal']} if len(matching) == 1 else None
    assert result['affected'] == expected and result['stage'] == 'preflight'
    if role == 'source_sequences':
        extra = deepcopy(matching[0]); extra['ordinal'] += 1
        bundle['inputs'].append(extra)
        assert preparation_failure_facts(body, bundle=bundle)[0]['affected'] is None


@pytest.mark.parametrize('fault', ['stage', 'code', 'locator', 'foreign_bundle', 'role'])
def test_native_failure_locator_stage_code_and_operand_agreement_reject(fault):
    body, bundle = query_failure()
    if fault == 'stage': body['failures'][0]['stage'] = 'inputs'
    elif fault == 'code': body['failures'][0]['code'] = PREFIX + 'invalid_model_format'
    elif fault == 'locator': body['failures'][0]['record_key'] = BUNDLE_REF + '#/failures/01'
    elif fault == 'foreign_bundle': body['failures'][0]['record_key'] = 'artifact_wrong#/failures/0'
    else: bundle['failures'][0]['role'] = 'fm_database'
    with pytest.raises(ValueError, match='failure_locator_conflict'):
        preparation_failure_facts(body, bundle=bundle)


def test_actual_nonzero_and_missing_outputs_keep_native_failure_meanings():
    _, bundle = read_native(RETAINED / 'test_actual_press_native_refus0/plan.json')
    body = body_for(bundle)
    rows = preparation_failure_facts(body, bundle=bundle)
    assert rows[0]['stage'] == 'execution' and rows[0]['affected'] is None
    assert {row['affected']['role'] for row in rows[1:]} == {'binary_models', 'ssi_index', 'msv_profiles', 'remaining_profiles'}
    assert all(row['stage'] == 'outputs' and row['affected']['ordinal'] == 0 for row in rows[1:])
    body['failures'] *= 2
    assert preparation_failure_facts(body, bundle=bundle) == rows


def test_occurrence_id_key_is_used_without_infernal_alias_or_nearby_name():
    body, bundle = query_failure(0)
    occurrence = {'occurrence_id': BUNDLE_REF + '#/inputs/0', 'direction': 'input', 'role': 'queries', 'ordinal': 0}
    body['prepared']['occurrences'] = [occurrence]
    body['failures'][0]['record_key'] = occurrence['occurrence_id']
    assert preparation_failure_facts(body, bundle=bundle)[0]['affected'] == {'direction': 'input', 'role': 'queries', 'ordinal': 0}
    body['prepared']['occurrences'][0]['role'] = 'fm_database'
    with pytest.raises(ValueError, match='failure_locator_conflict'):
        preparation_failure_facts(body, bundle=bundle)
    body['failures'] = [{'stage': 'format', 'code': 'hmmer_model_unrecognized_signature',
        'record_key': occurrence['occurrence_id'] + '#model/0'}]
    assert preparation_failure_facts(body, bundle=bundle)[0]['affected']['role'] == 'fm_database'


@pytest.mark.parametrize('fault', ['role', 'ordinal', 'path'])
def test_capture_file_failure_requires_exact_selected_file(fault):
    _, bundle = selected_native('hmmconvert', 'binary')
    body = body_for(bundle)
    row = next(r for r in bundle['artifacts'] if r['role'] == 'converted_models')
    parts = [PREFIX + 'sealed_artifact_digest_mismatch', 'output', row['role'], '0', row['relative_path']]
    body['failures'] = [{'stage': 'capture', 'code': ':'.join(parts), 'record_key': None}]
    assert preparation_failure_facts(body, bundle=bundle)[0]['affected'] == {'direction': 'output', 'role': 'converted_models', 'ordinal': 0}
    parts[{'role': 2, 'ordinal': 3, 'path': 4}[fault]] = 'wrong'
    body['failures'][0]['code'] = ':'.join(parts)
    with pytest.raises(ValueError, match='failure_file_association_conflict'):
        preparation_failure_facts(body, bundle=bundle)


def test_exception_prose_and_unknown_stage_are_explicit_fallback_not_claims():
    body, _ = query_failure()
    body.update(source_ref=None, capture=None, prepared=None, failures=[{
        'stage': 'made up stage', 'code': 'Unexpected sentence at /private/path.', 'record_key': None}])
    row, = preparation_failure_facts(body)
    assert row == {'handoff_ref': 'source_original_handoff', 'source_ref': None,
        'stage': 'unclassified', 'code': PREFIX + 'unclassified_error', 'record_key': None, 'affected': None}


@pytest.mark.parametrize('case,code,role', [
    ('test_imported_fm_contract_and_0', 'incompatible_fm_abi', 'fm_database'),
    ('test_imported_fm_contract_and_1', 'source_binding_digest_mismatch', 'source_sequences'),
    ('test_invalid_query_bytes_are_n0', 'invalid_exactmatch_queries', 'queries'),
    ('test_missing_wrong_and_stale_i2', 'invalid_model_format', 'models'),
    ('test_supplied_fm_structure_is_0', 'invalid_fm_database', 'fm_database'),
    ('test_unsafe_or_unestablished_m0', 'unsafe_alimask_range', 'alignment'),
    ('test_unsafe_or_unestablished_m1', 'unsupported_alimask_model_map', 'alignment'),
])
def test_actual_retained_preflight_records_preserve_stage_and_operand(case, code, role):
    import json
    bundle = json.loads((RETAINED / case / 'hmmer-preparation-attempt/bundle.json').read_bytes())
    assert any(row['stage'] == 'preflight' and row['code'] == PREFIX + code for row in bundle['failures'])
    rows = preparation_failure_facts(body_for(bundle), bundle=bundle)
    selected = next(row for row in rows if row['code'] == PREFIX + code)
    assert selected['stage'] == 'preflight'
    operands = [row for row in bundle['inputs'] if row['role'] == role]
    expected = {'direction': 'input', 'role': role, 'ordinal': operands[0]['ordinal']} if len(operands) == 1 else None
    assert selected['affected'] == expected
