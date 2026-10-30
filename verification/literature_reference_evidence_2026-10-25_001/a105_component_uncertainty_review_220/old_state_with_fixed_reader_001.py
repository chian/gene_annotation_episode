"""Read original pre-fix saved v1/v2 sheets with fixed frozen code; no science."""
from pathlib import Path
import hashlib
import json
import os
import sys

BASE=Path(__file__).resolve().parent
PIN=BASE/'pin_002'
sys.dont_write_bytecode=True
sys.path[:0]=[str(PIN),str(PIN/'tests')]
from test_literature_compiled_assay_185 import readonly
from gene_annotation_episode.literature_compiled_assay_storage import LiteratureCompiledAssayRepository
import gene_annotation_episode.literature_compiled_assay_inputs as inputs
import gene_annotation_episode.literature_compiled_assay_calculations as calculations

proof=Path(json.loads((BASE/'ROOT_COLD_PROOF_001.json').read_text())['proof_path']).parent
state=proof/'state'
forms=json.loads((proof/'ORIGINAL_MIXED_FORM_001.json').read_text())
expected=json.loads((proof/'SAVED_SHEETS_001.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p.relative_to(state)):sha(p) for p in state.rglob('*') if p.is_file()}
def forbid(*args,**kwargs):raise AssertionError('cold source/parser/calculator work is forbidden')
inputs.read_compiled_assay_inputs=forbid
inputs._covariance_v2=forbid
calculations.populate_compiled_assay=forbid
calculations._populate_v2=forbid
LiteratureCompiledAssayRepository.receive_cells=forbid
with readonly(state) as cold:
    run_id,=cold.db.execute('SELECT run_id FROM runtime_runs').fetchone()
    allowed={cold.get(forms[field][0]['sheet_ref'])[name]
        for field in ('old','new') for name in ('artifact_ref','request_ref')}
    original_get=cold.get_artifact
    def saved_only(reference):
        assert reference in allowed,'original/upstream scientific artifacts are forbidden'
        return original_get(reference)
    cold.get_artifact=saved_only
    actual=[LiteratureCompiledAssayRepository(cold,run_id,version).read(forms[field][0]['sheet_ref'])
        for version,field in ((1,'old'),(2,'new'))]
    assert actual==expected and cold.db.total_changes==0
    assert cold.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==8
assert before=={str(p.relative_to(state)):sha(p) for p in state.rglob('*') if p.is_file()}
hashes=json.loads((BASE/'PIN_002.json').read_text())['hashes']
changed=[p for p,h in hashes.items() if sha(PIN/p)!=h]
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
    if getattr(m,'__file__',None) and n.startswith(('gene_annotation_episode','method_loop','test_'))}
outside={n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)}
assert not changed and not outside
result={'old_pre_fix_sheets_equal_with_fixed_reader':True,'versions':[1,2],
    'source_and_calculators_blocked':True,'receive_blocked':True,
    'changed_rows':0,'observations_unchanged':8,'state_hashes_unchanged':True,
    'imports_outside_pin':outside,'changed_pinned_files':changed,
    'scope':'Original controlled pre-fix v1/v2 saved sheets read directly with fixed pin002; not a new model or whole-worker replay claim.'}
with (BASE/'ROOT_OLD_STATE_FIXED_READER_001.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
