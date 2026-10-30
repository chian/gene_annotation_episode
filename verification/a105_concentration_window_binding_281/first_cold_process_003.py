"""First fresh-process reconstruction; original receipt reads only."""
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_literature_concentration_window_binding_281 import block_science,forbid
from test_literature_compiled_assay_185 import readonly
from gene_annotation_episode.communication import validate_form,_compiled_schema_content
from gene_annotation_episode.episode_bindings import BindingContext,EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_concentration_window_storage import NAMESPACE,LiteratureConcentrationWindowRepository
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_concentration_window_prompt import CONCENTRATION_WINDOW_TASK

CASE=Path(sys.argv[1]).resolve()
def load(name):return json.loads((CASE/name).read_text())
form=load('ORIGINAL_FORM_281.json');schema=load('ORIGINAL_SCHEMA_281.json');descriptors=load('ORIGINAL_DESCRIPTOR_281.json')
data=load('ORIGINAL_RECEIVER_281.json');allowed=set(load('ORIGINAL_ARTIFACTS_281.json'))
before={str(p.relative_to(CASE/'state')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (CASE/'state').rglob('*') if p.is_file()}
patch=pytest.MonkeyPatch();block_science(patch);_compiled_schema_content.cache_clear()
context=BindingContext(**data,received_record_refs=tuple(LiteratureConcentrationWindowRepository.cell_record_refs(form['window'])))
reads=[]
with readonly(CASE/'state') as store:
    get=store.get_artifact
    def saved_only(ref):
        assert ref in allowed,'Scientific source bytes forbidden';reads.append(ref);return get(ref)
    patch.setattr(store,'get_artifact',saved_only)
    for name in ('artifact','put','create_problem'):patch.setattr(store,name,forbid)
    host=SimpleNamespace(store=store,run_id=context.run_id,tools=None)
    restored=compose_episode_bindings(WorkflowServices(host),store=store,journal=SimpleNamespace(store=store,run_id=context.run_id),
        execution_backend=None,descriptors=descriptors,job_episodes=None,resource_estimator=None,role_credit_bindings={})
    host.episode_bindings=EpisodeBindingRegistry(restored.bindings);binding,=restored.bindings
    assert binding.as_record()==descriptors[0]
    received=binding.received_report_facts(context)[NAMESPACE];assert received==form['window']
    saved=binding._concentration_window_repository().read(form['window'][0]['sheet_ref']);assert saved==load('ORIGINAL_SAVED_281.json')
    validate_form(form,schema,lambda reference,namespace:True)
    parent_state=dict(literature_experimental_work=dict(version='literature_experimental_task_v1',aspect='reference_evidence_parent'),
        reference_evidence_parent=dict(version='reference_evidence_parent_v1',source_refs=[received[0]['evidence_source_ref']]),
        child_reports=[form],goal=dict(objective='Use the received reference evidence for the assigned source question.'),scope=data['scope'],working_state={})
    prompt=render_literature_experimental_prompt(parent_state,'Preserve the caller source-evidence task.')
    assert CONCENTRATION_WINDOW_TASK in prompt and 'A105 experimental evidence worksheet' in prompt and 'Preserve the caller source-evidence task.' in prompt
    assert 'matrix_exact' not in prompt and 'concentration_window_return_v1' not in prompt
    assert store.db.total_changes==0
after={str(p.relative_to(CASE/'state')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (CASE/'state').rglob('*') if p.is_file()}
assert before==after
record=dict(pid=os.getpid(),fresh_process=True,requested_rows=len(form['window']),
    source_science_current_factories_projection_receive_model_writes_blocked_before_constructor=True,
    only_original_receipt_artifacts_read=set(reads)==allowed,receipt_artifact_count=len(allowed),
    state_byte_hashes_unchanged=before==after,sqlite_changes=0,receiving_prompt_rendered_without_factories=True,
    scope='Controlled engineering choices; mechanically reused converted source; no configured-model claim.')
(CASE/'FRESH_COLD_PROCESS_281.json').write_text(json.dumps(record,indent=2)+'\n')
(CASE/'FRESH_COLD_RECEIVING_PROMPT_281.txt').write_text(prompt)
print(json.dumps(record))
