"""Pure masking checks, including saved authentic native bytes from oracle 612.

All constructed byte strings below are labelled synthetic by their test context.
No native executable, acquisition, Store or model is used by these tests.
"""
import builtins
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch
import jsonschema
import pytest
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_contracts import PARAMETERS, sequence_masking_operation_schema, validate_sequence_masking_record
from gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_inputs import parse_masking_input_fasta, preflight_masking_input_fasta, parse_sequence_masking_output, populate_sequence_masking_sheet
from gene_annotation_episode.episodic_workflow.root.a104.library.sequence_masking_calculations import calculate_sequence_masking_components
FIXTURES = Path(__import__('gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_contracts', fromlist=['__file__']).__file__).resolve().parent.parent / 'a101/tests/fixtures/masking_native'

def occurrence(content, oid='input', role='sequences', completeness='complete'):
    return {'occurrence_id': oid, 'direction': 'output' if role == 'mask' else 'input', 'role': role, 'ordinal': 0, 'artifact_ref': 'retained:' + oid, 'sha256': hashlib.sha256(content).hexdigest(), 'size_bytes': len(content), 'completeness': completeness}

def operation(program='dustmasker', format='interval', style=None, mode='mask', parse_seqids=False):
    return {'version': 'sequence_masking_operation_v1', 'program': program, 'mode': mode, 'engine_version': None, 'input_format': 'fasta', 'output_format': format, 'masking_style': style or ('not_applicable' if mode == 'create_counts' else 'interval' if format == 'interval' else 'soft'), 'parse_seqids': parse_seqids, 'requested_parameters': {k: None for k in PARAMETERS[program, mode]}}

def custody(records, *, complete=True, returncode=0, producer='authenticated_native', explicit=False):
    basis = 'native_fasta_iteration' if producer == 'authenticated_native' else 'caller_declared'
    return {'producer_kind': producer, 'sequence_order': [r['record_key'] for r in records], 'order_basis': basis, 'output_complete': complete, 'native_returncode': returncode, 'record_bindings': [{'output_record_ordinal': i, 'input_record_key': r['record_key'], 'basis': basis} for i, r in enumerate(records)] if explicit else []}

def build(input_bytes, output_bytes, *, op=None, records=None, owner=None, statistics=None):
    op = operation() if op is None else op
    if records is None:
        records = parse_masking_input_fasta(input_bytes, occurrence=occurrence(input_bytes), molecule='protein' if op['program'] == 'segmasker' else 'dna')['records']
    owner = custody(records) if owner is None else owner
    out = occurrence(output_bytes, 'output', 'mask', 'complete' if owner['output_complete'] else 'partial')
    parsed = parse_sequence_masking_output(output_bytes, format=op['output_format'], occurrence=out, input_records=records, operation=op, custody=owner)
    outcome = {'returncode': owner['native_returncode'], 'state': 'succeeded' if owner['native_returncode'] == 0 else 'failed' if owner['native_returncode'] is not None else 'unknown', 'output_complete': owner['output_complete']}
    sheet = populate_sequence_masking_sheet(operation=op, inputs=records, parsed_output=parsed, statistics=statistics, native_outcome=outcome)
    return (sheet, calculate_sequence_masking_components(sheet))

def retained(pin):
    content = (FIXTURES / pin['path']).read_bytes()
    assert len(content) == pin['size_bytes']
    assert hashlib.sha256(content).hexdigest() == pin['sha256']
    return content


