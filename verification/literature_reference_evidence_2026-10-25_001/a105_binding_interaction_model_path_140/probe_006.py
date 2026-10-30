"""Concrete synthetic prepared-packet population; no paper/model-service claim."""
from pathlib import Path
from dataclasses import replace
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from gene_annotation_episode.communication import plain
from gene_annotation_episode.literature_binding_interaction_model_storage import COMPONENTS
from test_literature_binding_interaction_model_inputs import setup_model
from test_literature_binding_interaction_model_storage import populate

results=[]
for status in ('known','estimated','absent'):
    store,context,native,args,_,_=setup_model(OUT/('synthetic_prepared_packet_006_'+status),status='known' if status=='absent' else status)
    try:
        if status=='absent':args.update(model_source_ref=None,model_witnesses=[])
        repo,owner,_,outcome,original=populate(store,context,native,args)
        rows=repo.fact_cells(owner,[outcome['result']['sheet_ref']],components=COMPONENTS)
        results.append({'variance_case':status,'native_eight_cells':original['result']['cells'],
            'four_supplemental_rows':rows,'scope':'synthetic prepared packet, direct selected adapter probe; ordinary runtime accounting established separately by integration tests'})
    finally:store.close()
(OUT/'SYNTHETIC_POPULATION_006.json').write_text(json.dumps({'scientific_status':'synthetic_engineering_fixture_only','primary_covariance_extraction':'unimplemented; packet needs host canonical estimate keys','cases':results},indent=2)+'\n')
files=[*ROOT.glob('gene_annotation_episode/literature_binding_interaction_model_*.py'),
    *ROOT.glob('tests/test_literature_binding_interaction_model_*.py'),
    ROOT/'gene_annotation_episode/literature_episodes.py',ROOT/'gene_annotation_episode/literature_experimental_prompt.py',
    ROOT/'tests/test_literature_parent_population_information.py',ROOT/'gene_annotation_episode/defaults.toml',
    *ROOT.glob('gene_annotation_episode/*schemas.json')]
(OUT/'SOURCE_FINGERPRINTS_006.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},indent=2)+'\n')
print(json.dumps([{r['component']:r['value'] for r in case['four_supplemental_rows']} for case in results],indent=2))
