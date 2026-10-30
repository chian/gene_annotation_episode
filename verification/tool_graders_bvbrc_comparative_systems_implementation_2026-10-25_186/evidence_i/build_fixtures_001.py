from pathlib import Path
import json
from copy import deepcopy
source=Path('tests/fixtures/bvbrc_comparative_systems_bundle')
target=Path('tests/fixtures/bvbrc_comparative_systems_integration')
x=json.loads((source/'inputs.json').read_text())['families']
p=deepcopy(x['parameters']);p['producer_evidence_selections']=[]
for d in p['document_selection']['documents']:
 d['producer_evidence_id']=None;d['input']={'kind':'requirement','requirement_id':'native'}
(target/'parameters.json').write_text(json.dumps(p,indent=2)+'\n')
(target/'families.json').write_bytes((source/'families_families_document.json').read_bytes())
(target/'CLASSIFICATION.json').write_text(json.dumps({'native_bytes':'Unchanged retained producer output from source-executed synthetic input.','transport':'Controlled AppService and Workspace response fixtures.','task_association':'Synthetic task 123; no claim the BV-BRC service produced these bytes.','producer':'Not attested by the host fixture; producing version remains unverified.','live_service_verified':False},indent=2)+'\n')