def test_synthetic_overlap_duplicate_intervals_reuse_exact_shared_helpers():
    from gene_annotation_episode.episodic_workflow.root.a104.library import sequence_masking_ratios as genomic_overlap_calculations
    from gene_annotation_episode.episodic_workflow.root.a104 import hmmer_search_grader
    with patch.object(hmmer_search_grader, '_union', wraps=hmmer_search_grader._union) as union, patch.object(genomic_overlap_calculations, '_ratio', wraps=genomic_overlap_calculations._ratio) as ratio:
        sheet, result = build(b'>one\nACGTACGTACGT\n', b'>generated\n0 - 3\n2 - 5\n8 - 8\n0 - 3\n')
    row = result['records'][0]
    assert union.call_count == ratio.call_count == 1
    assert len(sheet['parsed_output']['records'][0]['native_intervals']) == 4
    assert row['native_interval_count']['value'] == 4
    assert row['merged_intervals_half_open'] == [[0, 6], [8, 9]]
    assert row['merged_interval_count']['value'] == 2
    assert row['masked_positions']['value'] == 7
    assert row['unmasked_positions']['value'] == 5
    assert row['masked_fraction']['value'] == 7 / 12

def test_synthetic_no_mask_absent_partial_and_native_failed_are_distinct():
    raw = b'>a\nACGT\n>b\nACGT\n'
    records = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule='dna')['records']
    _, complete = build(raw, b'>a\n>b\n')
    assert [r['masked_positions']['value'] for r in complete['records']] == [0, 0]
    _, absent = build(raw, b'')
    assert all((r['masked_positions']['value'] is None for r in absent['records']))
    owner = custody(records, complete=False, returncode=3, explicit=True)
    sheet, partial = build(raw, b'>a\n0 - 1\n>b\n', owner=owner)
    assert partial['records'][0]['masked_positions']['value'] == 2
    assert partial['records'][1]['masked_positions']['value'] is None
    assert partial['records'][1]['masked_fraction']['missing_reason'] == 'output_record_incomplete'
    assert any((f['code'] == 'native_failed' for f in sheet['failures']))
    unbound = custody(records, complete=False, returncode=3)
    sheet, unknown = build(raw, b'>a\n0 - 1\n>b\n', owner=unbound)
    assert len(sheet['parsed_output']['unassigned_records']) == 2
    assert sheet['parsed_output']['unassigned_records'][0]['intervals_half_open'] == [[0, 2]]
    assert all((r['masked_positions']['value'] is None for r in unknown['records']))

def test_synthetic_supplied_outputs_require_explicit_record_bindings():
    raw = b'>a\nACGT\n>b\nACGT\n'
    records = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule='dna')['records']
    sheet, _ = build(raw, b'>a\n0 - 1\n>b\n', owner=custody(records, producer='supplied_artifact'))
    assert not sheet['parsed_output']['records']
    owner = custody(records, producer='supplied_artifact', explicit=True)
    sheet, result = build(raw, b'>different\n0 - 1\n>other\n', owner=owner)
    assert result['records'][0]['masked_positions']['value'] == 2
    assert sheet['parsed_output']['records'][0]['association'] == 'caller_declared'

@pytest.mark.parametrize('invalid,reason', [(b'AC-GT', 'gapped_input_unsupported'), (b'ACUGT', 'unsupported_sequence_symbol'), (b'AC?GT', 'unsupported_sequence_symbol'), (b'AC\xffGT', 'input_not_utf8')])
def test_synthetic_invalid_substrate_has_no_denominator(invalid, reason):
    raw = b'>one\n' + invalid + b'\n'
    records = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule='dna')['records']
    assert records[0]['length'] is None
    assert records[0]['original_sequence'].encode('utf-8', errors='surrogateescape') == invalid
    sheet, result = build(raw, b'>one\n0 - 1\n', records=records, owner=custody(records, explicit=True))
    assert any((f['code'] == reason for f in sheet['failures']))
    row = result['records'][0]
    assert row['input_length']['missing_reason'] == reason
    assert row['masked_fraction']['denominator'] is None
    assert row['masked_positions']['value'] is None

