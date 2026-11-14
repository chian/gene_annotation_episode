"""Actual private constructors and controlled selected assessment/scoring ports."""
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
import pytest

AXIS=__package__.rsplit('.tests',1)[0]
ROOT=Path(__file__).resolve().parents[1]
HOMES=sorted(str(path.parent.relative_to(ROOT)) for path in ROOT.rglob('episode.py')
             if 'published_evidence_assessment' in path.parts and 'tests' not in path.parts and 'class LiteratureEpisode(' in path.read_text())

@pytest.fixture(params=HOMES)
def binding(request):
    cls=import_module(AXIS+'.'+request.param.replace('/','.')+'.episode').LiteratureEpisode
    return cls(SimpleNamespace(workflow=SimpleNamespace(store=object(),run_id='original-run')))


def test_optional_original_grading_policy_is_preserved(binding):
    assert binding._required_grading_repository(SimpleNamespace()) is None
    assert binding._required_grading_repository() is None


def test_unknown_source_namespace_retains_actual_contract_exception(binding):
    binding._population_routes=lambda context:()
    error=import_module(AXIS+'.domain').ContractError
    with pytest.raises(error,match='assay_grading_reader_namespace_unbound'):
        binding._intervention_source_cells(SimpleNamespace(),'unknown','original-sheet',['original-cell'])


def test_selected_assessment_reads_original_cells_and_checks_schema(binding):
    rows=[{'original_cell':'actual-original-value'}];calls=[]
    schema={'type':'array','items':{'type':'object','properties':{'original_cell':{'type':'string'}},'required':['original_cell'],'additionalProperties':False}}
    def fact_cells(context,refs,*,components):
        calls.append((context,refs,components));return rows
    binding._population_routes=lambda context:(('selected_cells','requested','provider',(),lambda:SimpleNamespace(fact_cells=fact_cells)),)
    binding._rate_fact_sources=lambda:{'selected_cells':{'report_schema':schema}}
    context=SimpleNamespace()
    assert binding._intervention_source_cells(context,'selected_cells','original-sheet',['original-cell']) is rows
    assert calls==[(context,['original-sheet'],['original-cell'])]


def test_automatic_judgments_keep_original_selection_and_failure(binding):
    calls=[];request=object();outcome={'status':'invalid','record_refs':[]}
    def prepare(context):calls.append(('prepare',context));return request
    def complete(context,reference,response,**kwargs):
        calls.append(('complete',context,reference,response,kwargs));return outcome
    binding._a106_subscore_repo=SimpleNamespace(prepare_judgments=prepare,complete_judgment=complete)
    context=SimpleNamespace();provenance={'provider':'original'}
    assert binding.automatic_score_judgments(context) is request
    assert binding.complete_score_judgment(context,'original-judgment',None,provenance=provenance,failure='unavailable') is outcome
    assert calls==[('prepare',context),('complete',context,'original-judgment',None,{'provenance':provenance,'failure':'unavailable'})]
