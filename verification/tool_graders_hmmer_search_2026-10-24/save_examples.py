"""Verification-only artifact assembly; production parsers/calculators stay pure.

Reads retained native bytes and writes filled sheets/results. It does not call
HMMER, download data, or assert episode integration. Run from repository root.
"""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import socket
import subprocess
from unittest.mock import patch

from gene_annotation_episode.hmmer_search_inputs import parse_hmmer_search_artifacts, parse_hmmer_api_result, build_hmmer_search_sheet
from gene_annotation_episode.hmmer_search_grader import calculate_hmmer_search_scores

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def fasta(text):
    rows=[]
    for block in text.split('>')[1:]:
        header,*lines=block.splitlines()
        seq=''.join(lines)
        rows.append({'name':header.split()[0],'sequence':seq,'length':len(seq),'kind':'protein_sequence','alphabet':'amino','source_description':header})
    return rows


def write(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def blocked(*args,**kwargs):
    raise AssertionError('saved-sheet recalculation attempted I/O, acquisition, or execution')


examples=[]
source_files=[]
local=ROOT/'cases/gene_001/jobs/homology_001'
for program in ('phmmer','hmmsearch','hmmscan','jackhmmer'):
    if program=='phmmer':
        paths={r:local/f for r,f in [('stdout','homology_search.stdout'),('tblout','hits.tbl'),('domtblout','domains.tbl')]}
        query=fasta((local/'target.faa').read_text())[0]
        targets=fasta((local/'reported-references.faa').read_text())
        provenance='retained actual 2026-10-20 local execution; not rerun'
    else:
        paths={r:BASE/'native'/f'{program}.{r}' for r in ('stdout','tblout','domtblout')}
        targets=fasta((BASE/'native/targets.fa').read_text())
        query={'name':'test','kind':'profile','length':20,'alphabet':'amino'} if program=='hmmsearch' else fasta((BASE/'native/query.fa').read_text())[0] if program=='jackhmmer' else None
        if program=='hmmscan': targets=[{'name':'test','kind':'profile','length':20,'alphabet':'amino'}]
        provenance='actual bounded 2026-10-24 native HMMER 3.4 execution on bundled tiny test inputs'
    checkpoints=[]
    if program=='jackhmmer':
        paths['included_msa']=BASE/'native/jackhmmer.included.sto'
        for n in (1,2):
            for role,prefix,suffix in [('chkhmm','round-model','hmm'),('chkali','round-included','sto')]:
                path=BASE/'native'/f'{prefix}-{n}.{suffix}'
                checkpoints.append({'role':role,'iteration':n,'text':path.read_text(),'artifact_ref':str(path.relative_to(ROOT))})
                source_files.append(path)
    source_files.extend(paths.values())
    inputs={'query':query,'targets':targets,'acquisition':{'output_complete':True,'hit_population_complete':True},'verification_provenance':provenance}
    native=parse_hmmer_search_artifacts(program=program,artifacts={r:p.read_text() for r,p in paths.items()},artifact_refs={r:str(p.relative_to(ROOT)) for r,p in paths.items()},engine_version='3.4',checkpoints=checkpoints)
    sheet=build_hmmer_search_sheet(native,inputs=inputs)
    score=calculate_hmmer_search_scores(sheet)
    write(BASE/f'{program}.sheet.json',sheet);write(BASE/f'{program}.scores.json',score)
    saved=json.loads((BASE/f'{program}.sheet.json').read_text())
    with patch('builtins.open',blocked),patch.object(socket,'socket',blocked),patch.object(subprocess,'Popen',blocked):
        recalculated=calculate_hmmer_search_scores(saved)
    assert recalculated==score
    if program=='phmmer': chosen=score['domains'][0]
    elif program=='hmmsearch': chosen=next(d for d in score['domains'] if d['target_name']=='test2')
    elif program=='hmmscan': chosen=next(d for d in score['domains'] if d['query_name']=='test2')
    else: chosen=next(d for d in score['domains'] if d['target_name']=='test2' and d['iteration']==2)
    fields=['model_length','sequence_length','paired_positions','insert_positions','delete_positions','alignment_columns','model_span_coverage','sequence_span_coverage','paired_model_coverage','paired_sequence_coverage','sequence_identity_fraction','consensus_identity_fraction','native_domain_score_bits','native_domain_bias_bits','native_independent_evalue','native_accuracy','posterior_lower_mean','posterior_upper_mean']
    examples.append({'program':program,'provenance':provenance,'hits':len(score['hits']),'domains':len(score['domains']),'queries':len(score['queries']),'iterations':len(score['iterations']),'row':{k:chosen.get(k) for k in fields},'saved_sheet_recalculation':'equal with file/network/subprocess blocked','production_integration':'not established by this pure-module verification'})

captures=ROOT/'verification/hmmer_reported_timing_actual_service_2026-10-22_001/workspace/public-search-http-captures'
for label,capture in [('api_phmmer_page1','26bc8bd463741aea924eabd181e41bfc91237dc04a04c7a3f5d03f6f64bd1e39'),('api_phmmer_page2','4e88be472b0304cdea6ed5c38126eef0d7865b5345ad21863e9c9e318afc1c67')]:
    path=captures/capture/'response.entity';source_files.append(path)
    payload=json.loads(path.read_text())
    sheet=build_hmmer_search_sheet(parse_hmmer_api_result(payload,algorithm='phmmer',artifact_ref=str(path.relative_to(ROOT))),inputs={'acquisition':{'output_complete':True,'page_count':2,'hit_population_complete':False},'verification_provenance':'retained actual remote service page acquired 2026-10-22; no new API call'})
    scores=calculate_hmmer_search_scores(sheet)
    write(BASE/f'{label}.sheet.json',sheet);write(BASE/f'{label}.scores.json',scores)
    saved=json.loads((BASE/f'{label}.sheet.json').read_text())
    with patch('builtins.open',blocked),patch.object(socket,'socket',blocked),patch.object(subprocess,'Popen',blocked):
        assert calculate_hmmer_search_scores(saved)==scores
    chosen=scores['domains'][1 if label.endswith('page1') else 0]
    examples.append({'program':label,'provenance':'retained actual API page; not complete hit population','hits':len(scores['hits']),'domains':len(scores['domains']),'row':{k:chosen.get(k) for k in ['paired_positions','insert_positions','delete_positions','alignment_columns','api_identity_fraction','consensus_identity_fraction','alignment_identity_fraction','sequence_identity_fraction','native_domain_bias_bits','posterior_lower_mean','posterior_upper_mean']},'saved_sheet_recalculation':'equal with file/network/subprocess blocked','production_integration':'not established by this pure-module verification'})

empty={'status':'SUCCESS','result':{'stats':{'algo':'hmmscan','nreported':0},'hits':[]},'page_count':1}
write(BASE/'synthetic_hmmscan_empty.payload.json',empty)
sheet=build_hmmer_search_sheet(parse_hmmer_api_result(empty,algorithm='hmmscan',artifact_ref='synthetic_hmmscan_empty.payload.json'),inputs={'acquisition':{'output_complete':True,'hit_population_complete':True},'verification_provenance':'synthetic zero-hit API payload; planned retained empty fixture path absent'})
write(BASE/'synthetic_hmmscan_empty.sheet.json',sheet)
write(BASE/'synthetic_hmmscan_empty.scores.json',calculate_hmmer_search_scores(sheet))
write(BASE/'NUMERICAL_EXAMPLES.json',examples)
manifest=[]
for path in source_files:
    data=path.read_bytes();manifest.append({'path':str(path.relative_to(ROOT)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
write(BASE/'SOURCE_MANIFEST.json',manifest)
print(json.dumps(examples,indent=2))