def test_synthetic_empty_record_and_empty_file_are_different():
    raw = b'>empty\n'
    parsed = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule='dna')
    assert parsed['records'][0]['length'] == 0
    assert parsed['records'][0]['failures'][0]['code'] == 'empty_sequence'
    _, result = build(raw, b'>empty\n', records=parsed['records'], owner=custody(parsed['records'], explicit=True))
    assert result['records'][0]['masked_fraction'] == {'numerator': 0, 'denominator': 0, 'value': None, 'missing_reason': 'zero_denominator'}
    empty = parse_masking_input_fasta(b'', occurrence=occurrence(b''), molecule='dna')
    assert empty['records'] == []
    assert empty['failures'][0]['code'] == 'empty_input'

@pytest.mark.parametrize('row,reason', [(b'bad row', 'malformed_interval_row'), (b'8 - 9', 'interval_out_of_bounds'), (b'3 - 1', 'reversed_interval'), (b'-1 - 2', 'malformed_interval_row')])
def test_synthetic_malformed_interval_preserves_valid_rows_and_other_records(row, reason):
    sheet, result = build(b'>a\nACGT\n>b\nACGT\n', b'>a\n0 - 1\n' + row + b'\n>b\n2 - 3\n')
    assert sheet['parsed_output']['records'][0]['intervals_half_open'] == [[0, 2]]
    assert any((f['code'] == reason for f in sheet['failures']))
    assert result['records'][0]['masked_positions']['value'] is None
    assert result['records'][1]['masked_positions']['value'] == 2

@pytest.mark.parametrize('output,reason', [(b'acg', 'output_sequence_length_mismatch'), (b'acga', 'output_sequence_symbol_change'), (b'acg?', 'unsupported_output_symbol')])
def test_synthetic_incompatible_soft_output_never_implies_mask(output, reason):
    sheet, result = build(b'>a\nACGT\n', b'>a\n' + output + b'\n', op=operation(format='fasta'))
    assert reason in {f['code'] for f in sheet['failures']}
    assert result['records'][0]['masked_fraction']['value'] is None
    assert result['records'][0]['changed_positions']['value'] is None

def test_synthetic_original_bytes_ordinals_and_mixed_occurrences_survive():
    a = b'>dup caf\xc3\xa9\r\n aC gT \r\n>dup\r\nA-\r\n>dup\r\nTGCA\r\n'
    b = b'>dup\nCCCC\n'
    pa = parse_masking_input_fasta(a, occurrence=occurrence(a, 'a'), molecule='dna')
    pb = parse_masking_input_fasta(b, occurrence=occurrence(b, 'b'), molecule='dna')
    assert [r['record_ordinal'] for r in pa['records']] == [0, 1, 2]
    assert [r['byte_offset'] for r in pa['records']] == [0, a.index(b'>dup', 1), a.rindex(b'>dup')]
    assert pa['records'][0]['original_sequence'] == 'aCgT'
    records = [pa['records'][2], pb['records'][0]]
    sheet, result = build(b'', b'>dup\n1 - 2\n>dup\n', records=records)
    assert [r['record_key'] for r in result['records']] == ['a#/records/2', 'b#/records/0']
    assert result['records'][0]['masked_fraction']['value'] == 0.5
    assert sheet['inputs'][0]['byte_offset'] == a.rindex(b'>dup')

def test_synthetic_saved_only_recalculation_denies_all_io_and_process_work():
    sheet, expected = build(b'>one\nACGTACGTACGT\n', b'>one\n0 - 3\n2 - 5\n8 - 8\n')
    saved = json.loads(json.dumps(sheet))

    def denied(*args, **kwargs):
        raise AssertionError('saved calculation attempted I/O or process work')
    with patch.object(builtins, 'open', denied), patch.object(io, 'open', denied), patch.object(socket, 'socket', denied), patch.object(subprocess, 'Popen', denied):
        actual = calculate_sequence_masking_components(saved)
    assert actual == expected
    assert saved == sheet

