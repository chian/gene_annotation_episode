"""The advertised saved status operation reads its original observation only."""
import asyncio
from copy import deepcopy
import shutil

from gene_annotation_episode import native_blast_masking_results as host
from gene_annotation_episode.state import Store
from test_native_blast_masking_host_returns import HostCase, selector


def test_saved_status_uses_original_observation_without_acquisition_or_new_credit(tmp_path, monkeypatch):
    with Store(tmp_path / 'store') as store:
        case = HostCase(store, tmp_path, monkeypatch, selected=selector(saved_data=['sheet']))
        original = case.execute()['result']
        case.admit()
        selected = selector()
        selected.update(mode='saved_recalculation', saved_sheet_ref=original['prepared']['sheet_artifact_ref'])
        child = case.result_child(selected, index=1)
        assert case.results.validate_selected_inputs(child, child.assignment) == [
            case.target['handle'], selected['saved_sheet_ref']]
        def forbidden(*args, **kwargs):
            raise AssertionError('saved status attempted fresh native observation or result work')
        monkeypatch.setattr(case.owner.job_progress_provider.targets, 'observe_target', forbidden)
        monkeypatch.setattr('gene_annotation_episode.native_blast_masking_acquisition._capture_file', forbidden)
        monkeypatch.setattr('gene_annotation_episode.native_blast_masking_acquisition.local_blast_masking_plan', forbidden)
        monkeypatch.setattr(host, 'prepare_native_blast_masking_result', forbidden)
        monkeypatch.setattr(host, 'publish_selected_masking_result', forbidden)
        shutil.rmtree(case.native_root.parent)
        outcome = case.execute(child=child, tool='execution.results.status')
        body = outcome['result']
        assert outcome['status'] == 'completed' and outcome['record_refs'] == []
        assert body['observation'] == original['observation'] and case.observations == 1
        assert body['capture'] is body['prepared'] is body['source_ref'] is body['reused_from'] is None
        assert body['status'] is None and body['complete'] is False
        assert not any(body[k] for k in ('quantities','artifacts','statistics','checks','failures','saved_data','record_refs'))
        assert case.results.credit_view(child, {'known_record_refs': [], 'initial_known_record_refs': []})['credit'] == 0
        assert case.results.completion(child) is None
        before = list(store.db.iterdump())
        replay = asyncio.run(case.results.execute(child, case.target,
            'execution.results.status', {}, body['operation_key']))
        assert replay == outcome and case.observations == 1
        assert list(store.db.iterdump()) == before
