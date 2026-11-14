"""Actual global Store admission and root native measurement type boundaries.

All durations/resources are engineered receipt data, not a native run or policy.
No shared-history exporter, provider, scientific score or execution is invoked.
"""
from copy import deepcopy
from dataclasses import asdict
import json

import pytest

from gene_annotation_episode.domain import ContractError, RECORD_SCHEMAS, canonical, parse_sequences, validate_schema
from gene_annotation_episode.run_statistics import ExecutionClass, RunStatistic
from gene_annotation_episode.state import Store


@pytest.fixture
def store_and_operands(tmp_path):
    # A real parsed source and its extracted products exercise Store admission
    # independently of problem intake and its unrelated API adapter imports.
    fasta = '>query\nACGT\n>reference\nAGGT\n'
    parsed = parse_sequences(fasta, format='fasta', molecule='dna')
    assert [(row.name, row.sequence) for row in parsed] == [('query', 'ACGT'), ('reference', 'AGGT')]
    assert all(not row.issues for row in parsed)
    with Store(tmp_path / 'store') as store:
        with store.transaction():
            fasta_ref = store.artifact(fasta, 'text/x-fasta')
            source_data = {'provider': 'engineering.fixture.fasta', 'accession': None,
                'uri': None, 'artifact_ref': fasta_ref, 'text_ref': fasta_ref,
                'request_ref': None, 'version': None, 'retrieved_at': None}
            validate_schema(source_data, RECORD_SCHEMAS['source'])
            source = store.put('source', source_data, origin='caller')
            subjects = []
            for row in parsed:
                # This reference identifies the actual FASTA record. Its
                # sequence is published below as the parser's extraction;
                # no indexed-member identity or input-root mapping is claimed.
                reference_data = {'reference_type': 'dna', 'source_ref': source['id'],
                    'accession': row.name, 'label': row.name, 'sequence_ref': None,
                    'molecule': 'dna', 'length': None, 'term_refs': [], 'context_refs': []}
                validate_schema(reference_data, RECORD_SCHEMAS['reference'])
                parent = store.put('reference', reference_data, origin='caller')
                sequence_ref = store.artifact(row.sequence, 'text/x-sequence')
                product_data = {'parent_refs': [parent['id']], 'molecule': 'dna',
                    'sequence_ref': sequence_ref, 'derivation': 'extraction',
                    'context_refs': [], 'footprint': []}
                validate_schema(product_data, RECORD_SCHEMAS['product'])
                product = store.put('product', product_data, origin='tool')
                assert store.get_artifact(product['sequence_ref']) == row.sequence.encode('ascii')
                assert store.get(product['parent_refs'][0])['source_ref'] == source['id']
                assert store.roots(product['id']) == []
                assert store.coverage(product['id']) == []
                assert store.subject_unit(product['id']) == 'nt'
                subjects.append(product['id'])
            assert store.get_artifact(source['artifact_ref']) == fasta.encode('utf-8')
        query, reference = subjects
        assert query != reference
        assert store.subject_length(query) == store.subject_length(reference) == 4
        yield store, [{'role': 'query', 'subject_ref': query},
                      {'role': 'reference', 'subject_ref': reference}]


def _measurement_record(*, phase='pairwise_sequence_alignment', query_residues=4,
                        outcome='unknown', duration_kind='unmeasured', elapsed_seconds=None):
    scope = ExecutionClass(phase=phase, backend='local', resource_id='engineering-receipt-fixture',
        implementation_sha256=None, parameters_sha256='a' * 64,
        memory_bytes=1024, scratch_bytes=2048, cpu_threads=None,
        query_residues=query_residues, reference_residues=4, reference_records=None,
        reference_state='available')
    statistic = RunStatistic(attempt_sha256='b' * 64, source_sha256='c' * 64,
        observed_at='2026-11-11T00:00:00+00:00', outcome=outcome,
        duration_kind=duration_kind, elapsed_seconds=elapsed_seconds, condition_ref=None)
    # This is the complete original serialized measurement shape, built using
    # actual canonical statistics classes before crossing Store's lazy import.
    return {'version': 'native_execution_measurement_v1',
            'execution_class': asdict(scope), 'statistic': asdict(statistic),
            'condition_capture': 'unavailable_before_submission'}