@pytest.mark.parametrize('program,mode', [('dustmasker', 'mask'), ('segmasker', 'mask'), ('windowmasker', 'mask'), ('windowmasker', 'create_counts')])
def test_operation_schema_and_validation_have_one_parameter_authority(program, mode):
    op = operation(program, 'ascii_statistics' if mode == 'create_counts' else 'interval', mode=mode)
    schema = sequence_masking_operation_schema(program=program, mode=mode)
    jsonschema.validate(op, schema)
    assert validate_sequence_masking_record('Operation', op) == op
    assert set(schema['properties']['requested_parameters']['required']) == set(op['requested_parameters'])
    bad = deepcopy(op)
    bad['requested_parameters']['extra'] = None
    with pytest.raises(ContractError, match='sequence_masking_object_fields'):
        validate_sequence_masking_record('Operation', bad)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)
    bad = deepcopy(op)
    bad['requested_parameters'].pop(next(iter(bad['requested_parameters'])))
    with pytest.raises(ContractError, match='sequence_masking_object_fields'):
        validate_sequence_masking_record('Operation', bad)
    schema['properties']['requested_parameters']['properties'].clear()
    assert sequence_masking_operation_schema(program=program, mode=mode)['properties']['requested_parameters']['properties']

def test_contract_numerical_types_bounds_and_unknown_versions():
    op = operation('windowmasker', 'ascii_statistics', mode='create_counts')
    op['requested_parameters']['genome_size'] = 2 ** 63 - 1
    assert validate_sequence_masking_record('Operation', op)['requested_parameters']['genome_size'] == 2 ** 63 - 1
    for value in (True, 0, 2 ** 63, 1.5):
        op['requested_parameters']['genome_size'] = value
        with pytest.raises(ContractError):
            validate_sequence_masking_record('Operation', op)
    for value in (float('nan'), float('inf'), -1, True):
        seg = operation('segmasker')
        seg['requested_parameters']['locut'] = value
        with pytest.raises(ContractError):
            validate_sequence_masking_record('Operation', seg)
    seg = operation('segmasker')
    seg['requested_parameters'].update(locut=4.0, hicut=2.0)
    assert validate_sequence_masking_record('Operation', seg)['engine_version'] is None
    for func in (lambda: sequence_masking_operation_schema(program='dustmasker', mode='create_counts'), lambda: validate_sequence_masking_record('Other', {})):
        with pytest.raises(ContractError):
            func()

def test_contract_rejects_wrong_associations_bytes_and_format_style():
    raw = b'>a\nACGT\n'
    with pytest.raises(ContractError, match='content_occurrence_mismatch'):
        parse_masking_input_fasta(raw, occurrence=occurrence(b'>b\nACGT\n'), molecule='dna')
    op = operation('segmasker', 'fasta', 'hard')
    with pytest.raises(ContractError, match='mode_format'):
        validate_sequence_masking_record('Operation', op)
    sheet, _ = build(raw, b'>a\n0 - 1\n')
    bad = deepcopy(sheet)
    bad['parsed_output']['records'][0]['input_record_key'] = 'wrong#/records/0'
    with pytest.raises(ContractError):
        calculate_sequence_masking_components(bad)
    copied = validate_sequence_masking_record('SequenceMaskingSheet', sheet)
    copied['inputs'][0]['checks'].clear()
    assert sheet['inputs'][0]['checks']


@pytest.mark.parametrize('raw,molecule', [(b'>duplicate\naC gT\n>duplicate\nTGCA\n', 'dna'), (b'', 'dna'), (b'>empty\n', 'dna'), (b'>bad\nA-C\n', 'dna'), (b'>bad\nAUC\n', 'dna'), (b'not fasta\n', 'dna'), (b'>bad\nAC\xffG\n>good\nTGCA\n', 'dna'), (b'>protein\nacdefghiklmnpqrstvwy\n', 'protein')])
def test_preflight_and_captured_parser_share_exact_input_validation(raw, molecule):
    preflight = preflight_masking_input_fasta(raw, molecule=molecule)
    parsed = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule=molecule)
    ordinals = {r['record_key']: r['record_ordinal'] for r in parsed['records']}
    assert preflight == {'version': 'sequence_masking_preflight_v1', 'valid': bool(parsed['records']) and (not parsed['failures']), 'record_count': len(parsed['records']), 'failures': [{'code': f['code'], 'record_ordinal': ordinals.get(f['record_key']), 'line_number': f['line_number']} for f in parsed['failures']]}
    assert not {'artifact_ref', 'occurrence_id', 'record_key'} & set(preflight)


