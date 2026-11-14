"""Actual private conditional bodies retain original job evaluation and effects.

These controls execute isolated original/selected statements with explicitly
controlled ports. They launch no scientific action and make no restoration claim.
"""
from __future__ import annotations
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT=Path(__file__).resolve().parents[2]
FIXTURES=Path(__file__).with_name('fixtures')/'homology_selected_job_branches'
MANIFEST=json.loads((FIXTURES/'manifest.json').read_text())

def selected(tree):
    call=next(n for n in ast.walk(tree) if isinstance(n,ast.AsyncFunctionDef) and n.name=='call')
    own=[n for n in ast.walk(call) if isinstance(n,ast.If) and ast.unparse(n.test)=='self.workflow.is_job_source(self)']
    receipts=[n for n in ast.walk(call) if isinstance(n,ast.If) and ast.unparse(n.test)=='self.workflow.receipts is not None and (not self.workflow.is_job_source(self)) and (not self.workflow.uses_received_record_context(self))']
    assert len(own)==1 and len(receipts)==2
    return [own[0],*receipts]

@pytest.mark.parametrize('case',MANIFEST['homes'],ids=lambda case:case['home'])
@pytest.mark.parametrize('branch',(0,1,2),ids=('own_estimator','fresh_receipt_guard','protocol_receipt_guard'))
@pytest.mark.parametrize('scenario',('ordinary','missing_receipts','failed_own_estimator','receipt_property_error'))
def test_selected_job_branch_retains_original_observation(case,branch,scenario):
    original=(FIXTURES/case['fixture']).read_bytes()
    assert hashlib.sha256(original).hexdigest()==case['original_sha256']
    current=(ROOT/case['home']/'task_decision.py').read_bytes()
    before=selected(ast.parse(original))[branch];after=selected(ast.parse(current))[branch]
    assert ast.dump(before.test,include_attributes=False)==ast.dump(after.test,include_attributes=False)
    observations=[]
    for statement in (before,after):
        events=[]
        class Workflow:
            @property
            def receipts(self):
                events.append(('receipts',))
                if scenario=='receipt_property_error':raise OSError('controlled_receipt_access')
                return None if scenario=='missing_receipts' else SimpleNamespace(receive=lambda *a,**k:events.append(('forbidden_receive',)))
            def is_job_source(self,source):
                events.append(('is_job_source',source.path))
                return self.job_episodes is not None and source.path[-1][0] in self.job_episodes.roles
            def uses_received_record_context(self,source):
                events.append(('forbidden_received_context',));raise AssertionError('unreached_nonjob_context')
        workflow=Workflow();workflow.job_episodes=SimpleNamespace(roles=tuple(MANIFEST['roles']))
        def assignment(source):events.append(('assignment',source.path));return {'job_ref':'job_original'}
        def sample(source,*,include_inherited):events.append(('sample',include_inherited));return {'original':'sample'}
        def estimate(expectations,*,job_ref,sample):
            events.append(('estimate',deepcopy(expectations),job_ref,deepcopy(sample)))
            if scenario=='failed_own_estimator':raise ValueError('controlled_estimator_failure')
            return [{'estimate':'original'}]
        workflow.job_episodes.assignment=assignment;workflow.job_episodes.latest_sample=sample
        workflow.resource_estimator=SimpleNamespace(estimate=estimate,
            estimate_context=lambda value:events.append(('forbidden_nonjob_estimator',)))
        source=SimpleNamespace(workflow=workflow,path=((case['parent'],'root'),(case['role'],'child')),episode_id='actual_episode')
        scope={'self':source,'context':{'execution_expectations':{'original':'expectations'},'visible_record_refs':['record_original']},'index':3}
        try:
            module=ast.fix_missing_locations(ast.Module(body=[deepcopy(statement)],type_ignores=[]))
            exec(compile(module,'<actual-private-conditional>','exec'),{},scope)
            outcome=('returned',scope.get('estimates'))
        except Exception as error:outcome=('raised',type(error),str(error))
        observations.append((outcome,events))
    assert observations[0]==observations[1]
    assert not any(event[0].startswith('forbidden_') for event in observations[1][1])

