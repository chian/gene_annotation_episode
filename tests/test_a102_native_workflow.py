"""Real structures, scripted episode choices, real native scores and receipts."""
import asyncio
import json
import os

import pytest

from gene_annotation_episode.a102_publication import received_grade
from gene_annotation_episode.state import Store
from a102_native_fixture import NativeCase


CASES=[('tpi','P0A858.faa','AF_P0A858.pdb','1YPI.cif'),
    ('lacy','P02920.faa','AF_P02920.pdb','AF_P18817.pdb'),
    ('atpg','P0ABA6.faa','AF_P0ABA6.pdb','AF_Q9KNH4.pdb'),
    ('lacy-mutant-construct','P02920.faa','1PV7.cif','AF_P18817.pdb'),
    ('mj0226-hisrs','MJ0226.faa','1B78.cif','1ADJ.cif'),
    ('mj0226-glyrs','MJ0226.faa','1B78.cif','1ATI.cif'),
    ('unrelated','P0A858.faa','AF_P0A858.pdb','AF_P18817.pdb')]


@pytest.mark.parametrize('case_id,sequence_file,target_file,reference_file',CASES,ids=[r[0] for r in CASES])
def test_native_comparisons_automatically_credit_owner_and_parent(tmp_path,case_id,sequence_file,target_file,reference_file):
    program=os.environ.get('A102_USALIGN')
    if not program:pytest.skip('Set A102_USALIGN to the pinned US-align binary for native structure validation')
    with Store(tmp_path/'state') as store:
        case=NativeCase(tmp_path,store,sequence_file=sequence_file,target_file=target_file,
            reference_file=reference_file,usalign=program)
        record=asyncio.run(case.run())
        rows=store.db.execute('SELECT source_ref FROM a102_native_publications').fetchall()
        assert len(rows)==1
        grade=received_grade(store,rows[0][0])['grade'];base=grade['components']['B']
        assert grade['eligible']
        assert case.credit_before_inspection==pytest.approx(base)
        assert record.controller_state.current_credit==pytest.approx(base)
        owner=store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')='scientific_process'").fetchone()[0]
        root=store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')='annotation'").fetchone()[0]
        assert rows[0][0] in case.flow.receipts.known(owner)
        assert rows[0][0] in case.flow.receipts.known(root)
        assert store.count('assessment')==store.count('annotation')==0
        assert all(view['local']['limits']['cpu_threads']==1 for views in case.resource_views.values() for view in views)
        assert grade['function_specific']['E'] is None
        if case_id in {'tpi','lacy','atpg'}:assert base>.3
        if case_id in {'mj0226-hisrs','mj0226-glyrs','unrelated'}:assert base<.3
        result={'case':case_id,'B':base,'components':grade['components'],
            'target_model':grade['target_model'],'reference_model':grade['reference_model'],
            'native_metrics':grade['native_metrics'],'owner_credit':case.credit_before_inspection,
            'parent_credit':record.controller_state.current_credit,'F':None,'E':None,'contrast':None}
        (tmp_path/'real_result.json').write_text(json.dumps(result,indent=2)+'\n')
        if case_id=='lacy-mutant-construct':
            assert 'C154G' in ' '.join(grade['target_model']['qualifications'])
            binding=store.db.execute('SELECT body FROM a102_structure_bindings WHERE source_ref=?',
                (grade['target_binding_ref'],)).fetchone()[0]
            assert any(row['input_symbol']=='C' and row['model_symbol']=='G'
                for row in json.loads(binding)['mapping_algorithm']['substitutions'])


def test_complete_foldseek_comparison_is_graded_without_pairwise_followup(tmp_path):
    usalign=os.environ.get('A102_USALIGN');foldseek=os.environ.get('A102_FOLDSEEK')
    if not foldseek:pytest.skip('Set A102_FOLDSEEK to the pinned Foldseek binary')
    with Store(tmp_path/'state') as store:
        case=NativeCase(tmp_path,store,sequence_file='P0A858.faa',target_file='AF_P0A858.pdb',
            reference_file='1YPI.cif',usalign=usalign,foldseek=foldseek,discover=True)
        record=asyncio.run(case.run())
        rows=store.db.execute('SELECT source_ref FROM a102_native_publications').fetchall()
        assert len(rows)==1
        grade=received_grade(store,rows[0][0])['grade']
        assert grade['producer']=='Foldseek'
        assert record.controller_state.current_credit==pytest.approx(grade['components']['B'])
        assert case.credit_before_inspection>0
        assert not store.db.execute("SELECT 1 FROM a102_tool_operations WHERE json_extract(request,'$.name')='structure.align'").fetchone()


def test_real_fragment_is_mapped_without_claiming_biological_completeness(tmp_path):
    program=os.environ.get('A102_USALIGN')
    if not program:pytest.skip('Set A102_USALIGN for a real fragment comparison')
    with Store(tmp_path/'state') as store:
        case=NativeCase(tmp_path,store,sequence_file='P0A858.faa',target_file='AF_P0A858.pdb',
            reference_file='1YPI.cif',usalign=program,fragment=128)
        record=asyncio.run(case.run())
        source=store.db.execute('SELECT source_ref FROM a102_native_publications').fetchone()[0]
        grade=received_grade(store,source)['grade']
        assert grade['supplied_length']==128 and max(grade['target_positions'])<128
        assert grade['components']['n_pairs']<=128
        assert record.controller_state.current_credit==pytest.approx(case.credit_before_inspection)
        sheet=case.flow.project_credit(store,case.scope,known_record_refs=[source])['target_sheets'][case.target]
        assert sheet['full_target_index']['value'] is None
        (tmp_path/'real_result.json').write_text(json.dumps({'case':'tpi-fragment-128',
            'components':grade['components'],'owner_credit':case.credit_before_inspection,
            'parent_credit':record.controller_state.current_credit,'full_target_index':sheet['full_target_index']},indent=2)+'\n')


def test_real_subregion_returns_original_positions_and_parent_recomputes_extent(tmp_path):
    program=os.environ.get('A102_USALIGN')
    if not program:pytest.skip('Set A102_USALIGN for the real original-coordinate subregion comparison')
    with Store(tmp_path/'state') as store:
        case=NativeCase(tmp_path,store,sequence_file='P0A858.faa',target_file='AF_P0A858.pdb',
            reference_file='1YPI.cif',usalign=program,region=(50,150))
        record=asyncio.run(case.run())
        source=store.db.execute('SELECT source_ref FROM a102_native_publications').fetchone()[0]
        grade=received_grade(store,source)['grade']
        assert grade['target_ref']==case.target and grade['supplied_length']==255
        assert min(grade['target_positions'])>=50 and max(grade['target_positions'])<150
        assert 0<record.controller_state.current_credit<case.credit_before_inspection
        assert record.controller_state.current_credit/ case.credit_before_inspection==pytest.approx((100+247)/(255+247))
        (tmp_path/'real_result.json').write_text(json.dumps({'case':'tpi-original-region-50-150',
            'components':grade['components'],'owner_credit':case.credit_before_inspection,
            'parent_credit':record.controller_state.current_credit,'target_scope':grade['target_scope']},indent=2)+'\n')
