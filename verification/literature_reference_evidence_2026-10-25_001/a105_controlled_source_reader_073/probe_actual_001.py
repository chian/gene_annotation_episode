import json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from gene_annotation_episode import literature_controlled_response_v2_inputs as reader
from gene_annotation_episode.literature_controlled_response_owner_calculations import populate_controlled_response_owner
from jsonschema import Draft202012Validator
base=Path(__file__).resolve().parent.parent/'a105_controlled_full_source_design_069'
cases=json.loads((base/'CONSTRUCTED_SOURCE_CASES_001.json').read_text())
roster=json.loads((base/'CONSTRUCTED_SOURCE_ROSTER_001.json').read_text())
for case in cases:
 data={r['source_ref']: (r['content_utf8'].encode() if r['content_utf8'] is not None else (base/r['encoded_image_file']).read_bytes())for r in roster}
 data[case['selection']['covariance']['source_ref']]=case['source_covariance_text'].encode()
 def read(ref,rep):
  raw=data[ref]; return {'artifact_ref':'artifact_'+hashlib.sha256(raw).hexdigest(),'content':raw}
 try:
  result=reader.read_controlled_response_v2_inputs(case['selection'],read_source=read)
  Draft202012Validator(reader._extraction_schema()).validate(result)
  sheet=populate_controlled_response_owner(result['calculation_inputs'])
  print(case['name'],result['covariance']['projection_state'],sheet['cells']['controlled_response_difference']['value'],sheet['cells']['contrast_variance']['value'])
 except Exception as exc:
  print(case['name'],type(exc).__name__,str(exc)[:2000]);raise
