"""Freeze exact files for the focused source/graph/arithmetic execution."""
from pathlib import Path
from hashlib import sha256
import difflib
import json
import shutil
import sys
import importlib.metadata

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=HERE.parent
PIN=HERE/'pin_001'
assert not PIN.exists()
def fp(path):
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
modules=['__init__','domain','literature_experimental_contracts','literature_assay_inputs','literature_rate_native_inputs',
    'literature_partner_source_fields','literature_partner_defined_units','literature_kinetic_inputs','literature_binding_visual_inputs',
    'literature_binding_reader','literature_controlled_response_calculations','literature_controlled_response_inputs',
    'literature_controlled_response_figure_inputs','literature_controlled_response_owner_calculations','literature_controlled_response_v2_inputs']
tests=['test_literature_controlled_response'+suffix+'.py' for suffix in ('_inputs','_v2_inputs','_figure_inputs','_owner_calculations','_calculations')]
files=['gene_annotation_episode/'+name+'.py' for name in modules]+['tests/'+name for name in tests]+['pyproject.toml']
contracts={
 'a105_controlled_full_source_design_069':['CONSTRUCTED_SOURCE_CASES_001.json','CONSTRUCTED_SOURCE_ROSTER_001.json','CONSTRUCTED_GRAPH_001.png','SELECTION_SCHEMA_V2_001.json','EXTRACTION_SCHEMA_V2_001.json'],
 'a105_controlled_graph_design_061':['SELECTION_SCHEMA_V2_001.json','GRAPH_REQUEST_SCHEMA_001.json','GRAPH_RESULT_SCHEMA_002.json','COUNT_RESULT_SCHEMA_002.json'],
 'a105_controlled_adapter_design_065':['OWNER_INPUT_SCHEMA_004.json','OWNER_OUTPUT_SCHEMA_004.json','OWNER_SHAPE_EXAMPLES_004.json','ACTIVE_UNKNOWN_OWNER_CASE_006.json'],
 'a105_controlled_response_design_056/reader_stage_007':['COMPATIBILITY_RECEIPT_007.json','SOURCE_TEXT_007.txt','SELECTION_SCHEMA_007.json'],
 'a105_controlled_response_design_056/implementation_stage_008/final_snapshot_008/gene_annotation_episode':['literature_controlled_response_inputs.py']}
for directory,names in contracts.items():
    files += [str((BASE/directory/name).relative_to(ROOT)) for name in names]
for name in files:
    dest=PIN/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
put(HERE/'PIN_MANIFEST_001.json',{name:fp(PIN/name) for name in files})
put(HERE/'ENVIRONMENT_001.json',dict(python=sys.version,executable=sys.executable,executable_identity=fp(Path(sys.executable).resolve()),
    packages={name:importlib.metadata.version(name) for name in ('pytest','jsonschema','Pillow')},platform=sys.platform))
old=BASE/'a105_controlled_response_design_056/implementation_stage_008/PIN_MANIFEST_008.json'
legacy=json.loads(old.read_text())['original_files']
comparisons=[]
for name in ['gene_annotation_episode/'+n+'.py' for n in modules if n not in ('literature_controlled_response_inputs','literature_controlled_response_v2_inputs','literature_controlled_response_owner_calculations','literature_controlled_response_figure_inputs')]:
    actual=fp(ROOT/name);expected=legacy.get(name)
    comparisons.append(dict(path=name,actual=actual,original008=expected,equal=expected is not None and actual['sha256']==expected['sha256']))
put(HERE/'LEGACY_DEPENDENCY_COMPARISON_001.json',dict(scope='Read-only current-versus-original008 comparison; domain.py outside-owner drift is retained, no pin rewrite',comparisons=comparisons))
owned=['gene_annotation_episode/literature_controlled_response_inputs.py','gene_annotation_episode/literature_controlled_response_v2_inputs.py','tests/test_literature_controlled_response_v2_inputs.py']
patch=[]
for name in owned:
    before=(HERE/'before_001'/name).read_text().splitlines(keepends=True) if (HERE/'before_001'/name).exists() else []
    patch.extend(difflib.unified_diff(before,(ROOT/name).read_text().splitlines(keepends=True),fromfile='a/'+name if before else '/dev/null',tofile='b/'+name))
(HERE/'IMPLEMENTATION_001.patch').write_text(''.join(patch))
put(HERE/'PRODUCTION_FREEZE_001.json',dict(files={name:fp(ROOT/name) for name in owned},owner076=fp(ROOT/'gene_annotation_episode/literature_controlled_response_owner_calculations.py'),
    declared_only_owned_files=True,no_git_baseline=True))
print(json.dumps(dict(pin_files=len(files),production={name:fp(ROOT/name)['sha256'] for name in owned})))
