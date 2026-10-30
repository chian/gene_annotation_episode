"""Repair only001's final harness scope conversion; reuse selected state."""
from pathlib import Path
import hashlib
import json
import os
import sys
from types import SimpleNamespace

OWN=Path(__file__).resolve().parent;REPO=OWN.parents[1]
PIN=REPO/'verification/literature_reference_evidence_2026-10-25_001/a105_summary_precision_integration_review_256/joined_pin_008'
sys.dont_write_bytecode=True
sys.path[:]=[str(PIN),str(PIN/'tests'),*[p for p in sys.path if p and Path(p).resolve() not in (OWN,REPO)]]
os.chdir(PIN)
from test_literature_kinetic_summary_precision_binding_251 import block_science,forbid
from test_literature_compiled_assay_185 import readonly
from gene_annotation_episode.communication import validate_form,reference_resolver
from gene_annotation_episode.literature_kinetic_summary_precision_storage import NAMESPACE
from gene_annotation_episode.episode_bindings import BindingContext,EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.episode_composition import compose_episode_bindings
import gene_annotation_episode.communication as communication
from gene_annotation_episode import literature_kinetic_storage as nstorage
import pytest

def read(name):return json.loads((OWN/name).read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashes(root):return {str(p.relative_to(root)):digest(p) for p in root.rglob('*') if p.is_file()}
state=OWN/'joint_existing_boundary_001/state'
original=read('ADMITTED_JOINT_FORM_001.json');schema=read('ORIGINAL_SCHEMA_001.json')
descriptors=read('ORIGINAL_DESCRIPTOR_001.json');ns=read('ORIGINAL_NATIVE_SHEET_001.json');ss=read('ORIGINAL_PRECISION_SHEET_001.json')
nr=original['native_parameter'][0]['sheet_ref'];sr=original['precision'][0]['sheet_ref']
before=hashes(state);mp=pytest.MonkeyPatch()
try:
    block_science(mp);mp.setattr(nstorage,'read_kinetic_inputs',forbid);mp.setattr(nstorage,'populate_kinetic_contrast',forbid)
    communication._compiled_schema_content.cache_clear()
    with readonly(state) as cold:
        run_id,parent=cold.db.execute('SELECT run_id,episode_id FROM literature_kinetic_summary_precision_received ORDER BY rowid DESC LIMIT 1').fetchone()
        rootrow=cold.db.execute('SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?',(run_id,parent)).fetchone()
        request=json.loads(rootrow['request']);path=json.loads(rootrow['path']);scope=request['message']['scope']
        allowed={cold.get(ref)[key] for ref in (nr,sr) for key in ('artifact_ref','request_ref')}
        get=cold.get_artifact
        def saved_only(ref):
            assert ref in allowed,'Original source/science bytes forbidden in cold read'
            return get(ref)
        mp.setattr(cold,'get_artifact',saved_only)
        host=SimpleNamespace(store=cold,run_id=run_id,tools=None)
        restored=compose_episode_bindings(WorkflowServices(host),store=cold,journal=SimpleNamespace(store=cold,run_id=run_id),
            execution_backend=None,descriptors=descriptors,job_episodes=None,resource_estimator=None,role_credit_bindings={})
        host.episode_bindings=EpisodeBindingRegistry(restored.bindings);binding,=restored.bindings
        receiver=BindingContext(run_id,parent,path[-1][0],tuple(map(tuple,path)),scope,request['message'].get('episode_assignment',{}),request,
            tuple(dict.fromkeys([nr,sr,*ss['input_source_refs'],*ns['input_source_refs']])))
        assert binding.as_record()==descriptors[0]
        facts=binding.received_report_facts(receiver)
        assert facts[NAMESPACE]==original['precision'] and facts['literature_kinetic_cells']==original['native_parameter']
        assert binding.services.literature_kinetic_repository().read(nr)==ns
        assert binding._summary_precision_repository().read(sr)==ss
        validate_form(original,schema,reference_resolver(cold.references(scope)))
        assert cold.db.total_changes==0
        observations=cold.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
        actions=cold.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]
        assert observations==actions==4
    assert before==hashes(state)
    pin_before=read('PIN_INPUT_HASHES_001.json')
    assert pin_before=={str(p.relative_to(PIN)):digest(p) for p in PIN.rglob('*') if p.is_file() and p.name!='GOAL.md'}
    imported=[]
    for name,module in sorted(sys.modules.items()):
        file=getattr(module,'__file__',None)
        if not file:continue
        p=Path(file).resolve()
        if not p.is_file():continue
        if name.startswith(('gene_annotation_episode','method_loop','test_')):assert p.is_relative_to(PIN),(name,str(p))
        imported.append({'module':name,'path':str(p),'sha256':digest(p)})
    (OWN/'ACTUAL_COLD_IMPORTS_002.json').write_text(json.dumps(imported,indent=2)+'\n')
    result={'status':'passed','selected_execution':'joint_existing_boundary_001','cold_repair':'scope converted to original plain saved request scope; no scientific path rerun',
        'controlled_responses':True,'actual_model_backed_science':False,'pin':str(PIN),'pin_unchanged':True,
        'actions':actions,'observations':observations,'native_selected_operations':1,'summary_selected_operations':1,'new_assembly_operations':0,
        'ordinary_two_family_admitted_form':True,'same_original_kinetic_selection':ns['selection']==ss['extraction']['selection']['kinetic_selection'],
        'same_reported_parameter_anchor':'verified before001 cold step; saved original inputs retained',
        'independent_verifications_inferred':False,'cold_first_composer':True,'cold_source_io':False,'cold_scientific_calculation':False,
        'cold_writes':0,'cold_state_byte_identical':True,'imported_modules':len(imported),
        'limits':['current native schema factory remains available for exact legacy form grammar validation',
            'cold final reference validation uses existing scoped registry; original admission used ordinary runtime resolver',
            'new reusable worksheet template and semantic link validation remain proposed, not implemented']}
    (OWN/'JOINT_BOUNDARY_RESULT_002.json').write_text(json.dumps(result,indent=2)+'\n')
finally:mp.undo()
