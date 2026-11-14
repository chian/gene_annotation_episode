"""Controlled retained-owner boundaries, with actual same-site before/after probes.

Metadata methods run on explicitly unconstructed passive catalog owners. The
constructor import-site probes execute only the exact current ImportFrom node,
not the full factory. Received authorities use a declared SQLite read fixture;
native hosts use a closed-interface observation fixture that supplies only
nonquiescent observations. No native worker, cgroup receipt, saved restoration,
scientific workflow, service acquisition or installation is performed here.
"""
from copy import deepcopy
import ast
import asyncio
from contextlib import contextmanager
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

AXIS='gene_annotation_episode.episodic_workflow.root.a107'
OWNER='library.received_execution_information.historical_receiving_owner'
TOOLS={
 'atac':('native_atac_differential','native_atac_differential_tool_info','library.atac_execution_contracts','validate_atac_bindings'),
 'chromatin':('native_chromatin_interactions','native_chromatin_interaction_tool_info','library.chromatin_request_contracts','validate_chromatin_bindings'),
 'genomic':('native_genomic_overlap','native_genomic_overlap_tool_info','library.received_execution_information.historical_native_genomic_overlap_contracts','validate_genomic_overlap_bindings'),
 'fluorescence':('native_fluorescence','native_fluorescence_tool_info','native_fluorescence_contracts','validate_fluorescence_bindings'),
 'protein':('native_protein_structure','native_protein_structure_tool_info','native_protein_structure_contracts','validate_protein_structure_bindings'),
}
FAMILIES={
 'atac':('AtacDifferentialReturns','NativeAtacDifferentialResults','atac_results','atac_differential_returns','native_atac_differential_results','atac_differential_result_selector_v1','library.atac_received_fact_contracts','atac_fact_sources','atac_differential_failures','atac_return_'),
 'chromatin':('ChromatinInteractionReturns','NativeChromatinInteractionResults','native_chromatin_interaction_results','chromatin_interaction_returns','native_chromatin_interaction_results','chromatin_interaction_result_selector_v1','library.chromatin_received_fact_contracts','chromatin_fact_sources','chromatin_interaction_failures','chromatin_return_'),
 'flux':('FluxBalanceReturns','NativeFluxBalanceResults','native_flux_balance_results','flux_balance_returns','native_flux_balance_results','flux_balance_result_selector_v1','library.flux_balance_received_fact_contracts','fba_fact_sources','flux_balance_failures','flux_balance_return_'),
 'genomic':('GenomicOverlapReturns','NativeGenomicOverlapResults','native_genomic_overlap_results','genomic_overlap_returns','native_genomic_overlap_results','genomic_overlap_result_selector_v1','library.genomic_overlap_received_fact_contracts','genomic_overlap_fact_sources','genomic_overlap_failures','genomic_overlap_return_'),
}


def module(name):return importlib.import_module(AXIS+'.'+name)


def metadata_owner():
    cls=module(OWNER).HistoricalReceivedExecutionOwner
    owner=cls.__new__(cls);owner.resources={};owner.api_execution=None
    for name in ('native_expression_nmf_results','native_flux_balance_results','atac_results',
        'native_chromatin_interaction_results','native_rna_structure_results','native_genomic_overlap_results',
        'rna_structure_comparison_results','native_blast_standard_database_results','native_blast_database_results',
        'native_hmmer_preparation_results','native_infernal_preparation_results','native_blast_results','native_infernal_results'):
        setattr(owner,name,None)
    return owner


def actual_request_schema(family,bindings):
    owner=metadata_owner();key=TOOLS[family][0]
    owner.resources={'declared':{'kind':'local',key:deepcopy(bindings)}}
    return owner._request_schema('declared',selected=True,compact=False)


def local_chromatin_empty():
    cls=module('library.received_execution_information.historical_local_assignment_validation').HistoricalLocalAssignmentValidation
    configuration={'kind':'local','workspace':'/declared/workspace',
        'policy':{'memory_bytes':5368709120,'scratch_bytes':1048576},'native_chromatin_interactions':[]}
    return cls(configuration).configuration


def original_fact_origin(family):
    owner=metadata_owner();setattr(owner,FAMILIES[family][2],object())
    schema=owner.fact_sources('results')['execution_result_origin']['report_schema']
    Draft202012Validator.check_schema(schema)
    return schema