def _receipt(store, operands, measurement):
    artifact = store.artifact(canonical(measurement), 'application/json')
    receipt = {'representation': 'native_execution_receipt_v2', 'operation': 'align_pair',
               'measurement_artifact_ref': artifact, 'operands': deepcopy(operands)}
    validate_schema(receipt, RECORD_SCHEMAS['native_execution'])
    return receipt


def test_global_store_admits_original_artifact_and_reopens_unknown_measurement(store_and_operands):
    store, operands = store_and_operands
    measurement = _measurement_record()
    receipt = _receipt(store, operands, measurement)
    before = deepcopy(receipt)
    # Before the coordinated State import correction this actual boundary raises
    # ModuleNotFoundError for deleted gene_annotation_episode.episodic_workflow.root.execution_recording.
    # Preserve that baseline; no catch, skip, facade or replacement type hides it.
    admitted = store.put('native_execution', receipt, origin='tool')
    assert receipt == before
    assert store.put('native_execution', deepcopy(receipt), origin='tool')['id'] == admitted['id']
    assert len(store.list('native_execution')) == 1
    assert json.loads(store.get_artifact(admitted['measurement_artifact_ref'])) == measurement
    from gene_annotation_episode.episodic_workflow.root import native_measurement, native_timing_information
    assert native_measurement.ExecutionClass is ExecutionClass
    assert native_measurement.RunStatistic is RunStatistic
    assert native_timing_information.NativeMeasurement is native_measurement.NativeMeasurement
    with Store(store.path) as reopened:
        restored = native_timing_information.read_measurement(reopened, admitted['id'])
        assert type(restored) is native_measurement.NativeMeasurement
        assert type(restored.execution_class) is ExecutionClass
        assert type(restored.statistic) is RunStatistic
        assert restored.as_record() == measurement
        assert restored.statistic.elapsed_seconds is None
        assert restored.execution_class.cpu_threads is None
        assert restored.statistic.condition_ref is None


@pytest.mark.parametrize('change,code', [
    ('phase', 'native_execution_operation_phase_mismatch'),
    ('length', 'native_execution_operand_length_mismatch'),
    ('repeated_role', 'native_execution_operand_role_repeated'),
    ('origin', 'native_execution_requires_native_tool_origin'),
])
def test_store_rejects_real_receipt_mismatches_without_publishing_record(store_and_operands, change, code):
    store, operands = store_and_operands
    measurement = _measurement_record(
        phase='protein_homology_search' if change == 'phase' else 'pairwise_sequence_alignment',
        query_residues=5 if change == 'length' else 4)
    receipt = _receipt(store, operands, measurement)
    if change == 'repeated_role':
        # Distinct actual subjects preserve JSON uniqueItems while violating the
        # separate native operand-role identity rule.
        receipt['operands'][1]['role'] = 'query'
    with pytest.raises(ContractError, match=code) as caught:
        store.put('native_execution', receipt, origin='caller' if change == 'origin' else 'tool')
    assert type(caught.value) is ContractError
    assert store.list('native_execution') == []