@pytest.mark.parametrize('content,molecule', [('not bytes', 'dna'), (True, 'dna'), (b'>a\nACGT\n', []), (b'>a\nACGT\n', 'rna')])
def test_preflight_malformed_caller_arguments_raise_stable_contract_error(content, molecule):
    with pytest.raises(ContractError, match='sequence_masking_'):
        preflight_masking_input_fasta(content, molecule=molecule)

@pytest.mark.parametrize('mode', ['interval', 'soft', 'hard'])
def test_saved_sheet_rejects_forged_exact_mask_assumptions(mode):
    op = operation(format='interval' if mode == 'interval' else 'fasta', style='hard' if mode == 'hard' else None)
    out = b'>a\n0 - 1\n' if mode == 'interval' else b'>a\nacGT\n' if mode == 'soft' else b'>a\nNNGT\n'
    sheet, _ = build(b'>a\nACGT\n', out, op=op)
    bad = deepcopy(sheet)
    bad['parsed_output']['records'][0]['intervals_half_open'] = [[0, 4]]
    with pytest.raises(ContractError, match='relationship'):
        calculate_sequence_masking_components(bad)
    if mode != 'interval':
        bad = deepcopy(sheet)
        bad['parsed_output']['records'][0]['output_sequence'] = 'TTGT'
        with pytest.raises(ContractError, match='relationship'):
            calculate_sequence_masking_components(bad)

def test_saved_sheet_cannot_erase_hard_n_ambiguity_or_input_failures():
    sheet, _ = build(b'>a\nANNT\n', b'>a\nNNNN\n', op=operation(format='fasta', style='hard'))
    sheet['parsed_output']['records'][0]['measurement'] = 'exact_mask'
    with pytest.raises(ContractError, match='native_hard_mask_ambiguity'):
        calculate_sequence_masking_components(sheet)
    raw = b'>a\nA-CG\n'
    records = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule='dna')['records']
    sheet, _ = build(raw, b'>a\n0 - 1\n', records=records, owner=custody(records, explicit=True))
    sheet['failures'] = []
    with pytest.raises(ContractError, match='lost_input_diagnostics'):
        calculate_sequence_masking_components(sheet)

def test_incompatible_molecule_never_supplies_mask_denominator():
    raw = b'>protein\nACGT\n'
    records = parse_masking_input_fasta(raw, occurrence=occurrence(raw), molecule='protein')['records']
    _, result = build(raw, b'>protein\n0 - 1\n', records=records)
    row = result['records'][0]
    assert row['unit'] == 'nt'
    assert row['input_length']['value'] is None
    assert row['masked_fraction']['missing_reason'] == 'incompatible_input_molecule'

def test_partial_input_and_unassociated_soft_output_keep_original_data():
    raw = b'>closed\nACGT\n>last\nAC\n'
    parsed = parse_masking_input_fasta(raw, occurrence=occurrence(raw, completeness='partial'), molecule='dna')
    assert [r['length'] for r in parsed['records']] == [4, None]
    valid = b'>a\nACGT\n'
    records = parse_masking_input_fasta(valid, occurrence=occurrence(valid), molecule='dna')['records']
    sheet, _ = build(valid, b'>unbound\naCGt\n', op=operation(format='fasta'), records=records, owner=custody(records, producer='supplied_artifact'))
    assert sheet['parsed_output']['unassigned_records'][0]['intervals_half_open'] == [[0, 1], [3, 4]]

