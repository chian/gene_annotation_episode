"""Retain actual new profile evidence and its scoped scientific qualifications."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import sqlite3

RUN = Path('/home/chia/gene_annotation_episode_runs/configured_api_prechoice_001')
OUT = Path('/tmp/configured-caller-actual-science-20261022-002')
OUT.mkdir(mode=0o700, exist_ok=True)
assert not any(OUT.iterdir()), 'proof_destination_not_empty'
run_id = 'run_23b029a976e343e2bf3957dcc5d0d2ac'
episode_id = 'episode_3f296d8c6dbd96a740157d29eceda747dd4cc7b19d97b4763735999fe99b1979'
committed = {r['reference'] for r in json.loads(
    (RUN/'workspace/checkpoint/committed-references.json').read_text())['records']}


def write(name, value):
    with (OUT/name).open('x') as f:
        f.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n')
        f.flush()
        os.fsync(f.fileno())


def witness(path):
    b = path.read_bytes()
    return {'path':str(path), 'sha256':hashlib.sha256(b).hexdigest(), 'bytes':len(b)}


db = sqlite3.connect((RUN/'workspace/state.sqlite3').as_uri()+'?mode=ro', uri=True)
db.row_factory = sqlite3.Row
try:
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    records = {}
    def get(ref):
        row = db.execute('SELECT data FROM records WHERE id=?', (ref,)).fetchone()
        assert row is not None
        v = json.loads(row[0]); records[ref] = v
        return v

    selected = {}
    for index in (29,30,32,33,34):
        r = db.execute('SELECT action,result,credit FROM runtime_actions WHERE run_id=? '
            'AND episode_id=? AND decision_index=?', (run_id,episode_id,index)).fetchone()
        assert r is not None
        a, outcome = json.loads(r['action']), json.loads(r['result'])
        assert outcome['status'] == 'completed'
        selected[index] = {'selection':a,'result':outcome,'credit':r['credit']}
        for ref in outcome.get('record_refs',[]): get(ref)
    assert selected[29]['selection'] == {'kind':'tool','tool':'public.hmmer.search',
        'arguments':{'algorithm':'hmmscan','database':'pfam','page_size':20,
                     'subject_ref':'product_013bd19a5b3ea8c0af36b7d4'}}
    assert [selected[i]['credit'] for i in (29,30,32,33,34)] == [13.0,14.0,15.0,15.0,16.0]

    profile = get('assessment_8a1fcbb02b16a14a43b337af')
    activity = get('assessment_bf30b5213fa3a24a42a20e93')
    cwh43 = get('assessment_01dffdfe78c25b9b8df76826')
    obs = get(profile['observation_ref'])
    family = get(profile['investigation_finding']['source_claim']['value']['ref'])
    source = get(obs['source_ref'])
    assert obs['id'] not in committed and source['id'] not in committed
    assert obs['kind'] == 'profile_match' and family['accession'] == 'PF03372'
    assert obs['id'] in selected[29]['result']['record_refs']
    assert profile['relation']=='strengthens'
    assert profile['investigation_finding']['qualification']['kind']=='prediction_not_measurement'
    assert activity['observation_ref']==obs['id'] and activity['relation']=='mixed'
    assert activity['investigation_finding']['same_source_claim_as_ref']==profile['id']
    assert activity['investigation_finding']['qualification']['kind']=='measurement_does_not_establish_claim'
    assert cwh43['relation']=='does_not_discriminate'
    assert cwh43['investigation_finding']['qualification']['kind']=='measurement_does_not_establish_claim'
    alignment = get(cwh43['observation_ref'])
    assert alignment['id'] in committed and alignment['kind']=='alignment'
    reference = get(cwh43['investigation_finding']['source_claim']['value']['ref'])
    assert reference['accession']=='P25618' and reference['length']==953
    for finding in (profile,activity,cwh43):
        hypothesis = get(finding['hypothesis_ref'])
        get(hypothesis['value']['ref'])
        for ref in finding['condition_refs']: get(ref)
    product = get('product_013bd19a5b3ea8c0af36b7d4')

    artifacts={}
    for artifact_ref in (source['artifact_ref'],product['sequence_ref']):
        sha=artifact_ref.removeprefix('artifact_')
        path=RUN/'workspace/artifacts'/sha[:2]/sha
        b=path.read_bytes(); assert hashlib.sha256(b).hexdigest()==sha
        with (OUT/artifact_ref).open('xb') as f: f.write(b); f.flush(); os.fsync(f.fileno())
        artifacts[artifact_ref]=witness(path)
    assert len((OUT/product['sequence_ref']).read_bytes())==253
    raw=json.loads((OUT/source['artifact_ref']).read_bytes())
    assert raw['status']=='SUCCESS' and raw['result']['stats']['algo']=='hmmscan'
    assert raw['result']['stats']['database']=='pfam'
    hit=next(h for h in raw['result']['hits'] if h['metadata']['accession']=='PF03372')
    assert hit['is_included'] is True
    domain=hit['domains'][0]
    measures={m['name']:m['value']['value'] for m in obs['measurements'] if m['value']['type']=='number'}
    assert measures['bitscore']==domain['bitscore'] and measures['evalue']==domain['ievalue']
    assert measures['identity_fraction']==domain['alignment_display']['identity'][0]
    assert measures['query_start']==domain['alignment_display']['sqfrom']-1
    assert measures['query_end']==domain['alignment_display']['sqto']

    observations=[]
    for r in db.execute('SELECT unit_index,observation FROM runtime_observations WHERE run_id=? '
            'AND episode_id=? ORDER BY unit_index',(run_id,episode_id)):
        v=json.loads(r['observation'])
        if v.get('decision_index') in (29,30,32,33,34):
            observations.append(v)
    by_index={v['decision_index']:v for v in observations}
    assert set(by_index)=={29,30,32,33,34}
    assert [by_index[i]['step']['marginal_credit'] for i in (29,30,32,33,34)]==[0,1,1,0,1]
    assert all(v['step']['stop'] is False for v in observations)
    request_text=db.execute('SELECT request FROM runtime_model_calls WHERE run_id=? '
        'AND episode_id=? AND call_index=35',(run_id,episode_id)).fetchone()[0]
    request=json.loads(request_text)
    later={}
    for name,context in [('raw',request['context']),('model',request['model_presentation']['context'])]:
        assert context['current_credit']==16.0
        later[name]={k:context[k] for k in ('current_credit','investigation_progress',
            'annotation_evidence_vector') if k in context}
    annotation=get(selected[33]['result']['aliases']['integrated_annotation'])
    assert annotation['resolution']=='unresolved' and annotation['revision']==14
    meanings=[i for s in annotation['coherent_sets'] for i in s['interpretations']]
    assert any(i['hypothesis_ref']==profile['hypothesis_ref'] and i['disposition']=='supported'
               and profile['id'] in i['assessment_refs'] for i in meanings)
    assert any(i['hypothesis_ref']==activity['hypothesis_ref'] and i['disposition']=='unresolved'
               and activity['id'] in i['assessment_refs'] for i in meanings)
    counts={table:db.execute('SELECT count(*) FROM '+table+' WHERE run_id=?',(run_id,)).fetchone()[0]
            for table in ('runtime_episodes','runtime_actions','runtime_observations','runtime_commission_intents')}
    assert counts['runtime_episodes']==1 and counts['runtime_commission_intents']==0
    result={'captured_at':datetime.now(timezone.utc).isoformat(),'run_id':run_id,'episode_id':episode_id,
        'kind':'actual_configured_model_science_own_actions','selected':selected,'records':records,
        'actual_observations':observations,'later_call35_request_sha256':hashlib.sha256(request_text.encode()).hexdigest(),
        'later_call35_views':later,'artifact_sources':artifacts,'counts_at_snapshot':counts,
        'interpretation_limits':['PF03372 profile supports broad family correspondence, not measured activity or substrate',
            'activity qualification explicitly reuses the same profile source claim, not another experiment',
            'P25618 alignment is inherited evidence, not newly performed native work',
            'annotation remains unresolved; no scientific child commission or child-to-parent influence demonstrated']}
finally:
    db.close()
write('SCIENCE_GAIN002.json',result)
write('READSET002.json',{'script':witness(Path(__file__)),'run_manifest':witness(RUN/'run.json'),
    'db_mode':'readonly/query_only/explicit transaction/closed','original_db_opened':False,
    'store_or_application_imports':0,'new_model_service_or_native_calls':0,'source_or_runtime_mutations':0})
members={p.name:{'sha256':witness(p)['sha256'],'bytes':p.stat().st_size} for p in OUT.iterdir() if p.is_file()}
write('MANIFEST002.json',{'members':members})
for p in OUT.iterdir():p.chmod(0o444)
OUT.chmod(0o500)
print(json.dumps({'proof':str(OUT),'manifest':witness(OUT/'MANIFEST002.json'),
    'counts':counts,'new_own_progress':[13,14,15,15,16],'child_influence_demonstrated':False},sort_keys=True))
