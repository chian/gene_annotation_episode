"""Actual A102 registered callers and explicit foreign API observations.

Source-only template. No network, native worker, model or biological claim.
The original source family fixtures supply the actual Store/Journal/registrations.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from . import source_family_checks as original

HOMES=(('published_evidence_assessment', 'literature'), ('published_evidence_assessment/evidence_search_strategy_improvement', 'literature_strategy'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment', 'literature_search'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_page'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction', 'literature_table'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement', 'literature_ordered'), ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction', 'literature_targeted'), ('scientific_process/published_evidence_assessment', 'literature'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement', 'literature_strategy'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment', 'literature_search'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination', 'literature_page'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction', 'literature_table'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement', 'literature_ordered'), ('scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction', 'literature_targeted'))
PREFIX='gene_annotation_episode.episodic_workflow.root.a102'
def own(name):return import_module(PREFIX+'.'+name)
def plain(value):return own('communication').plain(value)
def observe(callback):
    try:
        value=callback()
        return {'status':'returned','type':type(value).__module__+'.'+type(value).__qualname__,
            'value':plain(value.as_record() if hasattr(value,'as_record') else value)}
    except Exception as error:
        return {'status':'raised','type':type(error).__module__+'.'+type(error).__qualname__,
            'message':str(error),'code':getattr(error,'code',None),'detail':plain(getattr(error,'detail',None)),
            'field':getattr(error,'field',None)}
def specialized(binding):
    # Detect a concrete method body feature, never infer from metadata status.
    return '_CHILDREN' not in type(binding).child_roles.__code__.co_names

def own_behavior(value):
    binding=value.binding;context=value.context;role=value.role
    task=original.make_task(value)
    assert value.workflow.specialist(task) is binding
    invalid=deepcopy(value.assignment);invalid['version']='not_the_original_assignment'
    tool=observe(lambda:binding._tool_arguments(context,'not_a_declared_source_operation',{}))
    assert tool['status']=='raised' and tool['type']==PREFIX+'.domain.ContractError'
    assert tool['message']=='tool_not_available_to_literature_role'
    result={'role':role,'binding':binding.binding_path,
        'unknown_role':observe(lambda:binding._role('not_a_literature_role')),
        'nonstring_role':observe(lambda:binding._role(None)),
        'schema':observe(lambda:binding.assignment_schema(role,context=context)),
        'incoming_schema':observe(lambda:binding.child_assignment_schema(context,role)),
        'assignment':observe(lambda:binding._validate_assignment(role,value.assignment,context.scope,context=context)),
        'invalid_assignment':observe(lambda:binding._validate_assignment(role,invalid,context.scope,context=context)),
        'children':observe(lambda:binding.child_roles(role)),
        'available_children':observe(lambda:binding.allowed_children(context,value.workflow.services.capabilities())),
        'instructions':observe(lambda:binding.instructions(context)),
        'catalog':observe(lambda:binding.catalog(context)),
        'summary':observe(lambda:binding.decision_context(context,None)),
        'unavailable_tool':tool,'credit':original.task_credit_trace(value),
        'scientific':original.scientific_trace(value)}
    assert result['schema']['status']==result['assignment']['status']=='returned'
    assert result['invalid_assignment']['status']=='raised'
    return result

def foreign_role(value,foreign,operation):
    assert foreign!=value.role and foreign in {role for _,role in HOMES}
    binding=value.binding
    callback={'guard':lambda:binding._role(foreign),
        'schema':lambda:binding.assignment_schema(foreign,context=value.context),
        'children':lambda:binding.child_roles(foreign)}[operation]
    result=observe(callback)
    if specialized(binding):
        assert result=={'status':'raised','type':'builtins.ValueError',
            'message':'unsupported_literature_role:'+foreign,'code':None,'detail':None,'field':None}
    else:assert result['status']=='returned',result
    return {'home':value.home,'own_role':value.role,'foreign_role':foreign,'operation':operation,
        'specialized':specialized(binding),'observation':result}

def page_parent(value,child_private,parent_private,fields):
    assert value.role in ('literature_table','literature_ordered','literature_targeted')
    configuration=deepcopy(value.configuration)
    def configured(home,private):
        config={**configuration,'private_yield_binding':private,'yield_bindings':configuration['yield_bindings'] if private else None}
        return type(value.bindings[home])(value.workflow.services,**config)
    parent_home=value.home.rsplit('/',1)[0]
    child=configured(value.home,child_private);parent=configured(parent_home,parent_private)
    bindings=[parent if h==parent_home else child if h==value.home else b for h,b in value.bindings.items()]
    registry=own('episode_bindings').EpisodeBindingRegistry((value.workflow.scientific_process_binding,*bindings))
    parent_path=value.context.path[:-1]
    assert registry.for_path(parent_path) is parent and registry.for_child(parent_path,value.role) is child
    page=deepcopy(value.assignment['page'])
    page.update(literature_task=deepcopy(value.assignment['literature_task']),proposed_annotation_ref=value.proposed)
    if fields=='missing_task':page.pop('literature_task')
    elif fields=='missing_proposed':page.pop('proposed_annotation_ref')
    elif fields=='missing_credit_unit':page['literature_task'].pop('credit_unit')
    else:assert fields=='complete'
    parent_id=own('method_loop.identities').EpisodeRef(value.workflow.run_id,parent_path).episode_id
    context=replace(value.context,role='literature_page',path=parent_path,episode_id=parent_id,
        assignment=page,request=original.request_record(page,value.schema))
    parent_validation=observe(lambda:parent._validate_assignment('literature_page',page,context.scope,context=context))
    with patch.object(value.workflow,'episode_bindings',registry):
        admitted=observe(lambda:child.prepare_assignment(context,value.role,deepcopy(value.assignment),context.scope,'actual-page-parent'))
    # Which configuration controls page authentication is visible independently
    # of whether the same saved page is valid under its parent's declaration.
    should_accept=(fields=='complete' or fields in {'missing_task','missing_proposed'} and not child_private
        or fields=='missing_credit_unit' and child_private)
    assert (admitted['status']=='returned')==should_accept,admitted
    if should_accept:assert admitted['value']==value.assignment
    return {'child_home':value.home,'parent_home':parent_home,'child_private':child_private,
        'parent_private':parent_private,'fields':fields,'parent_validation':parent_validation,
        'child_admission':admitted,'original_page':page}


def topology(value,mode,context_kind,configuration):
    config=deepcopy(value.configuration)
    config.update(structure_population=configuration!='ordinary',reference_parent_sources=None,
        contract_information_profile=None)
    if configuration=='reference_empty':config['reference_parent_sources']=[]
    elif configuration=='reference_source':config['reference_parent_sources']=[value.source['id']]
    elif configuration=='profile':config['contract_information_profile']=own('composition_information').CONTRACT_INFORMATION_PROFILE
    else:assert configuration in {'ordinary','population'}
    legacy=own('published_evidence_assessment.episode').create_binding_tree(value.workflow.services,**deepcopy(config))
    scientific=own('scientific_process.published_evidence_assessment.episode').create_binding_tree(value.workflow.services,**deepcopy(config))
    trees={'legacy7':legacy,'scientific7':scientific,'both14':(*legacy,*scientific),'both14_reversed':(*scientific,*legacy)}
    selected=trees[mode]
    registry=own('episode_bindings').EpisodeBindingRegistry((value.workflow.scientific_process_binding,*selected))
    if context_kind=='annotation':path=(('annotation','original-root'),)
    elif context_kind=='scientific_process':path=(('annotation','original-root'),('scientific_process','original-0'))
    elif context_kind=='unbound_launch':path=(('launch','explicit-unbound-reader-context'),)
    else:
        home=next(h for h,r in HOMES if r==context_kind and h.startswith('scientific_process/')==(mode=='scientific7'))
        path=original.path_for(home)
    episode_id=own('method_loop.identities').EpisodeRef(value.workflow.run_id,path).episode_id
    context=replace(value.context,episode_id=episode_id,role=path[-1][0],path=path,assignment={},
        request={'report_contract':{'measurements':{'schema':own('domain').obj({})}}})
    value.workflow.receipts.bind(episode_id)
    value.workflow.receipts.receive(episode_id,list(value.context.received_record_refs),kind='initial')
    context=replace(context,received_record_refs=tuple(value.workflow.receipts.known(episode_id)))
    callbacks={
        'profile':lambda:registry.contract_information_profile(context),
        'initial':lambda:registry.initial_decision_context(context),
        'sources':lambda:registry.received_report_sources(context.role,path=context.path),
        'facts':lambda:registry.received_report_facts(context),
        'current':lambda:registry.current_report_facts(context),
        'references':lambda:registry.received_form_references(context,{},own('domain').obj({}),'topology-receipt'),
        'tokens':lambda:registry.received_evidence_tokens(context),
        'validate':lambda:registry.validate_received_report(context,{},own('domain').obj({}))}
    with patch.object(value.workflow,'episode_bindings',registry):
        owners=observe(lambda:[binding.binding_path for binding in registry._context_bindings(context)])
        results={name:observe(callback) for name,callback in callbacks.items()}
        repeated={name:observe(callback) for name,callback in callbacks.items()}
        duplicate=observe(lambda:own('episode_bindings').EpisodeBindingRegistry((*selected,selected[0])))
    assert duplicate['status']=='raised' and duplicate['type']=='builtins.ValueError'
    assert duplicate['message']=='duplicate_episode_binding_path:'+selected[0].binding_path
    assert results==repeated,'empty original reader/replay must be stable'
    if mode in {'legacy7','scientific7'} and owners['status']=='returned':
        assert all(binding.binding_path in owners['value'] for binding in selected)
    if mode in {'legacy7','scientific7'} and context_kind not in {role for _,role in HOMES} and configuration!='ordinary':
        assert results['sources']['status']=='raised' and results['sources']['message']=='received_report_field_conflict:received_report_sources'
    return {'mode':mode,'context_kind':context_kind,'configuration':configuration,
        'registered':[binding.binding_path for binding in registry._bindings],
        'context':context.as_record(),'selected_owners':owners,'callbacks':results,'repeat_callbacks':repeated,
        'duplicate_binding_rejection':duplicate,
        'nonempty_structural_cells_exercised':False,
        'unbound_foreign_context':context_kind=='unbound_launch'}


def retained_cells(value,binding,context):
    """Execute original A102 conditional geometry, then return its real cells.

    These are original synthetic CIF/XML fixture operands. No target support,
    experimental measurement, annotation confidence or episode credit is invented.
    """
    import asyncio
    import pytest
    from .source_partition_structure_inputs import source,cif,xml,selector
    root=value.source
    coordinates=source(value.store,cif(),parents=[root['id']])
    validation=source(value.store,xml(),parents=[root['id']])
    text='Molecule|Construct|System|Condition|Partner|Experiment'
    literal=source(value.store,text,parents=[root['id']],alias=True)
    literals={};offset=0
    for field,quote in zip(('molecule','construct','experimental_system','condition','partner','experiment'),text.split('|')):
        literals[field]={'source_ref':literal['id'],'representation':'original','start':offset,
            'end':offset+len(quote)};offset+=len(quote)+1
    arguments={'source_ref':root['id'],'coordinate_source_ref':coordinates['id'],
        'validation_source_ref':validation['id'],'source_kind':'synthetic_fixture','model_number':1,'literals':literals,
        'geometry_panel':[{'endpoint_a':{**selector(),'atom_names':['OE1','OE2']},
            'endpoint_b':{**selector('B','2','LIG'),'atom_names':['N1']},'positive_max_A':3.5,'incompatible_min_A':4.5}],
        'local_panel':[selector(),selector('B','2','LIG')],'evaluation_scope':'conditional_deposited_model_geometry'}
    path=original.path_for(binding.binding_path)
    episode_id=own('method_loop.identities').EpisodeRef(context.run_id,path).episode_id
    assignment={'version':'literature_assignment_v1','question_context_refs':[],
        'source_refs':[root['id'],coordinates['id'],validation['id'],literal['id']],
        'literature_task':deepcopy(value.assignment['literature_task']),'proposed_annotation_ref':value.proposed}
    producer=replace(context,role='literature',path=path,episode_id=episode_id,assignment=assignment,
        request=original.request_record(assignment,value.schema),
        received_record_refs=tuple(dict.fromkeys([*value.context.received_record_refs,*assignment['source_refs']])))
    value.workflow.receipts.bind(producer.episode_id)
    value.workflow.receipts.receive(producer.episode_id,list(producer.received_record_refs),kind='initial')
    result=asyncio.run(binding.execute(producer,'literature.structure.populate',arguments,'original-topology-science'))
    assert result['status']=='completed',result
    sheet=result['result']['sheet_ref'];repository=binding.literature_structure_repository()
    rows=repository.project_cells([sheet],permitted_record_refs=result['record_refs'],
        components=('source_geometry_signed','local_fit_index'))
    assert len(rows)==2 and all(row['sheet_ref']==sheet for row in rows)
    assert all(row['origin']=='proposed' and row['unconditional_uncertainty']=='unreported' for row in rows)
    assert rows[0]['value']==rows[1]['value']==pytest.approx(.64)
    return result,rows


def nonempty_receiving(value,mode,context_kind,configuration):
    """Complete actual cell custody through each originally selected reader.

    Source execution and admitted numerical cells remain distinct from target
    scientific findings and episode task credit. Aggregate duplicate errors stay.
    """
    if configuration=='ordinary':return {'population_selected':False}
    config={**deepcopy(value.configuration),'structure_population':True,'reference_parent_sources':None,
        'contract_information_profile':None}
    if configuration=='reference_empty':config['reference_parent_sources']=[]
    elif configuration=='reference_source':config['reference_parent_sources']=[value.source['id']]
    elif configuration=='profile':config['contract_information_profile']=own('composition_information').CONTRACT_INFORMATION_PROFILE
    else:assert configuration=='population'
    legacy=own('published_evidence_assessment.episode').create_binding_tree(value.workflow.services,**deepcopy(config))
    scientific=own('scientific_process.published_evidence_assessment.episode').create_binding_tree(value.workflow.services,**deepcopy(config))
    selected={'legacy7':legacy,'scientific7':scientific,'both14':(*legacy,*scientific),
        'both14_reversed':(*scientific,*legacy)}[mode]
    registry=own('episode_bindings').EpisodeBindingRegistry((value.workflow.scientific_process_binding,*selected))
    if context_kind=='annotation':path=(('annotation','original-root'),)
    elif context_kind=='scientific_process':path=(('annotation','original-root'),('scientific_process','original-0'))
    elif context_kind=='unbound_launch':path=(('launch','explicit-unbound-reader-context'),)
    else:
        home=next(h for h,r in HOMES if r==context_kind and h.startswith('scientific_process/')==(mode=='scientific7'))
        path=original.path_for(home)
    episode_id=own('method_loop.identities').EpisodeRef(value.workflow.run_id,path).episode_id
    context=replace(value.context,episode_id=episode_id,role=path[-1][0],path=path,assignment={},request={})
    producer=next(binding for binding in selected if binding.roles==('literature',))
    with patch.object(value.workflow,'episode_bindings',registry):
        outcome,rows=retained_cells(value,producer,context)
        schema=own('domain').obj({'cells':{**own('literature_structure_storage').structure_cells_schema(),
            'x-source':own('a102_literature_bindings').SOURCE_NAME}})
        form={'cells':rows};context=replace(context,request={'report_contract':{'measurements':{'schema':schema}}},
            received_record_refs=tuple(dict.fromkeys([*value.context.received_record_refs,*outcome['record_refs']])))
        value.workflow.receipts.bind(episode_id)
        value.workflow.receipts.receive(episode_id,list(context.received_record_refs),kind='initial')
        owners=registry._context_bindings(context)
        # Keep exact selected instances, including identical configurations from
        # multiple homes. Per-owner identities are evidence; no elected reader.
        own_receipts=[]
        for index,binding in enumerate(owners):
            if binding not in selected:continue
            result=observe(lambda:binding.received_form_references(context,form,schema,'actual-typed-cell-receipt'))
            assert result['status']=='returned' and result['value'],result
            own_receipts.append({'home':binding.binding_path,'references':result,
                'validate':observe(lambda:binding.validate_received_report(context,form,schema)),
                'tokens':observe(lambda:binding.received_evidence_tokens(context)),
                'facts':observe(lambda:binding.received_report_facts(context))})
        first=observe(lambda:registry.received_form_references(context,form,schema,'actual-aggregate-cell-receipt'))
        second=observe(lambda:registry.received_form_references(context,form,schema,'actual-aggregate-cell-receipt'))
        assert first==second
        aggregate={'sources':observe(lambda:registry.received_report_sources(context.role,path=context.path)),
            'facts':observe(lambda:registry.received_report_facts(context)),
            'tokens':observe(lambda:registry.received_evidence_tokens(context)),
            'validation':observe(lambda:registry.validate_received_report(context,form,schema))}
    expected_receivers=[binding.binding_path for binding in owners if binding in selected]
    assert [row['home'] for row in own_receipts]==expected_receivers
    return {'population_selected':True,'actual_original_outcome':outcome,'actual_rows':rows,
        'selected_receivers':own_receipts,'aggregate_receipt':first,'redelivery':second,'aggregate':aggregate,
        'no_private_source_reader_selected':not expected_receivers,
        'scientific_scope':'synthetic conditional deposited-model geometry; no target finding or task credit assertion'}
