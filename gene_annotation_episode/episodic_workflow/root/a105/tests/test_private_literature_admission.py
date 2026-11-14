"""Reading children authenticate their original source parent's page after role specialization."""
from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace
import pytest
from .test_private_literature_bindings import AXIS,HOMES
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError

READERS=[home for home in HOMES if import_module(AXIS+'.'+home+'.episode').LiteratureEpisode.roles[0]
         in {'literature_table','literature_ordered','literature_targeted'}]
SOURCE='source_'+'a'*64
ARTIFACT='artifact_'+'b'*64

@pytest.fixture(params=READERS)
def admission(request):
    cls=import_module(AXIS+'.'+request.param+'.episode').LiteratureEpisode
    records={SOURCE:{'record_type':'source','artifact_ref':ARTIFACT,'text_ref':ARTIFACT},
             ARTIFACT:{'record_type':'artifact','size':20}}
    services=SimpleNamespace(reference_in_scope=lambda ref,scope,namespace:ref in records and
        (namespace is None or records[ref]['record_type']==namespace),read_record=records.__getitem__)
    binding=cls(services)
    page={'version':'page_assignment_v1','source_ref':SOURCE,'artifact_ref':ARTIFACT,
          'representation':'original','question_context_refs':[],'prior_delivery_refs':[]}
    window={'source_ref':SOURCE,'representation':'original','offset':0,'limit':4}
    assignment={'version':'reading_assignment_v1','page':deepcopy(page),
        'selection':{'spans':[window]} if binding.roles[0]=='literature_targeted' else window}
    return binding,SimpleNamespace(role='literature_page',assignment=page,scope={}),assignment


def test_reading_admission_authenticates_parent_and_keeps_native_selector(admission):
    binding,parent,assignment=admission
    assert binding.prepare_assignment(parent,binding.roles[0],assignment,{},'original-commission')==assignment


def test_reading_admission_rejects_changed_parent_artifact(admission):
    binding,parent,assignment=admission
    parent.assignment['artifact_ref']='artifact_'+'c'*64
    with pytest.raises(ContractError,match='source_artifact_mismatch'):
        binding.prepare_assignment(parent,binding.roles[0],assignment,{},'original-commission')


def test_reading_admission_rejects_selector_outside_source(admission):
    binding,parent,assignment=admission
    window=assignment['selection'].get('spans',[assignment['selection']])[0]
    window['source_ref']='source_'+'d'*64
    with pytest.raises(ContractError,match='reading_source_mismatch'):
        binding.prepare_assignment(parent,binding.roles[0],assignment,{},'original-commission')
