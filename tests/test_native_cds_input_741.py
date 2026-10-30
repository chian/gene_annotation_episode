"""One explicit bounded acquisition and authentic selected CDS comparison.

This never chooses a candidate, retries a request, or substitutes a provider.
Native source annotations remain claims about the retrieved source sequence.
"""
from copy import deepcopy
from dataclasses import asdict
import builtins
import io
import json
import os
from pathlib import Path
import socket
import urllib.request

from Bio import SeqIO
import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, parse_genbank
from gene_annotation_episode import coding_sequence_native
from gene_annotation_episode.coding_sequence_support import (
    plan_coding_sequence_extractions, read_coding_sequence_results,
)
from gene_annotation_episode.sequence_extraction_grader import calculate_extraction_scores
from gene_annotation_episode.sequence_mapping import VERSION


pytestmark = pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ,
                                reason='requires bounded529 retained runtime')
LIMIT = 4194304


def save(directory, name, value):
    (directory / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def test_one_selected_current_nucleotide_request_and_authentic_cds(monkeypatch):
    directory = Path(os.environ['HMMER529_ATTEMPT']) / 'native-cds741'
    directory.mkdir(exist_ok=False)
    selected = {'accession': 'AJ320226.1', 'database': 'nuccore',
        'retmode': 'text', 'rettype': 'gbwithparts', 'max_bytes': LIMIT,
        'timeout_seconds': 90, 'selected_request_attempts': 1,
        'record_source_ordinal': 0, 'feature_source_ordinal': 2,
        'molecule_model': 'dna', 'provider_fallback': False, 'automatic_retry': False}
    save(directory, 'selected.json', selected)
    verification = {'capture': 'not_observed', 'snapshot_retained': False,
        'native_cds_validated': False, 'native_view_calls': 0,
        'independent_native_oracle_calls': 0, 'saved_recalculation_verified': False,
        'failure': None, 'summary': None}
    snapshot = None
    try:
        try:
            snapshot = PublicClients(timeout=90).ncbi_sequence('AJ320226.1', max_bytes=LIMIT)
        except AcquisitionError as error:
            snapshot = error.snapshot
            verification['capture'] = 'failed'
            verification['failure'] = {'code': error.code, 'phase': error.phase,
                'diagnostic': error.diagnostic, 'exception_type': type(error).__name__}
        if snapshot is not None:
            (directory / 'AJ320226.1.entity').write_bytes(snapshot.content)
            metadata = asdict(snapshot)
            del metadata['content']
            metadata.update(sha256=snapshot.sha256, size_bytes=len(snapshot.content))
            save(directory, 'AJ320226.1.json', metadata)
            verification['snapshot_retained'] = True
        save(directory, 'verification.json', verification)
        assert verification['failure'] is None and snapshot is not None, 'selected_nucleotide_capture_unavailable'
        assert snapshot.transport['status'] == 200
        assert snapshot.transport['body_complete'] is True
        assert len(snapshot.content) <= LIMIT
        assert snapshot.request == {'db': 'nuccore', 'id': 'AJ320226.1', 'rettype': 'gbwithparts',
            'retmode': 'text', 'tool': 'gene-annotation-episode'}
        verification['capture'] = 'complete_http200'
        records = parse_genbank(snapshot.content)
        save(directory, 'parsed.json', records)
        record = next(row for row in records if row['source_record_index'] == 0)
        assert record['accession'] == 'AJ320226.1', 'selected_native_accession_conflict'
        feature = next(row for row in record['features'] if row['source_feature_index'] == 2)
        assert feature['kind'] == 'CDS', 'selected_native_feature_not_cds'
        source_ref = 'captured_nucleotide:' + snapshot.sha256
        subject_ref = 'supplied-ncbi-entity:' + snapshot.sha256 + '#record0'
        length = len(record['sequence'])
        mapping = {'version': VERSION, 'units_per_symbol': 1, 'symbol_length': length,
            'path': [{'subject_ref': subject_ref, 'start': 0, 'end': length,
                      'unit': 'nt', 'strand': '+'}]}
        chosen = {'record_ordinal': 0, 'feature_ordinal': 2,
                  'subject_ref': subject_ref, 'parent_mapping': mapping}
        plan = plan_coding_sequence_extractions(records, selection=[chosen],
            source_ref=source_ref, molecule_model='dna')
        save(directory, 'plan.json', plan)
        native_view = coding_sequence_native.view_sequence
        def counted_view(*args, **kwargs):
            verification['native_view_calls'] += 1
            return native_view(*args, **kwargs)
        monkeypatch.setattr(coding_sequence_native, 'view_sequence', counted_view)
        produced = coding_sequence_native.run_coding_sequence_plan(plan)
        save(directory, 'native.json', produced)
        result = read_coding_sequence_results(plan, extracted=produced)
        save(directory, 'result.json', result)
        native_records = list(SeqIO.parse(io.StringIO(snapshot.content.decode('utf-8')), 'genbank'))
        assert native_records[0].features[2].type == 'CDS'
        verification['independent_native_oracle_calls'] += 1
        expected = str(native_records[0].features[2].extract(native_records[0].seq))
        row = result['rows'][0]
        assert row['sequence'] == expected
        assert verification['native_view_calls'] == 1
        assert row['source_feature'] == feature
        assert row['record_metadata']['accession'] == 'AJ320226.1'
        grading = row['grading']
        assert grading['sheet']['schema'] == 'sequence_extraction_sheet_v1'
        assert grading['scores']['schema'] == 'sequence_extraction_scores_v1'
        assert grading['scores']['summary']['matching_symbol_count'] == len(expected)
        assert grading['scores']['summary']['mismatching_symbol_count'] == 0
        assert grading['scores']['summary']['output_symbol_count'] == len(expected)
        assert grading['scores']['status'] == 'complete'
        verification['native_cds_validated'] = True
        verification['summary'] = deepcopy(grading['scores']['summary'])
        verification['qualification'] = {'source_annotations': 'external_source_assertions_not_current_target_annotation',
            'extraction_status': row['extraction_status'], 'geometry_basis': row['geometry_basis'],
            'issue_codes': row['issue_codes'], 'scientific_function_confidence': None,
            'host_resource_episode_integration_verified': False}
        saved = json.loads((directory / 'result.json').read_text())['rows'][0]['grading']
        saved_sheet, saved_scores = saved['sheet'], saved['scores']
        original_import = builtins.__import__
        def restricted_import(name, *args, **kwargs):
            if name == 'Bio' or name.startswith('Bio.') or name.endswith('coding_sequence_native'):
                raise AssertionError('native dependency in saved recalculation')
            return original_import(name, *args, **kwargs)
        def forbidden(*args, **kwargs):
            raise AssertionError('IO or native execution in saved recalculation')
        with monkeypatch.context() as saved_only:
            saved_only.setattr(builtins, '__import__', restricted_import)
            saved_only.setattr(builtins, 'open', forbidden)
            saved_only.setattr(socket, 'socket', forbidden)
            saved_only.setattr(urllib.request, 'urlopen', forbidden)
            saved_only.setattr(coding_sequence_native, 'view_sequence', forbidden)
            assert calculate_extraction_scores(saved_sheet) == saved_scores
        verification['saved_recalculation_verified'] = True
    except Exception as error:
        if verification['failure'] is None:
            verification['failure'] = {'code': 'native_cds_input_validation_failed',
                'exception_type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        save(directory, 'verification.json', verification)
