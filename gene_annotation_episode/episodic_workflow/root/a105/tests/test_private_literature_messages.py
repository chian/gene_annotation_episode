"""Original child identities and delivery replay select private counterparts."""
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace

import pytest

from .test_private_literature_bindings import AXIS, HOMES
from gene_annotation_episode.episodic_workflow.root.a105 import runtime

NAMES = {'literature_strategy':'evidence_search_strategy_improvement',
         'literature_search':'source_relevance_assessment', 'literature_page':'source_evidence_examination',
         'literature_table':'table_evidence_extraction', 'literature_ordered':'source_coverage_improvement',
         'literature_targeted':'passage_evidence_extraction'}
CASES = []
for home in HOMES:
    cls = import_module(f'{AXIS}.{home}.episode').LiteratureEpisode
    value = cls(object())
    CASES.extend((home, role) for role in value.child_roles(value.roles[0]))


@pytest.mark.parametrize('home,role', CASES)
def test_original_assignment_request_is_preserved(home, role):
    binding = import_module(f'{AXIS}.{home}.episode').LiteratureEpisode(object())
    page = {'source_ref':'original-source','artifact_ref':'original-artifact','representation':'original'}
    parent = SimpleNamespace(role=binding.roles[0], assignment=page)
    assignment = {'page':page, 'selection':{'question':'Resolve actual experiment and qualifications'},
                  'requested_assay_grading_components':[]}
    original = deepcopy(assignment)
    send = getattr(binding, 'prepare_child_request', lambda parent, role, value: deepcopy(value))
    sent = send(parent, role, assignment)
    assert sent == original and assignment == original
    assert sent is not assignment


@pytest.mark.parametrize('home,role', CASES)
@pytest.mark.parametrize('redelivery', [False,True])
def test_runtime_receipt_uses_saved_original_child(home, role, redelivery, monkeypatch):
    binding = import_module(f'{AXIS}.{home}.episode').LiteratureEpisode(object())
    seen, receipts = [], []
    receiver = 'receive_'+NAMES[role] if hasattr(binding,'receive_child_result') else 'received_form_references'
    setattr(binding, receiver, lambda *args: seen.append(args) or ['original-saved-finding'])
    context=SimpleNamespace(role=binding.roles[0])
    source=SimpleNamespace(episode_id='parent',scope={},path=((binding.roles[0],'parent'),))
    from gene_annotation_episode.episodic_workflow.root.a105.episode_return_records import EpisodeReturnRecords
    monkeypatch.setattr(EpisodeReturnRecords, 'recorded_admission_references', lambda *args: None)
    workflow=SimpleNamespace(receipts=SimpleNamespace(receive=lambda *args,**kwargs:receipts.append((args,kwargs))),
        is_job_source=lambda source:False,progress_provider=None,
        store=SimpleNamespace(get=lambda ref:None, db=SimpleNamespace(execute=lambda *args:SimpleNamespace(fetchone=lambda:None))),
        specialist=lambda source:binding,binding_context=lambda source:context,
        episode_bindings=SimpleNamespace(received_form_references=lambda *args:binding.received_form_references(*args)),
        journal=SimpleNamespace(row=lambda *args:{'action':json.dumps({'kind':'episode_child','role':role})}),
        run_id='message',native_timing_information=None)
    monkeypatch.setattr(runtime,'_references_in',lambda *args,**kwargs:[])
    assert runtime.Workflow._receive_form(workflow,source,{}, {},9,redelivery=redelivery)==['original-saved-finding']
    assert seen==[(context,{}, {},'message:parent:9:typed_form')]
    assert receipts[0][1]=={'kind':'report_redelivery' if redelivery else 'child_form','source_index':9}
