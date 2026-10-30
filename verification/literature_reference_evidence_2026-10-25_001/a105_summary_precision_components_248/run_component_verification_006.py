"""Final pure-component checks, exact public source outputs and actual imports."""
from pathlib import Path
import contextlib,hashlib,importlib.metadata,json,shutil,sys,time
import pytest
H=Path(__file__).resolve().parent
R=H.parents[2]
PIN=H/'pin_006'
assert not PIN.exists()
PIN.mkdir()

def digest(p):
 p=Path(p);raw=p.read_bytes();return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def save(n,v):(H/n).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
new=['gene_annotation_episode/literature_kinetic_summary_precision_inputs.py','gene_annotation_episode/literature_kinetic_summary_precision_calculations.py','gene_annotation_episode/literature_kinetic_summary_precision_prompt.py','tests/test_literature_kinetic_summary_precision_components_248.py']
tests=['tests/test_literature_kinetic_summary_precision_components_248.py','tests/test_literature_kinetic_inputs.py','tests/test_literature_kinetic_count_inputs.py','tests/test_literature_kinetic_calculations.py','tests/test_literature_rate_native_inputs.py','tests/test_literature_rate_replicates.py']
before={p:digest(R/p) for p in new}
started=time.monotonic()
with (H/'pytest_006.stdout.txt').open('w') as out,(H/'pytest_006.stderr.txt').open('w') as err,contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
 status=int(pytest.main(['-q','--junitxml='+str(H/'pytest_006.junit.xml'),*tests]))
elapsed=time.monotonic()-started
assert before=={p:digest(R/p) for p in new},'Owned code changed while testing'
# Actual source extraction/calculation/reconstruction, without selected integration.
from gene_annotation_episode.literature_kinetic_summary_precision_inputs import read_kinetic_summary_precision_inputs,validate_kinetic_summary_precision_extraction
from gene_annotation_episode.literature_kinetic_summary_precision_calculations import populate_kinetic_summary_precision
source_dir=R/'research/experimental_scoring_review_2026-10-23/a105_independent_preparation_case_242/sources'
source_files=[]
def read_source(reference,representation):
 assert reference=='@elife2015AP'
 p=source_dir/('elife-06181-v2.pdf' if representation=='original' else 'elife-06181-v2.txt')
 raw=p.read_bytes();source_files.append(p)
 return {'artifact_ref':'sha256_'+hashlib.sha256(raw).hexdigest(),'content':raw}
selection=json.loads((H/'ACTUAL_SOURCE_SELECTION_PROPOSAL_002.json').read_text())
extraction=read_kinetic_summary_precision_inputs(selection,read_source=read_source)
assert validate_kinetic_summary_precision_extraction(extraction,read_source=read_source)==extraction
sheet=populate_kinetic_summary_precision(extraction['calculation_inputs'])
save('ACTUAL_EXTRACTION_006.json',extraction);save('ACTUAL_SHEET_006.json',sheet)
# Pin each ACTUALLY loaded repo source; separately fingerprint third-party/system imports.
imports=[];repo_files={R/p for p in [*new,*tests]}
for name,module in sorted(sys.modules.items()):
 filename=getattr(module,'__file__',None)
 if not filename:continue
 p=Path(filename).resolve()
 if not p.is_file():continue
 row={'module':name,'path':str(p),**digest(p)}
 try:
  relative=p.relative_to(R)
 except ValueError:row['scope']='installed_dependency'
 else:
  if '.venv' in relative.parts:row['scope']='installed_dependency'
  else:row['scope']='repository_import';repo_files.add(p)
 imports.append(row)
# Test fixtures actually consumed by this workload, plus the exact retained public bytes.
fixture_names=['ACTUAL_SOURCE_SELECTION_PROPOSAL_002.json','CALCULATION_INPUTS_SCHEMA_004.json','EXTRACTION_SCHEMA_004.json','SELECTION_SCHEMA_002.json','SHEET_SCHEMA_004.json','SYNTHETIC_PARTIAL_IO_002.json','TASK_PROPOSAL_001.txt']
fixture_names += [p.name for p in H.glob('SYNTHETIC_*_SOURCE_002.json')]
for p in [*source_files,*[H/n for n in fixture_names]]:repo_files.add(p)
entries=[]
for p in sorted(repo_files):
 rel=p.relative_to(R);target=PIN/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 entries.append({'path':str(rel),'pin_path':str(target.relative_to(H)),**digest(p)})
save('ACTUAL_IMPORTS_006.json',{'imports':imports,'actual_import_count':len(imports),'installed_versions':{n:importlib.metadata.version(n) for n in ['scipy','jsonschema','Pillow','pytest']},'pin':str(PIN)})
save('PIN_MANIFEST_006.json',{'files':entries,'imports_receipt':'ACTUAL_IMPORTS_006.json','actual_source_reconstruction_equal':True,'source_acquisition':False,'provider_model':False,'selected_integration':False})
save('VERIFICATION_RECEIPT_006.json',{'pytest_exit_code':status,'elapsed_seconds':elapsed,'test_files':tests,'stdout':'pytest_006.stdout.txt','stderr':'pytest_006.stderr.txt','junit':'pytest_006.junit.xml','new_code_unchanged_during_checks':True,'pin_manifest':'PIN_MANIFEST_006.json','actual_import_count':len(imports),'actual_source_extraction_and_reconstruction':True,'ordinary_physical_count':sheet['source_cells']['independent_preparation_count']['value'],'ordinary_statistical_count':sheet['source_cells']['statistical_estimator_count']['value'],'scenario_mean_variance':sheet['scenario_cells']['mean_variance']['value'],'scenario_mean_se':sheet['scenario_cells']['mean_standard_error']['value'],'no_selected_integration_or_model_call':True,'all_owned_processes_terminal':True})
print('pytest exit',status,'elapsed',round(elapsed,2),'seconds; pinned',len(entries),'repo/source/test files and',len(imports),'actual imports.')
if status:sys.exit(status)