@pytest.mark.parametrize('mode', ['native_result', 'saved_recalculation'])
def test_actual_A104_worker_saved_stage_and_immutable_replay(tmp_path, monkeypatch, mode):
    from gene_annotation_episode.episodic_workflow.root.a104.library import native_blast_masking_result_worker as worker
    from gene_annotation_episode.episodic_workflow.root.a104.library import native_blast_masking_result_publication as publication
    from gene_annotation_episode.episodic_workflow.root.a104.library import sequence_masking_calculations as calculator
    from gene_annotation_episode.episodic_workflow.root.a104 import sequence_masking_contracts as contracts
    from gene_annotation_episode.episodic_workflow.root.a104 import native_hmmer_preparation_result_worker as original_io
    from gene_annotation_episode.episodic_workflow.root.a104.local_jobs import LocalJobPolicy
    assert worker.ContractError is publication.ContractError is contracts.ContractError is ContractError
    assert publication.LocalJobPolicy is LocalJobPolicy
    assert worker._read_bytes is original_io._read_bytes

    def forbidden(*args, **kwargs):
        raise AssertionError('Pure dependency validation cannot submit commands, native work or provider calls')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(publication, 'run_local_job', forbidden)
    sheet, calculated = build(b'>one\nACGTACGTACGT\n', b'>generated\n0 - 3\n2 - 5\n8 - 8\n')

    def saved(name, value):
        raw = json.dumps(value, sort_keys=True).encode()
        path = tmp_path / (name + '.json')
        path.write_bytes(raw)
        return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}
    directory = tmp_path / 'worker'
    directory.mkdir()
    source = 'execution_result_' + 'a' * 64
    selector = {'version': 'native_blast_masking_result_selector_v1', 'mode': mode, 'records': {'mode': 'all'}, 'quantities': ['masked_positions', 'masked_fraction'], 'statistics_fields': [], 'statistics_unit_codes': [], 'include_checks': False, 'artifacts': [], 'saved_data': [], 'saved_sheet_ref': 'artifact_' + 'b' * 64 if mode == 'saved_recalculation' else None}
    plan = {'version': worker.PLAN_VERSION, 'task': 'project_saved', 'directory': str(directory), 'source_ref': source, 'operation': sheet['operation'], 'native_outcome': sheet['native_outcome'], 'occurrences': [sheet['inputs'][0]['occurrence'], sheet['parsed_output']['occurrence']], 'selector': selector, 'saved_data': [], 'failures': [], 'files': {'sheet': saved('sheet', sheet), 'calculations': saved('calculations', calculated), 'statistics': None}}
    manifest = worker.run(plan)
    assert manifest['completed'] is True and (not manifest['failures'])
    projection = json.loads((directory / 'projection.json').read_text())
    by_quantity = {row['quantity']: row['value'] for row in projection['quantities']}
    assert by_quantity['masked_positions']['value'] == 7
    assert by_quantity['masked_fraction']['value'] == 7 / 12
    monkeypatch.setattr(worker, '_project_saved', forbidden)
    monkeypatch.setattr(calculator, 'calculate_sequence_masking_components', forbidden)
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    assert worker.run(plan) == manifest
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == before
    (directory / 'projection.json').write_text('{}')
    with pytest.raises(ContractError):
        worker.run(plan)

def test_A104_worker_lazy_parse_imports_and_exception_identity(tmp_path, monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a104.library import native_blast_masking_result_worker as worker
    from gene_annotation_episode.episodic_workflow.root.a104.library import native_blast_masking_result_publication as publication
    from gene_annotation_episode.episodic_workflow.root.a104 import blast_maskinfo_inputs
    assert blast_maskinfo_inputs.ContractError is worker.ContractError is publication.ContractError is ContractError

    def forbidden(*args, **kwargs):
        raise AssertionError('Pure dependency validation cannot submit a command')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(publication, 'run_local_job', forbidden)
    with pytest.raises(ContractError):
        worker._parse_calculate({'bundle': {}, 'original_plan': {}}, tmp_path, {'outputs': {}, 'failures': []})
