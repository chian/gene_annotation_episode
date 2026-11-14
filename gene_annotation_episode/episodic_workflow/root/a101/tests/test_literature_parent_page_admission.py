"""Reader children retain the parent's exact source and artifact admission."""
from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace

import pytest
from .test_literature_private_boundaries import PACKAGE, HOMES

READERS=[home for home in HOMES if home.endswith(('table_evidence_extraction','source_coverage_improvement','passage_evidence_extraction'))]


@pytest.mark.parametrize('home',READERS)
@pytest.mark.parametrize('conflicting_parent',[False,True])
def test_reader_admits_original_parent_page_before_inheriting_source(home,conflicting_parent):
    source='source_'+'a'*32
    artifact='artifact_'+'b'*32
    other='artifact_'+'c'*32
    records={source:{'record_type':'source','artifact_ref':artifact,'parent_source_refs':[]},
             artifact:{'record_type':'artifact','size':64},other:{'record_type':'artifact','size':64}}
    services=SimpleNamespace(reference_in_scope=lambda ref,scope,namespace:ref in records,
                             read_record=records.__getitem__)
    binding=import_module(PACKAGE+'.'+home.replace('/','.')+'.episode').LiteratureEpisode(services)
    role,=binding.roles
    page={'version':'page_assignment_v1','source_ref':source,'representation':'original',
          'artifact_ref':artifact,'question_context_refs':[],'prior_delivery_refs':[]}
    window={'source_ref':source,'representation':'original','offset':0,'limit':32}
    selection={'version':'reading_assignment_v1','page':deepcopy(page),
               'selection':{'spans':[window]} if role=='literature_targeted' else window}
    parent=SimpleNamespace(role='literature_page',assignment=deepcopy(page),scope={},
                           path=(('literature_page','original-page'),))
    if conflicting_parent:
        parent.assignment['artifact_ref']=other
        with pytest.raises(import_module(PACKAGE+'.domain').ContractError,match='literature_source_artifact_mismatch'):
            binding.prepare_assignment(parent,role,selection,{},'original-reader')
    else:
        assert binding.prepare_assignment(parent,role,selection,{},'original-reader')==selection