def current_constructor_import(family,kind):
    """Execute the real current import site; explicitly not full construction."""
    defining=module(OWNER);path=Path(defining.__file__)
    tree=ast.parse(path.read_bytes());symbol=FAMILIES[family][0 if kind=='return' else 1]
    cls,=[node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='HistoricalReceivedExecutionOwner']
    init,=[node for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=='__init__']
    node,=[node for node in ast.walk(init) if isinstance(node,ast.ImportFrom)
        and any(alias.name==symbol for alias in node.names)]
    assert node.level==0 and len(node.names)==1 and node.names[0].asname is None
    isolated=ast.Module(body=[deepcopy(node)],type_ignores=[])
    namespace={'__builtins__':__builtins__}
    exec(compile(isolated,str(path),'exec',dont_inherit=True),namespace)
    return namespace[symbol]


def error_record(call):
    try:call()
    except Exception as error:
        return {'type':type(error).__module__+'.'+type(error).__qualname__,'message':str(error),
            'missing_module':getattr(error,'name',None)}
    raise AssertionError('expected original invalid operand to remain invalid')


@pytest.mark.parametrize('family',TOOLS)
def test_actual_tool_catalog_preserves_original_invalid_binding_error(family):
    direct=lambda:getattr(module(TOOLS[family][2]),TOOLS[family][3])([None])
    expected=error_record(direct)
    observed=error_record(lambda:actual_request_schema(family,[None]))
    assert observed==expected and observed['type'] not in {'builtins.ModuleNotFoundError','builtins.ImportError'}


def test_actual_empty_chromatin_catalog_has_no_executable_binding():
    value=local_chromatin_empty();assert value['native_chromatin_interactions']==[]
    assert value['policy']['memory_bytes']==5368709120


@pytest.mark.parametrize('family',['atac','flux'])
def test_actual_fact_catalog_preserves_historical_origin_qualifications(family):
    schema=original_fact_origin(family)
    cls=current_constructor_import(family,'host');owner=importlib.import_module(cls.__module__)
    assert Draft202012Validator(schema).is_valid(owner.ORIGIN)
    changed=deepcopy(owner.ORIGIN);changed['completion_basis']='invented_unqualified_success'
    assert not Draft202012Validator(schema).is_valid(changed)
    if family=='atac':assert Draft202012Validator(schema).is_valid(owner.SAVED_ORIGIN)


@contextmanager
def authority(family):
    """Actual constructor; only a declared, in-memory saved-facts read port."""
    connection=sqlite3.connect(':memory:');connection.row_factory=sqlite3.Row
    connection.execute('CREATE TABLE runtime_forms(run_id TEXT,episode_id TEXT,facts TEXT)')
    owner=SimpleNamespace(store=SimpleNamespace(db=connection),run_id='declared_fixture')
    setattr(owner,FAMILIES[family][2],None)
    try:yield current_constructor_import(family,'return')(owner),connection
    finally:connection.close()


@pytest.mark.parametrize('family',FAMILIES)
def test_original_return_authority_reuses_existing_base_and_preserves_order(family):
    cls=current_constructor_import(family,'return')
    assert issubclass(cls,module('episode_return_records').EpisodeReturnRecords)
    expected={'source':[{'number':1},{'number':2}]}
    assert cls._ordered_subset({'source':[{'number':2}]},expected)
    assert not cls._ordered_subset({'source':[{'number':2},{'number':1}]},expected)
    assert not cls._ordered_subset({'source':[{'number':1},{'number':1}]},expected)
    assert not cls._ordered_subset({'source':[{'number':True}]},expected)


@pytest.mark.parametrize('family',FAMILIES)
def test_saved_facts_require_exact_original_values_and_do_not_write(family):
    with authority(family) as (instance,connection):
        context=SimpleNamespace(episode_id='declared_episode')
        facts={'source':[{'measurement':None,'qualification':'unavailable'}]}
        assert instance._frozen(context,facts) is False
        connection.execute('INSERT INTO runtime_forms VALUES(?,?,?)',(instance.run_id,context.episode_id,json.dumps(facts)))
        before=connection.total_changes
        assert instance._frozen(context,deepcopy(facts)) is True
        with pytest.raises(ValueError,match='^'+FAMILIES[family][9]+'frozen_facts_conflict$'):
            instance._frozen(context,{'source':[{'measurement':0,'qualification':'available'}]})
        assert connection.total_changes==before
        assert json.loads(connection.execute('SELECT facts FROM runtime_forms').fetchone()[0])==facts


