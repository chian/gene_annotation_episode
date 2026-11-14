"""Real native result evidence must cross the admitted parent boundary."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from method_loop.durable import DurableExecutionError

from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.episode_composition import reopen_scientific_binding
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from a101_native_return_fixture import NativeReturnCase, PUBLICATION


@pytest.mark.parametrize('positive',[False,True],ids=['complete-empty-search','real-homolog-hit'])
def test_native_evidence_contracts_reach_owner_and_receiving_parent(tmp_path,positive):
    with Store(tmp_path/'state') as store:
        case=NativeReturnCase(tmp_path,store,positive=positive)
        try:
            completed=asyncio.run(case.run())
            coverage=case.coverage
            assert coverage['native_result_complete'] and coverage['parser_finished']
            assert coverage['all_parsed_rows_acquired'] and coverage['native_error_count']==0
            assert coverage['parse_execution_failed'] is False
            assert coverage['parsed_row_count']==coverage['acquired_row_count']
            assert (coverage['parsed_row_count']>0)==positive
            assert case.snapshot in case.forms['results']['records']
            assert case.snapshot in case.owner_known
            assert case.snapshot in case.received['records']
            assert case.snapshot in case.parent_known
            assert (case.received['family']['status']=='unresolved')== (not positive)
            assert 'partial_acquisition' not in case.received['limitations']
            assert bool(store.list('observation'))==positive
            assert store.count('annotation')==0
            # Native acquisition triggers subscoring with no assessment/model
            # score declaration. The configured child finding counter is not
            # the A101 role's numerical projector.
            if positive:
                assert case.received['sequence_credit'] > .99
            else:
                assert case.received['sequence_credit'] == 0
            assert case.credit_before_inspection==case.received['sequence_credit']
            assert completed.controller_state.current_credit==case.received['sequence_credit']
            episode=store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')='scientific_process'").fetchone()[0]
            observation=store.db.execute('SELECT observation FROM runtime_observations WHERE episode_id=? ORDER BY unit_index DESC LIMIT 1',(episode,)).fetchone()[0]
            assert json.loads(observation)['step']['credit']==case.received['sequence_credit']
            inspection=json.loads(store.db.execute('SELECT result FROM runtime_actions WHERE episode_id=? '
                "AND json_extract(action,'$.tool')='episode.credit'",(episode,)).fetchone()[0])
            assert inspection['result']['credit']==case.received['sequence_credit']
            assert inspection['result']['a101_sheet']['targets']
            assert store.count('assessment')==0
            assert case.jobs.db.execute('SELECT count(*),sum(submission_requested) FROM orders').fetchone()[:]==(1,1)
            assert {v['result']['source'] for v in case.information}=={
                'execution_handoff','committed_record_refs','job_result_progress'}
            assert store.db.execute("SELECT count(*) FROM runtime_actions WHERE json_extract(action,'$.tool')='episode.return_contract'").fetchone()[0]==0
            assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==12
            assert any('Explicit form reference: episode-fact:committed_record_refs' in text for text in case.presentations)
            assert any('completed empty search' in text for text in case.presentations)
        finally:case.jobs.close()


@pytest.mark.parametrize('positive',[False,True],ids=['empty-search','unreceived-real-hit'])
def test_metadata_only_return_does_not_silently_import_child_search_snapshot(tmp_path,positive):
    with Store(tmp_path/'state') as store:
        case=NativeReturnCase(tmp_path,store,return_evidence=False,positive=positive)
        try:
            asyncio.run(case.run())
            snapshots={r[0] for r in store.db.execute('SELECT source_ref FROM homology_result_snapshots')}
            assert snapshots
            assert not snapshots & case.owner_known
            assert not snapshots & case.parent_known
            assert not snapshots & set(case.received['records'])
            assert 'partial_acquisition' in case.received['limitations']
            assert case.received['sequence_credit']==0
        finally:case.jobs.close()


def test_scientific_contract_profile_is_explicit_frozen_and_role_scoped(tmp_path):
    with Store(tmp_path/'state') as store:
        descriptor=prepare_scientific_binding(run_directory=tmp_path/'run',source_directory=PUBLICATION,
            tool_catalog=ToolRegistry(store).catalog(),child_roles=('scientific_process',),
            contract_information_profile=CONTRACT_INFORMATION_PROFILE)
        assert descriptor['configuration']['contract_information_profile']==CONTRACT_INFORMATION_PROFILE
        binding=reopen_scientific_binding(None,descriptor=descriptor,directory=tmp_path/'run')
        assert binding.as_record()==descriptor
        for role in ('annotation','scientific_process'):
            assert binding.contract_information_profile(SimpleNamespace(role=role))==CONTRACT_INFORMATION_PROFILE
        assert binding.contract_information_profile(SimpleNamespace(role='results')) is None
        changed=json.loads(json.dumps(descriptor))
        changed['configuration']['contract_information_profile']='invented'
        with pytest.raises(DurableExecutionError):
            reopen_scientific_binding(None,descriptor=changed,directory=tmp_path/'run')
