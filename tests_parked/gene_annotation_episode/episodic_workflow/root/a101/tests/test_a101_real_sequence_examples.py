"""Real transporter and complex-subunit sequences through native A101 scoring.

Inputs are anonymous amino acid sequences. Native phmmer, grading, receipt
transfer and numerical credit are real; episode decisions are scripted.
"""
import asyncio
import json

from Bio import SeqIO
import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_grading_entries
from a101_native_return_fixture import NativeReturnCase, REAL


REFERENCE_FILES = tuple(REAL/name for name in (
    'reference_tpi_Q8ZKP7.faa',
    'reference_lacy_P18817.faa',
    'reference_atpg_Q9KNH4.faa',
))


@pytest.mark.parametrize('filename,length,homolog',[
    ('transporter_lacy_P02920.faa',417,'sp|P18817|LACY_KLEOX'),
    ('complex_subunit_atpg_P0ABA6.faa',287,'sp|Q9KNH4|ATPG_VIBCH'),
],ids=['lacy-transporter','atpg-complex-subunit'])
def test_real_sequence_native_grader_automatically_credits_owner_and_parent(
        tmp_path,filename,length,homolog):
    sequence_file=REAL/filename
    query=str(SeqIO.read(sequence_file,'fasta').seq)
    assert len(query)==length
    # No exact target sequence is available in the shared reference panel.
    assert all(query!=str(SeqIO.read(path,'fasta').seq) for path in REFERENCE_FILES)
    with Store(tmp_path/'state') as store:
        case=NativeReturnCase(tmp_path,store,positive=True,sequence_file=sequence_file,
            reference_files=REFERENCE_FILES,anonymous_input=True)
        try:
            completed=asyncio.run(case.run())
            for role in ('annotation','scientific_process','launch','launch_local','results'):
                resource_context=case.resource_views[role][0]
                assert resource_context['local']['resource_id']==case.resource_views['annotation'][0]['local']['resource_id']
                assert resource_context['local']['limits']['max_running_jobs']==1
                assert resource_context['local']['limits']['cpu_threads']==1
                assert resource_context['local']['available']['job_slots'] in (0,1)
                if role in ('annotation','scientific_process','launch','launch_local'):
                    assert resource_context['local']['available']['job_slots']==1
                assert resource_context['execution_capabilities'][0]['allocation_limits']['memory_bytes']==1024**3
                assert resource_context['execution_capabilities'][0]['allocation_limits']['scratch_bytes']==64*1024**2
            assert any('Host resource limits and current shared capacity' in text for text in case.presentations)
            assert store.subject_length(case.target)==length
            coverage=case.coverage
            assert coverage['native_result_complete'] and coverage['parser_finished']
            assert coverage['all_parsed_rows_acquired'] and coverage['native_error_count']==0
            assert not coverage['parse_execution_failed']
            assert coverage['parsed_row_count']==coverage['acquired_row_count']>0
            assert case.snapshot in case.owner_known & case.parent_known
            assert case.snapshot in case.received['records']

            episode=store.db.execute("SELECT episode_id FROM runtime_episodes WHERE "
                "json_extract(path,'$[#-1][0]')='scientific_process'").fetchone()[0]
            inspection=json.loads(store.db.execute('SELECT result FROM runtime_actions WHERE '
                "episode_id=? AND json_extract(action,'$.tool')='episode.credit'",(episode,)
                ).fetchone()[0])['result']
            contributions=inspection['source_contributions']
            strongest=max(contributions,key=lambda row:row['bits'])
            assert strongest['program']=='phmmer'
            assert strongest['target_name']==homolog
            assert strongest['bits']>100
            assert 0<strongest['native_identity']<1
            assert strongest['reference_paired_fraction']>.9
            assert sum(end-start for start,end in strongest['target_intervals'])/length>.9
            # This contribution is joined to an actual retained native grader.
            grades=source_tool_grading_entries(store,strongest['source_ref'])
            assert any(grade['artifact_ref']==strongest['grading_artifact_ref']
                and grade['grading']['sheet']['schema']=='hmmer_search_sheet_v1'
                for grade in grades)

            credit=inspection['credit']
            assert .8<credit<=1
            # Reading credit is observational: acquisition already triggered it.
            assert case.credit_before_inspection==credit
            assert case.received['sequence_credit']==credit
            assert completed.controller_state.current_credit==credit
            observation=store.db.execute('SELECT observation FROM runtime_observations WHERE '
                'episode_id=? ORDER BY unit_index DESC LIMIT 1',(episode,)).fetchone()[0]
            assert json.loads(observation)['step']['credit']==credit

            sheet=inspection['a101_sheet']['targets'][case.target]
            assert sheet['profile']==['hmmer']
            assert sheet['function_specific_index']['value'] is None
            assert sheet['function_specific_index']['status']=='not_assessed'
            assert sheet['full_target_index']['value'] is None
            # Homology credit does not assert transport activity or an active
            # assembled ATP synthase, and needs no model assessment to exist.
            assert store.count('assessment')==store.count('annotation')==0
            assert case.jobs.db.execute('SELECT count(*),sum(submission_requested) FROM orders'
                ).fetchone()[:]==(1,1)
        finally:
            case.jobs.close()