@pytest.mark.parametrize('family',FAMILIES)
def test_returned_empty_failure_collection_keeps_its_original_source(family):
    with authority(family) as (instance,_):
        row=FAMILIES[family];catalog=getattr(module(row[6]),row[7])()
        schema={'type':'object','properties':{'failures':deepcopy(catalog[row[8]]['report_schema'])},
            'required':['failures'],'additionalProperties':False}
        assert instance._values({'failures':[]},schema)=={row[8]:[]}
        with pytest.raises((ValueError,TypeError)):
            instance._values({'failures':None},schema)


def test_fba_actual_binding_type_and_original_report_descriptor_are_preserved():
    with authority('flux') as (instance,_):
        with pytest.raises(ValueError,match='^flux_balance_return_binding_context_required$'):
            instance.authenticate(SimpleNamespace())
        owner=module('bvbrc_appservice_custody').AppServiceCustody
        assert inspect.getattr_static(type(instance),'_report_contract').__func__ is inspect.getattr_static(owner,'_report_contract').__func__


class UnclosedWriterObservation:
    """Declared callback fixture, never a native/cgroup execution receipt."""
    def __init__(self,terminal,quiescent):
        self.value={'native':{'terminal':terminal,'quiescent':quiescent},'fixture':'controlled_nonquiescent_writer'}
        self.calls=[]
    def read_handoff(self,action):
        self.calls.append('read_handoff');return {'fixture':'declared_handoff_read_boundary'}
    def observation(self,action):
        self.calls.append('observation');return deepcopy(self.value)
    def __getattr__(self,name):
        raise AssertionError('closed-writer path must not acquire, publish, or launch: '+name)


def failed_writer_observation(family,terminal,quiescent,collecting):
    cls=current_constructor_import(family,'host');instance=cls.__new__(cls)
    instance.receipts=UnclosedWriterObservation(terminal,quiescent)
    instance.store=SimpleNamespace()
    receipt={'host_failures':[]}
    asyncio.run(instance._original(SimpleNamespace(),receipt,collecting=collecting))
    assert instance.receipts.calls==['read_handoff','observation']
    assert receipt['observation']==instance.receipts.value
    assert not {'capture','native','worker_plan','worker_execution','projection'}&receipt.keys()
    return receipt


@pytest.mark.parametrize('family',FAMILIES)
@pytest.mark.parametrize('terminal,quiescent',[(False,False),(True,False),(False,True)])
def test_original_open_writer_failure_remains_returned_without_worker_or_capture(family,terminal,quiescent):
    receipt=failed_writer_observation(family,terminal,quiescent,True)
    assert len(receipt['host_failures'])==1
    failure=receipt['host_failures'][0]
    assert failure['code']=={'atac':'input_unavailable','chromatin':'input_unavailable',
        'flux':'writer_not_closed','genomic':'native_output_unavailable'}[family]
    assert failure['stage']=='capture'


@pytest.mark.parametrize('family',FAMILIES)
def test_original_status_observation_does_not_turn_open_writer_into_collection(family):
    assert failed_writer_observation(family,False,False,False)['host_failures']==[]


@pytest.mark.parametrize('family',FAMILIES)
def test_original_host_selector_identity_remains_exact(family):
    cls=current_constructor_import(family,'host');instance=cls.__new__(cls)
    context=SimpleNamespace(role='results',assignment={'selector':{'version':FAMILIES[family][5]}})
    assert instance.applies(context)
    context.role='annotation';assert not instance.applies(context)
    context.role='results';context.assignment={'selector':{'version':'invented'}}
    assert not instance.applies(context)


