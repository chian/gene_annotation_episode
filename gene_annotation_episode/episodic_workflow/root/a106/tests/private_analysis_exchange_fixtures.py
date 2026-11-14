"""Actual private analysis owners, with explicit offline caller configuration."""
from functools import partial
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
import pytest

AXIS=__package__.rsplit('.tests',1)[0]
ROOT=Path(__file__).resolve().parents[1]

def module(name):
    return import_module(AXIS+'.'+name)


@pytest.fixture(scope='module')
def analysis_workflow(tmp_path_factory):
    directory=tmp_path_factory.mktemp('original-private-analysis-exchanges')
    with module('state').Store(directory/'state') as store:
        store.create_problem(raw_sequence='ATGGCT',molecule='dna')
        tools=module('tools').ToolRegistry(store)
        library=module('scientific_process_library').ScientificProcessLibrary.freeze(
            directory/'scientific-process-library',source=ROOT.parents[3]/'research/slotted_process_library')
        tool_library=module('scientific_tool_library').ScientificToolLibrary.freeze(
            directory/'scientific-tool-library',catalog=tools.catalog())
        factories=[partial(module('scientific_process.episode').ScientificProcessEpisode,
            library=library,tool_library=tool_library,
            child_roles=('scientific_process','literature','launch','results'))]
        configuration=dict(store=store,directory=directory,run_id='private-analysis-exchanges',
            resources={'original-api':{'kind':'api','service':'bvbrc_appservice',
                'execution_contract':'bvbrc_appservice_execution_v1',
                'endpoints':{'AppService':'https://offline.invalid/app','Workspace':'https://offline.invalid/workspace'},
                'scientific_adapters':[]}},initial_information={'original-api':{'inventory':'original-caller'}},
            tool_registry=tools,handoff_unit=2,acquired_record_unit=3,log_window_bytes=128,log_roles=('stdout','stderr'))
        for parent in ('','scientific_process.'):
            literature=parent+'published_evidence_assessment'
            strategy=literature+'.evidence_search_strategy_improvement'
            search=strategy+'.source_relevance_assessment'
            page=search+'.source_evidence_examination'
            homes=(literature,strategy,search,page,page+'.table_evidence_extraction',
                page+'.source_coverage_improvement',page+'.passage_evidence_extraction')
            factories.extend(module(home+'.episode').LiteratureEpisode for home in homes)
            for prefix in (parent,literature+'.'):
                for home in ('execution_job_submission','execution_job_submission.api_job_execution','execution_result_acquisition'):
                    factories.append(partial(module(prefix+home+'.episode').ExecutionEpisode,**configuration))
        def unselected(*args,**kwargs):
            raise AssertionError('Offline exchanges must not select a provider or native job')
        workflow=module('runtime').Workflow(store,tools,SimpleNamespace(complete=unselected),
            directory,configuration['run_id'],unselected,unselected,
            episode_binding_factories=tuple(factories),
            annotation_child_roles=('scientific_process','literature','launch','results'))
        yield store,workflow,configuration
        assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0]==0
        assert store.db.execute('SELECT COUNT(*) FROM runtime_model_calls').fetchone()[0]==0


def api_assignment():
    return {'version':'api_service_assignment_v1','resource_id':'original-api','service':'bvbrc_appservice',
        'endpoint':'usable_handoff','constraints':{},'request':{
            'version':'bvbrc_appservice_request_v1','effect_contract':'selected_api_effects_v1',
            'required_application_id':'RNASeq','parameters':{},'start_parameters':{},
            'definition_inputs':[],'input_bindings':[],'workspace_targets':[]}}


def launch_assignment():
    return {'version':'execution_launch_assignment_v1','requests':{'original-api':api_assignment()},
        'immutable_input_versions':[],'constraints':{'allowed_kinds':['api']}}


def refs_schema():
    return {'type':'object','properties':{'refs':{'type':'array','items':{'type':'string','format':'reference',
        'x-reference-namespace':'artifact'},'x-source':'committed_record_refs'}},'required':['refs'],'additionalProperties':False}


def results_assignment(handoff):
    return {'version':'execution_results_assignment_v1','handoff_ref':handoff,'selector':{
        'version':'bvbrc_appservice_result_selector_v1','endpoint':'requested_artifacts',
        'requirements':[{'requirement_id':'native','role':'native_output','required':True,
            'declared_format':{'format':'json','version':None,'mode':None,'producer_source_ref':None,'transformation_evidence':[]},
            'producer_rule_evidence':None,'exact_object':None}],
        'adapter':None,'requested_schema':refs_schema(),'supplied_metadata':[],'supplied_capabilities':[]}}
