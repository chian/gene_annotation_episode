"""Saved-only controlled034 reconstruction; paper bytes/parsing/calculation forbidden."""
import json
import sys
from pathlib import Path
from hashlib import sha256
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT))
import verify_original_source as case
from gene_annotation_episode.state import Store
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository
import gene_annotation_episode.literature_rate_native_inputs as native
import gene_annotation_episode.literature_rate_calculations as calculations
import gene_annotation_episode.literature_rate_storage as storage
r=json.loads((OUT/'CONTROLLED_RECEIPT.json').read_bytes())
pin=json.loads((case.PIN/'SOURCE_MANIFEST.json').read_bytes())
for item in pin['files']:
 p=case.PIN/item['pin_relative_path']
 assert p.stat().st_size==item['size']
 assert sha256(p.read_bytes()).hexdigest()==item['sha256']
# Constructors access only the new controlled store, never an actual run.
store=Store(OUT/'controlled_001/state')
tables=['runtime_actions','runtime_observations','runtime_forms','runtime_report_attempts',
        'literature_rate_operations','literature_rate_source_received','literature_rate_received']
def snapshot():
 return {table:sha256(json.dumps([list(row) for row in store.db.execute('select * from '+table+' order by rowid')],separators=(',',':')).encode()).hexdigest() for table in tables}
before=snapshot();get=store.get_artifact
forbidden={r['original_artifact_ref'],r['text_artifact_ref']}
def get_artifact(ref):
 assert ref not in forbidden,'scientific source bytes were reopened'
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
assert actual==expected
assert before==snapshot()
store.close()
case.save('SAVED_ONLY_RECHECK.json',{'status':'passed','scientific_source_reads_forbidden':True,
 'source_parser_and_population_calculator_forbidden':True,'public_tables_before_after_equal':before,
 'pin_manifest_sha256':sha256((case.PIN/'SOURCE_MANIFEST.json').read_bytes()).hexdigest(),
 'pin_file_count_verified':len(pin['files']),'projection_equal_to_original_typed_return':True})
print(json.dumps({'status':'passed','pin_file_count_verified':len(pin['files']),'public_tables_unchanged':len(tables)}))
