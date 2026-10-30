"""Saved-only controlled034 reconstruction without importing source acquisition helpers.

Corrects recheck_saved.py: that first helper imported verify_original_source,
which loaded RAW/HTML at import before its guard. This helper never loads them.
"""
import json
import sys
from pathlib import Path
from hashlib import sha256
OUT=Path(__file__).resolve().parent
PIN=OUT.parent/'literature_model_run_030/pin_001'
sys.path.insert(0,str(PIN))
from gene_annotation_episode.state import Store
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository
import gene_annotation_episode.literature_rate_native_inputs as native
import gene_annotation_episode.literature_rate_calculations as calculations
import gene_annotation_episode.literature_rate_storage as storage
r=json.loads((OUT/'CONTROLLED_RECEIPT.json').read_bytes())
# Code-only provenance. Do not open the manifest's scientific-input entries.
generation=json.loads((OUT/'IMPORTED_GENERATION.json').read_bytes())
for item in generation['imports']:
 p=Path(item['path']);assert p.is_relative_to(PIN)
 assert sha256(p.read_bytes()).hexdigest()==item['sha256']
store=Store(OUT/'controlled_001/state')
tables=['runtime_actions','runtime_observations','runtime_forms','runtime_report_attempts',
        'literature_rate_operations','literature_rate_source_received','literature_rate_received']
def snapshot():
 return {table:sha256(json.dumps([list(row) for row in store.db.execute('select * from '+table+' order by rowid')],separators=(',',':')).encode()).hexdigest() for table in tables}
before=snapshot();get=store.get_artifact
forbidden={r['original_artifact_ref'],r['text_artifact_ref']}
accesses=[]
def get_artifact(ref):
 assert ref not in forbidden,'scientific source bytes were reopened'
 accesses.append(ref)
 return get(ref)
store.get_artifact=get_artifact
def no(*args,**kwargs):raise AssertionError('scientific parsing or population reran')
native.read_rate_source_inputs=no
calculations.populate_rate_contrast=no
storage.populate_rate_contrast=no
repo=LiteratureRateRepository(store,r['summary']['run_id'])
saved=repo.read(r['sheet_ref']);assert saved==json.loads((OUT/'CONTROLLED_SAVED_SHEET.json').read_bytes())
expected=json.loads((OUT/'CONTROLLED_RETURN.json').read_bytes())['requested_source_rate_cells']
actual=repo.source_projection().project_cells([r['sheet_ref']],permitted_record_refs=[r['sheet_ref']],components=[x['component'] for x in expected])
assert actual==expected and before==snapshot()
store.close()
result={'status':'passed','correction_to':'SAVED_ONLY_RECHECK.json: first helper loaded source bytes at import before guarding; its guard scope alone did not establish a source-free process',
 'scientific_source_reads_forbidden':True,'source_parser_and_population_calculator_forbidden':True,
 'public_tables_before_after_equal':before,'artifact_reads':list(dict.fromkeys(accesses)),
 'pin_manifest_sha256':sha256((PIN/'SOURCE_MANIFEST.json').read_bytes()).hexdigest(),
 'imported_code_files_verified':len(generation['imports']),'projection_equal_to_original_typed_return':True}
(OUT/'SAVED_ONLY_RECHECK_002.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'passed','imported_code_files_verified':len(generation['imports']),'public_tables_unchanged':len(tables)}))
