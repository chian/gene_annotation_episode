"""Installed own-axis types and pure returned-failure qualification; no native work."""
from copy import deepcopy
import importlib
import socket
import subprocess
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a104 import a104_execution_bindings as installer
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a104.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.a104.state import Store

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a104'
READERS = (('library.native_hmmer_result_records', 'NativeHMMERResultRecords'), ('library.native_blast_masking_result_records', 'NativeBLASTMaskingResultRecords'), ('library.native_blast_masking_returns', 'NativeBLASTMaskingReturns'), ('library.native_blast_utility_result_records', 'NativeBLASTUtilityResultRecords'), ('library.native_blast_utility_returns', 'NativeBLASTUtilityReturns'), ('library.native_blast_standard_database_result_records', 'StandardBLASTDatabaseResultRecords'), ('library.native_blast_standard_database_returns', 'StandardBLASTDatabaseReturns'), ('library.native_blast_database_result_records', 'NativeBLASTDatabaseResultRecords'), ('library.native_blast_database_returns', 'NativeBLASTDatabaseReturns'), ('library.native_blast_result_records', 'NativeBLASTResultRecords'), ('library.native_blast_returns', 'NativeBLASTReturns'), ('library.native_hmmer_preparation_result_records', 'NativeHmmerPreparationResultRecords'), ('native_hmmer_preparation_returns', 'NativeHmmerPreparationReturns'))
FLAGS = ('native_blast_standard_database', 'native_blast_database', 'native_blast', 'native_hmmer_preparation')


@pytest.fixture(autouse=True)
def forbid_external_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('installed reader test attempted native or network execution')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.mark.parametrize('module_name,symbol', READERS)
def test_installed_class_keeps_own_axis_types(module_name, symbol):
    module = importlib.import_module(PACKAGE + '.' + module_name)
    cls = getattr(module, symbol)
    assert cls.__module__ == PACKAGE + '.' + module_name
    if hasattr(module, 'EpisodeReturnRecords'):
        assert module.EpisodeReturnRecords is EpisodeReturnRecords
    if hasattr(module, 'ContractError'):
        assert module.ContractError is ContractError
    if symbol.endswith('Returns'):
        assert issubclass(cls, EpisodeReturnRecords)


@pytest.mark.parametrize('flags', [(), *(tuple([name]) for name in FLAGS), FLAGS])
def test_actual_installers_keep_selected_readers_and_original_owner(tmp_path, flags):
    with Store(tmp_path / 'store') as store:
        owner = SimpleNamespace(store=store, run_id='selected-reader-types', directory=tmp_path,
            resources={'selected': {name: {'selected': True} for name in flags}})
        installer.install_primary_result_readers(owner)
        installer.install_preparation_result_readers(owner)
        for name in ('native_hmmer_results', 'native_blast_masking_results',
                'native_blast_masking_returns', 'native_blast_utility_results', 'native_blast_utility_returns'):
            assert getattr(owner, name) is not None
        for key in FLAGS:
            assert (getattr(owner, key + '_results') is not None) == (key in flags)
            assert (getattr(owner, key + '_returns') is not None) == (key in flags)
        for name, reader in vars(owner).items():
            if name.endswith(('_results', '_returns')) and reader is not None:
                assert reader.owner is owner and reader.store is store
                if hasattr(reader, 'results'):
                    assert reader.results is getattr(owner, name.removesuffix('_returns') + '_results')


def test_utility_helper_uses_existing_worker_and_own_exception():
    from gene_annotation_episode.episodic_workflow.root.a104.library import native_blast_utility_capture_failure as helper
    from gene_annotation_episode.episodic_workflow.root.a104.library import native_blast_utility_result_publication as publication
    from gene_annotation_episode.episodic_workflow.root.a104 import native_blast_utility_result_worker as worker
    from gene_annotation_episode.episodic_workflow.root.a104.local_jobs import LocalJobPolicy
    assert helper.ContractError is publication.ContractError is worker.ContractError is ContractError
    assert helper.captured_utility_observations is worker.captured_utility_observations
    assert helper.qualified_utility_context is worker.qualified_utility_context
    assert publication.LocalJobPolicy is LocalJobPolicy
    with pytest.raises(ContractError, match='native_blast_utility_capture_failure_fixture'):
        helper._require(False, 'fixture')


def synthetic_preparation_failure():
    """Controlled qualified-record input; no native invocation is claimed."""
    prefix = 'native_hmmer_preparation_'
    bundle = {'inputs': [{'role': 'queries', 'ordinal': 0, 'format': 'text',
        'relative_path': 'inputs/queries/0', 'final_sha256': 'a' * 64, 'final_size_bytes': 12}],
        'working_copies': [], 'artifacts': [],
        'requested_job': {'native_hmmer_preparation': {'program': 'hmmerfm-exactmatch', 'outputs': []}},
        'failures': [{'stage': 'preflight', 'code': prefix + 'invalid_exactmatch_queries',
            'role': 'queries', 'detail': {'ordinal': 7, 'reason': 'query_empty'}}]}
    reference = 'artifact_' + 'b' * 64
    body = {'assignment': {'handoff_ref': 'source_original_handoff'}, 'source_ref': 'source_original_result',
        'capture': {'bundle_artifact_ref': reference}, 'prepared': {'occurrences': []},
        'failures': [{'stage': 'preflight', 'code': prefix + 'invalid_exactmatch_queries',
            'record_key': reference + '#/failures/0'}]}
    return body, bundle


def test_preparation_failure_keeps_query_line_separate_from_operand_and_deduplicates():
    from gene_annotation_episode.episodic_workflow.root.a104.library.native_hmmer_preparation_failure_views import preparation_failure_facts
    body, bundle = synthetic_preparation_failure()
    body['failures'] *= 2
    before = deepcopy((body, bundle))
    row, = preparation_failure_facts(body, bundle=bundle)
    assert row['affected'] == {'direction': 'input', 'role': 'queries', 'ordinal': 0}
    assert row['record_key'] == body['failures'][0]['record_key']
    assert row['code'] == 'native_hmmer_preparation_invalid_exactmatch_queries'
    assert (body, bundle) == before


@pytest.mark.parametrize('fault', ('stage', 'code', 'locator', 'foreign_bundle', 'role'))
def test_preparation_failure_rejects_changed_original_qualification(fault):
    from gene_annotation_episode.episodic_workflow.root.a104.library.native_hmmer_preparation_failure_views import preparation_failure_facts
    body, bundle = synthetic_preparation_failure()
    if fault == 'stage':
        body['failures'][0]['stage'] = 'inputs'
    elif fault == 'code':
        body['failures'][0]['code'] = 'native_hmmer_preparation_invalid_model_format'
    elif fault == 'locator':
        body['failures'][0]['record_key'] = body['failures'][0]['record_key'][:-1] + '01'
    elif fault == 'foreign_bundle':
        body['failures'][0]['record_key'] = 'artifact_wrong#/failures/0'
    else:
        bundle['failures'][0]['role'] = 'fm_database'
    with pytest.raises(ContractError, match='failure_locator_conflict'):
        preparation_failure_facts(body, bundle=bundle)