@pytest.mark.parametrize('family',['atac','chromatin'])
def test_capture_availability_retains_exact_existing_exception_identity(family):
    cls=current_constructor_import(family,'host');owner=importlib.import_module(cls.__module__)
    error_type=module('native_file_capture').NativeFileCaptureError
    assert owner.NativeFileCaptureError is error_type
    unexpected=error_type('invalid_capture_path')
    with pytest.raises(error_type) as observed:owner._input_failure(unexpected,field='/input')
    assert observed.value is unexpected
    absent=owner._input_failure(error_type('retained_artifact_unavailable'),field='/input')
    mismatch=owner._input_failure(error_type('retained_artifact_mismatch'),field='/input')
    assert absent['code']==('saved_attachment_unavailable' if family=='atac' else 'input_unavailable')
    assert mismatch['code']=='artifact_digest_mismatch'
    assert absent['field_path']==mismatch['field_path']=='/input'


def chromatin_environment():
    return {**{key:'1' for key in ('PYTHONNOUSERSITE','PYTHONSAFEPATH','PYTHONDONTWRITEBYTECODE',
        'OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')},**{key:'/declared/runtime' for key in
        ('PYTHONHOME','TMP','TEMP','TMPDIR','XDG_CACHE_HOME','PIP_CACHE_DIR','PYTHONPATH')}}


def old_chromatin_environment():
    owner=module('library.chromatin_request_contracts')
    path=Path(__file__).parent/'fixtures/a107_original_chromatin_environment.py'
    namespace={name:getattr(owner,name) for name in ('validate_chromatin_record','require','path_value','os')}
    exec(compile(path.read_bytes(),str(path),'exec',dont_inherit=True),namespace)
    return namespace['_environment']






def probe(phase,output):
    """Retain actual original failures; predictions are asserted after writing."""
    cases=[]
    for family in TOOLS:
        cases.append(('tool_'+family,lambda family=family:actual_request_schema(family,[None]),
            TOOLS[family][1],lambda family=family:error_record(lambda:getattr(module(TOOLS[family][2]),TOOLS[family][3])([None]))))
    cases.append(('empty_chromatin_local',local_chromatin_empty,'native_chromatin_interaction_contracts',None))
    for family in ('atac','flux'):
        cases.append(('origin_'+family,lambda family=family:original_fact_origin(family),FAMILIES[family][4],None))
    for family in FAMILIES:
        for kind in ('return','host'):
            missing=FAMILIES[family][3 if kind=='return' else 4]
            cases.append(('constructor_import_'+family+'_'+kind,lambda family=family,kind=kind:current_constructor_import(family,kind),missing,None))
    # Existing passive metadata controls remain unchanged before/after.
    cases.append(('unchanged_empty_atac_catalog',lambda:actual_request_schema('atac',[]),None,None))
    cases.append(('unchanged_unknown_resource',lambda:metadata_owner()._request_schema('missing',selected=True),None,
        lambda:{'type':'builtins.KeyError','message':"'missing'",'missing_module':None}))
    observations=[]
    for name,call,missing,post_error in cases:
        record={'name':name}
        try:
            value=call();record['outcome']='return'
            if isinstance(value,type):record['class']=value.__module__+'.'+value.__qualname__
            else:record['value_sha256']=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
        except Exception as error:
            record.update(outcome='exception',error={'type':type(error).__module__+'.'+type(error).__qualname__,
                'message':str(error),'missing_module':getattr(error,'name',None)})
        if phase=='baseline' and missing:
            expected={'type':'builtins.ModuleNotFoundError','message':"No module named '"+AXIS+'.'+missing+"'",'missing_module':AXIS+'.'+missing}
        elif post_error is not None:expected=post_error()
        else:expected=None
        record['expected']=expected
        record['expected_observed']=(record.get('error')==expected if expected is not None else record['outcome']=='return')
        observations.append(record)
    owner=module(OWNER);owner_path=Path(owner.__file__)
    report={'phase':phase,'source':str(owner_path),'source_sha256':hashlib.sha256(owner_path.read_bytes()).hexdigest(),
        'probes':observations,'all_expected_observed':all(item['expected_observed'] for item in observations),
        'scope':'Actual metadata methods plus exact isolated current constructor ImportFrom sites. Full factory construction, saved restoration and native execution are not claimed.'}
    target=Path(output);assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2)+'\n')
    assert report['all_expected_observed'],[(row['name'],row.get('error'),row['expected']) for row in observations if not row['expected_observed']]


if __name__=='__main__':
    assert len(sys.argv)==3 and sys.argv[1] in {'baseline','post'}
    probe(sys.argv[1],sys.argv[2])
