"""Reviewable constructed-only selected-path and parent-presentation evidence."""
import asyncio,hashlib,json,sqlite3
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import pytest
import test_literature_perturbation_covariance_meanings as cases
from gene_annotation_episode.communication import plain
BASE=Path(__file__).resolve().parent
PIN=BASE/'pin_003'
assert Path(cases.__file__).resolve().is_relative_to(PIN)
ART=BASE/'CURRENT_GENERATION_EVIDENCE_001'
ART.mkdir()
results={}
for kind,basis in [('mean_covariance','source_reported'),('uncorrelated','conditional_assumption'),('paired_units','source_supported_inference')]:
 store,context,binding,outcome,schema,form=cases.selected(ART/kind,kind,basis)
 try:
  parent=replace(context,role='annotation',episode_id='covariance-parent',assignment={},path=(('annotation','root'),))
  binding.received_form_references(parent,form,schema,'covariance-admission')
  parent_text=cases._steering({'child_reports':[form],**binding._received_fact_display_context(parent)},())
  own_text=cases._steering({'last_local_outcome':outcome,**binding._received_fact_display_context(context)},())
  assert kind in parent_text and basis in parent_text and '987654321' not in parent_text and '0.000000000000000000' not in parent_text
  (ART/(kind+'_parent.txt')).write_text(parent_text)
  (ART/(kind+'_own.txt')).write_text(own_text)
  (ART/(kind+'_form.json')).write_text(json.dumps(plain(form),indent=2)+'\n')
  row,=form['measurements']; results[kind]={'variance':row['value'],'qualifiers':plain(row['covariance_interpretations']),'parent_text_sha256':hashlib.sha256(parent_text.encode()).hexdigest(),'own_text_sha256':hashlib.sha256(own_text.encode()).hexdigest()}
 finally:store.close()
assert len({r['parent_text_sha256'] for r in results.values()})==3
captured=[]
original=cases._steering
def trace(inputs,*args,**kwargs):
 text=original(inputs,*args,**kwargs);captured.append({'inputs':plain(inputs),'text':text});return text
with pytest.MonkeyPatch.context() as monkeypatch,patch.object(cases,'_steering',trace):
 cases.test_ordinary_child_parent_and_first_read_only_reconstruction_keep_actual_covariance_meaning(ART/'ordinary',monkeypatch)
(ART/'ordinary_captured_prompts.json').write_text(json.dumps(captured,indent=2)+'\n')
db=sqlite3.connect((ART/'ordinary/state/state.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
observations=[dict(r) for r in db.execute('select * from runtime_observations')]
counts={table:db.execute('select count(*) from '+table).fetchone()[0] for table in ['runtime_observations','literature_perturbation_operations','literature_perturbation_summary_received']}
db.close();assert counts=={'runtime_observations':4,'literature_perturbation_operations':1,'literature_perturbation_summary_received':1}
(ART/'ordinary_observations.json').write_text(json.dumps(observations,indent=2)+'\n')
manifest=json.loads((BASE/'PIN_MANIFEST_003.json').read_text());changed=[n for n,h in manifest['files'].items() if hashlib.sha256((PIN/n).read_bytes()).hexdigest()!=h];assert not changed
result={'scope':'Constructed-only implementation evidence, scripted selections and sources, real production selected action, typed return, received parent and first source-free read-only reconstruction; no model or primary paper read','three_distinct_meanings':results,'ordinary_counts':counts,'ordinary_captured_views':len(captured),'pinned_files_checked':len(manifest['files']),'changed_pinned_files':changed}
(ART/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'three_distinct_meanings':list(results),'variance_values':[r['variance'] for r in results.values()],'ordinary_counts':counts,'ordinary_captured_views':len(captured),'changed_pinned_files':changed}))
