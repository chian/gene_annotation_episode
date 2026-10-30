"""Partial statistics remain usable without inventing generated provenance."""
import pytest

from gene_annotation_episode.native_blast_masking_contracts import (
    generated_statistics_binding, requested_job_from_native_blast_masking,
)
from gene_annotation_episode.state import Store
from test_native_blast_masking_host_returns import HostCase, selector
from test_native_blast_masking_invocation import job_for


def test_partial_statistics_preserve_actual_producer_binding_and_unknown_use(tmp_path, monkeypatch):
    """Synthetic nonzero exit wraps unchanged saved612 statistics, not a new run."""
    choice = selector(quantities=(), artifacts=[
        {'direction': 'output', 'role': 'statistics', 'ordinal': 0}])
    with Store(tmp_path / 'store') as store:
        case = HostCase(store, tmp_path, monkeypatch, program='windowmasker',
            mode='create_counts', selected=choice, failure=True)
        body = case.execute()['result']
        case.admit()
        assert body['status']['native_state'] == 'failed'
        assert body['failures'] and not body['status']['output_complete']
        job = job_for(tmp_path / 'later-mask', 'windowmasker')
        operand = next(row for row in job['operands'] if row['role'] == 'statistics')
        output = next(row for row in body['artifacts'] if row['role'] == 'statistics')
        operand.update({key: output[key] for key in ('artifact_ref', 'sha256', 'size_bytes')})
        job['statistics_binding'] = {
            **generated_statistics_binding(case.bundle), 'producer_source_ref': body['source_ref']}
        assignment = {'requested_job': requested_job_from_native_blast_masking(job)}
        assert case.bundle['statistics_binding'] is None
        with pytest.raises(ValueError, match='original_binding_required'):
            case.results.validate_job_inputs(case.root, assignment)
        job['statistics_binding'].update(kind='supplied', provenance='unknown',
            producer_source_ref=None, producer_attempt_id=None, reference_occurrence_ids=[])
        assignment = {'requested_job': requested_job_from_native_blast_masking(job)}
        assert case.results.validate_job_inputs(case.root, assignment) == [
            operand['artifact_ref']]