@pytest.mark.parametrize('outcome,duration_kind,seconds', [
    ('unknown', 'unmeasured', None), ('failed', 'lower_bound', 1.25),
    ('succeeded', 'complete', 2.5),
])
def test_root_timing_fields_preserve_original_units_and_unknowns(store_and_operands, outcome, duration_kind, seconds):
    from gene_annotation_episode.episodic_workflow.root import native_measurement as measurement
    from gene_annotation_episode.episodic_workflow.root import native_timing_information as timing
    store, operands = store_and_operands
    record = _measurement_record(outcome=outcome, duration_kind=duration_kind, elapsed_seconds=seconds)
    measured = measurement.NativeMeasurement.from_record(record)
    receipt_ref = timing.record_native_measurement(store, measured, operation='align_pair', operands=operands)
    fields = timing.measurement_fields(receipt_ref, timing.read_measurement(store, receipt_ref), operation='align_pair')
    validate_schema(fields, timing.MEASUREMENT_SCHEMA)
    assert fields == {'receipt_ref': receipt_ref, 'operation': 'align_pair',
        'phase': 'pairwise_sequence_alignment', 'outcome': outcome, 'duration_kind': duration_kind,
        'duration_measure': 'protected_service_wall_seconds', 'elapsed_seconds': seconds,
        'cpu_threads': None, 'memory_limit_bytes': 1024, 'scratch_limit_bytes': 2048,
        'query_residues': 4, 'reference_residues': 4}
    timing.validate_native_measurements(store, fields, schema=timing.MEASUREMENT_SCHEMA)


def test_changed_timing_fact_uses_exact_root_report_boundary_error(store_and_operands):
    from gene_annotation_episode.episodic_workflow.root import native_measurement as measurement
    from gene_annotation_episode.episodic_workflow.root import native_timing_information as timing
    from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError
    store, operands = store_and_operands
    measured = measurement.NativeMeasurement.from_record(_measurement_record())
    receipt_ref = timing.record_native_measurement(store, measured, operation='align_pair', operands=operands)
    fields = timing.measurement_fields(receipt_ref, measured, operation='align_pair')
    fields['elapsed_seconds'] = 0.0
    assert timing.ReportBoundaryError is ReportBoundaryError
    with pytest.raises(ReportBoundaryError) as caught:
        timing.validate_native_measurements(store, fields, schema=timing.MEASUREMENT_SCHEMA)
    assert caught.value.diagnostic['code'] == 'native_measurement_fact_mismatch'
    assert timing.read_measurement(store, receipt_ref).statistic.elapsed_seconds is None


def test_serialized_mapping_is_not_a_typed_native_publisher_input(store_and_operands):
    from gene_annotation_episode.episodic_workflow.root import native_timing_information as timing
    store, operands = store_and_operands
    before = store.db.execute('SELECT count(*) FROM artifacts').fetchone()[0]
    with pytest.raises(TypeError, match='typed_native_measurement_required'):
        timing.record_native_measurement(store, _measurement_record(), operation='align_pair', operands=operands)
    assert store.db.execute('SELECT count(*) FROM artifacts').fetchone()[0] == before
    assert store.list('native_execution') == []


@pytest.mark.parametrize('foreign_part', ['execution_class', 'statistic'])
def test_real_foreign_axis_statistics_types_are_not_root_measurement_types(foreign_part):
    from gene_annotation_episode.episodic_workflow.root import native_measurement as measurement
    # Actual independently owned classes, solely negative type-boundary inputs.
    # No axis runtime, execution exporter, fabricated class or alias is imported.
    from gene_annotation_episode.episodic_workflow.root.a104.run_statistics import (
        ExecutionClass as ForeignExecutionClass, RunStatistic as ForeignRunStatistic,
    )
    record = _measurement_record()
    scope = ExecutionClass(**record['execution_class'])
    statistic = RunStatistic(**record['statistic'])
    if foreign_part == 'execution_class':
        scope = ForeignExecutionClass(**record['execution_class'])
        assert type(scope) is not ExecutionClass
    else:
        statistic = ForeignRunStatistic(**record['statistic'])
        assert type(statistic) is not RunStatistic
    with pytest.raises(TypeError, match='typed_native_execution_measurement_required'):
        measurement.NativeMeasurement(scope, statistic, record['condition_capture'])


def test_unavailable_condition_cannot_acquire_an_invented_condition_reference(store_and_operands):
    store, operands = store_and_operands
    measurement = _measurement_record()
    measurement['statistic']['condition_ref'] = 'execution_condition_' + 'd' * 64
    receipt = _receipt(store, operands, measurement)
    with pytest.raises(ValueError, match='unavailable_condition_must_remain_unknown'):
        store.put('native_execution', receipt, origin='tool')
    assert store.list('native_execution') == []
