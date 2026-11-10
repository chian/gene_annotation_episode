"""Real BioY-window detection using new bounded native phmmer jobs.

Scientific choices here are scripted algorithm checks. Fresh model decisions
are exercised separately by the real investigation entry point.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

from Bio import SeqIO
import pytest

from gene_annotation_episode.a103_detection import search_receipt,detect
from gene_annotation_episode.a103_scoring import bind_locus,binding_summary,neighborhood,_translation,cooccurrence
from gene_annotation_episode.a103_publication import publish
from gene_annotation_episode.a103_attachments import refresh,target_link
from gene_annotation_episode.a103_credit import A103ContextCredit
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.homology_results import HomologyResults,NativePhmmerInput
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import prepare_job,start_prepared,wait_job
from gene_annotation_episode.state import Store
from a103_native_fixture import REAL,PROGRAM,genomic_source
from a103_test_support import protein


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def execute_bounded(command,directory):
    policy=LocalJobPolicy(1024 ** 3, 128 * 1024 ** 2)
    handle=prepare_job(command,cwd=directory,policy=policy,handle_path=directory/'search.handle.json',
        stdout_path=directory/'native.stdout',stderr_path=directory/'native.stderr',cpu_threads=1)
    while True:
        try:start_prepared(handle);break
        except AcquisitionError as error:
            if error.code!='local_resource_busy':raise
            time.sleep(.2)
    result=wait_job(handle)
    assert result.returncode==0,result
    return policy,handle


def native_search(store,query,database,directory,scope):
    directory.mkdir()
    query_path=directory/'query.faa'
    query_path.write_text('>query\n'+store.get_artifact(store.get(query)['sequence_ref']).decode()+'\n')
    command=[str(PROGRAM),'--cpu','1','--tblout',str(directory/'hits.tbl'),
        '--domtblout',str(directory/'domains.tbl'),str(query_path),str(database)]
    policy,handle=execute_bounded(command,directory)
    inputs=NativePhmmerInput(query,query_path,database,directory/'native.stdout',directory/'hits.tbl',
        sha(database),sha(PROGRAM),{'kind':'actual_bounded_A103_detection_control',
            'native_parameters':{'command':command,'cpu':1,'search_mode':'native_defaults'}},directory/'domains.tbl')
    adapter=HomologyResults(store,policy=policy)
    while True:
        try:outcome=asyncio.run(adapter.extract(inputs,scope=scope,limit=2048));break
        except AcquisitionError as error:
            if error.code!='local_resource_busy':raise
            time.sleep(.2)
    assert outcome['status']=='completed',outcome
    return outcome['result']


def test_real_complete_search_scoped_absence_unknown_and_cooccurrence(tmp_path):
    files=['rcapsulatus-bioy.gb','bsubtilis-bioy.gb']
    records=[next(SeqIO.parse(REAL/name,'genbank')) for name in files]
    query_sequence=_translation(records[0],records[0].features[290])['sequence']
    with Store(tmp_path/'state') as store:
        target,=store.create_problem(raw_sequence=query_sequence,molecule='protein')['subject_refs']
        scope={'subject_refs':[target]}
        sources=[genomic_source(store,name) for name in files]
        known={target,*sources}
        database=tmp_path/'complete-searched-cds.faa'
        database.write_text(''.join('>'+record.id+'.CDS.'+str(i)+'\n'+tr['sequence']+'\n'
            for record in records for i,feature in enumerate(record.features) if feature.type=='CDS'
            and (tr:=_translation(record,feature))['status']=='verified'))
        artifact=store.artifact(database.read_bytes(),'text/plain')
        database_source=store.put('source',{'provider':'retained.a103.complete_cds_panel','accession':'explicit-real-CDS-panel',
            'uri':None,'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,
            'version':'actual_record_CDS_sequences','retrieved_at':None},origin='external')['id']
        known.add(database_source)
        partner_sequence=_translation(records[0],records[0].features[292])['sequence']
        partner=protein(store,partner_sequence,sources[0],'NC_014034.1.CDS.292')
        known.add(partner)
        bindings=[];neighbors=[]
        store.db.execute('CREATE TABLE a103_bindings(source_ref TEXT PRIMARY KEY,body TEXT NOT NULL)')
        for i,(filename,record,source) in enumerate(zip(files,records,sources)):
            body=bind_locus({'input_path':str(REAL/filename),'target_ref':target,'file_source_ref':source,
                'accession':record.id,'selector':{'protein_id':('WP_013068946.1' if i==0 else 'NP_388918.1')},
                'format':'genbank','query_sequence':query_sequence,'query_molecule':'protein'})
            body.update(target_regions=[[0,len(query_sequence)]],material_ref=target,supplied_target_genome=i==0)
            body['protein_reference_ref']=protein(store,body['locus']['translation']['sequence'],source,record.id+'.bioy')
            known.add(body['protein_reference_ref'])
            ref=publish(store,binding_summary(body),[target,body['protein_reference_ref']])
            store.db.execute('INSERT INTO a103_bindings VALUES(?,?)',(ref,canonical(body)));known.add(ref)
            measured=neighborhood(body,1500,2500)
            measured.update(binding_ref=ref,target_regions=body['target_regions'])
            nref=publish(store,measured,[target,ref]);known.add(nref)
            bindings.append((ref,body));neighbors.append((nref,measured))
        detections={}
        report=[]
        for label,query in [('bioy',target),('partner',partner)]:
            result=native_search(store,query,database,tmp_path/label,scope)
            known.update(r['id'] for r in store.list('source'))
            metadata,query_peptide=search_receipt(store,result['snapshot_ref'],result['native_source_ref'],query,known)
            for i,((binding_ref,body),(nref,measured)) in enumerate(zip(bindings,neighbors)):
                request={'component_ref':query,'snapshot_ref':result['snapshot_ref'],'native_source_ref':result['native_source_ref'],
                    'native_path':str(tmp_path/label/'native.stdout'),'database_path':str(database),
                    'database_source_ref':database_source,'search_metadata':metadata,'query_sequence':query_peptide,
                    'bindings':[body],'neighborhood':measured,'neighborhood_ref':nref}
                detected=detect(request)
                assert detected['native_search_complete'] and detected['all_actual_cds_in_search'],detected
                detected.update(target_ref=target,target_regions=[[0,len(query_sequence)]],binding_refs=[binding_ref])
                dref=publish(store,detected,[query,binding_ref,nref]);known.add(dref)
                detections[label,i]=(dref,detected)
                report.append({'query':label,'record':body['accession'],'present':detected['present'],
                    'searched_cds':detected['searched_cds'],'scope':detected['scope']})
                if label=='partner' and i==1:
                    assert detected['present'] is False,detected
                    # The full original record also contains incomplete edge
                    # CDSs. The examined local neighborhood was complete;
                    # expanding the scope must preserve those real unknowns.
                    narrowed={**request,'neighborhood':None,'neighborhood_ref':None}
                    unknown=detect(narrowed)
                    assert unknown['present'] is None and unknown['uncertain_cds']
        assert detections['partner',0][1]['present'] is True
        rows=[{'genome_key':detections['bioy',i][1]['genome_key'],'sampling_group':'organism-'+str(i),
            'left_present':detections['bioy',i][1]['present'],'right_present':detections['partner',i][1]['present']}
            for i in range(2)]
        association=cooccurrence(rows)
        association.update(target_ref=target,target_regions=[[0,len(query_sequence)]],left_reference_ref=target,
            right_reference_ref=partner,definition_source_refs=sources,
            detection_refs=[d[0] for d in detections.values()],detection_scope='actual_received_detection_inventories',
            comparison_group='actual-two-window-panel',comparison_variant='native-searches-1')
        ref=publish(store,association,[target,partner,*sources]);known.add(ref)
        generated,_=refresh(store,known,scope);known.update(generated)
        projected=A103ContextCredit()(store,scope,known_record_refs=known)
        assert projected['a103_sheet']['cooccurrence'][0]['source_ref']==ref
        assert projected['credit']==pytest.approx(association['native_significance_index'] or 0)
        (tmp_path/'REAL_DETECTION_RESULTS.json').write_text(json.dumps({'detections':report,
            'contingency':association['contingency'],'p_value':association['p_value'],
            'A103_credit':projected['credit'],'decision_mode':'scripted_real_native_algorithm_control'},indent=2))


def test_real_unmapped_protein_does_not_inherit_a_selected_reference_neighborhood(tmp_path):
    record=next(SeqIO.parse(REAL/'rcapsulatus-bioy.gb','genbank'))
    sequence=_translation(record,record.features[290])['sequence']
    with Store(tmp_path/'state') as store:
        target,=store.create_problem(raw_sequence=sequence,molecule='protein')['subject_refs']
        origin=genomic_source(store,'ecoli-window.gb')
        body=bind_locus({'input_path':str(REAL/'ecoli-window.gb'),'target_ref':target,'file_source_ref':origin,
            'accession':'NC_000913.3','selector':{'locus_tag':'b4167'},'format':'genbank',
            'query_sequence':sequence,'query_molecule':'protein'})
        assert body['native_input_placement']['state']=='not_found'
        actual=protein(store,body['locus']['translation']['sequence'],origin,'NC_000913.3.CDS.60')
        body.update(protein_reference_ref=actual,material_ref=target,target_regions=[[0,len(sequence)]],supplied_target_genome=False)
        link=target_link(store,target,body,{target,origin,actual})
        assert link['factor'] is None and link['state']=='unresolved'
        assert link['target_organism_inferred'] is False
        value=A103ContextCredit()(store,{'subject_refs':[target]},known_record_refs={target,origin,actual})
        assert value['credit']==0 and value['source_contribution_count']==0
