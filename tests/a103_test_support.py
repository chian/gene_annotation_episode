"""Small explicitly engineered genomic inputs for A103 contract checks."""
from __future__ import annotations

from copy import deepcopy
import io

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import SeqFeature, SimpleLocation
from Bio.SeqRecord import SeqRecord

from gene_annotation_episode.a103_scoring import bind_locus, binding_summary, neighborhood, digest
from gene_annotation_episode.a103_publication import publish
from gene_annotation_episode.biopython_pairwise_grader import grade_biopython_pairwise
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.sequence_ops import align_pair
from gene_annotation_episode.tool_grading_artifacts import retain_tool_grading


CODONS = {'M':'ATG','D':'GAT','E':'GAA','A':'GCT','K':'AAA','G':'GGT','Q':'CAA','N':'AAT'}


def source(store,provider,body):
    artifact = store.artifact(canonical(body),'application/json')
    return store.put('source',{'provider':provider,'accession':digest(body),'uri':None,
        'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':'engineering_fixture',
        'retrieved_at':None},origin='tool')['id']


def protein(store,sequence,origin,accession):
    artifact = store.artifact(sequence,'text/plain')
    return store.put('reference',{'reference_type':'protein','source_ref':origin,'accession':accession,
        'label':'Engineering protein sequence; no biological function claimed','sequence_ref':artifact,
        'molecule':'protein','length':len(sequence),'term_refs':[],'context_refs':[]},origin='tool')['id']


def genomic_file(path,identity,*,anchor='MDEAKG',partner='MKQQ',gap=9,reverse=False,circular=False):
    data = list('A'*400)
    features = []
    start = 100
    for name,sequence in (('anchor',anchor),('partner',partner)):
        nt = ''.join(CODONS[a] for a in sequence)+'TAA'
        end = start+len(nt)
        strand = -1 if reverse and name=='partner' else 1
        placed = nt if strand==1 else str(Seq(nt).reverse_complement())
        data[start:end] = placed
        features.append(SeqFeature(SimpleLocation(start,end,strand=strand),type='CDS',qualifiers={
            'locus_tag':[name],'protein_id':[identity+'.'+name],'translation':[sequence],'transl_table':['11']}))
        start = end+gap
    record = SeqRecord(Seq(''.join(data)),id=identity,name=identity,description='Engineered A103 contract fixture')
    record.annotations.update(molecule_type='DNA',topology='circular' if circular else 'linear',organism='Engineering fixture')
    record.features = features
    SeqIO.write(record,path,'genbank')
    return path


def binding(store,path,target,known,*,supplied=False):
    raw = store.artifact(path.read_bytes(),'text/plain')
    origin = store.put('source',{'provider':'engineering.genome','accession':path.stem,'uri':None,
        'artifact_ref':raw,'text_ref':raw,'request_ref':None,'version':'engineering_fixture','retrieved_at':None},origin='external')['id']
    body = bind_locus({'input_path':str(path),'target_ref':target,'file_source_ref':origin,
        'accession':path.stem,'selector':{'locus_tag':'anchor'},'format':'genbank'})
    body.update(target_regions=[[0,store.subject_length(target)]],material_ref=target,supplied_target_genome=supplied)
    tr = body['locus']['translation']
    assert tr['status']=='verified'
    component = protein(store,tr['sequence'],origin,path.stem+'.anchor')
    body['protein_reference_ref'] = component
    reference = publish(store,binding_summary(body),[target,component])
    store.db.execute('CREATE TABLE IF NOT EXISTS a103_bindings (source_ref TEXT PRIMARY KEY,body TEXT NOT NULL)')
    store.db.execute('INSERT OR IGNORE INTO a103_bindings VALUES(?,?)',(reference,canonical(body)))
    known.update({origin,component,reference})
    return reference,body


def measured_neighborhood(store,binding_ref,body,known):
    result = neighborhood(body,100,200)
    result.update(binding_ref=binding_ref,target_regions=body['target_regions'])
    for row in result['cds']:
        tr = row['translation']
        component = protein(store,tr['sequence'],body['file_source_ref'],
            body['accession']+'.CDS.'+str(row['source_feature_index']))
        row['protein_reference_ref'] = component
        known.add(component)
    ref = publish(store,result,[body['target_ref']])
    known.add(ref)
    return ref,result


def native_pair(store,query,reference,known):
    def seq(ref):return store.get_artifact(store.get(ref)['sequence_ref']).decode()
    native = align_pair(seq(query),seq(reference),molecule='protein',mode='global')
    grade = grade_biopython_pairwise(native,molecule='protein',_retain_correspondence=True)
    artifact = store.artifact(canonical(native),'application/json')
    grading = retain_tool_grading(store,provider='biopython.alignment',native_artifact_ref=artifact,grading=grade)
    origin = store.put('source',{'provider':'biopython.alignment','accession':digest(native),'uri':None,
        'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':'actual_native_pairwise',
        'retrieved_at':None,'auxiliary_artifact_refs':[grading]},origin='tool')['id']
    obs = store.put('observation',{'subject_refs':[query],'source_subject_refs':[reference],'kind':'alignment',
        'source_ref':origin,'measurements':[],'dependencies':[query,reference],'anchor':None},origin='tool')['id']
    known.update({query,reference,origin,obs})
    return obs
