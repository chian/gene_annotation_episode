"""Draft caller-repair checks using real A103 owners/registry and SQLite memory.

Only host capacity and local-snapshot ports are controlled. These observations
are planning data, never commissioning, native execution or scientific credit.
"""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
from .resource_task_checks import own,capture,ControlledAdapter

SOURCE_ROLES=(('literature',),('literature','literature_strategy'),
    ('literature','literature_strategy','literature_search'),
    ('literature','literature_strategy','literature_search','literature_page'),
    *(('literature','literature_strategy','literature_search','literature_page',role)
      for role in ('literature_table','literature_ordered','literature_targeted')),('monitor',))
CALLER_CASES=tuple(prefix+'_'+roles[-1] for prefix in ('root','scientific') for roles in SOURCE_ROLES)
PLANNING_CASES=('selected','parent','root','scientific','recursive_scientific','standalone_duplicate',
    'invalid_private_parent',*CALLER_CASES,'root_missing_launch','scientific_missing_launch',
    'wrong_registered_class','wrong_resource_child','nonparticipant','generic_default',
    'malformed_nonparticipant','malformed_private','annotation_source_undeclared',
    'scientific_source_undeclared','annotation_science_undeclared','malformed_unknown_descendant',
    'broken_resource_malformed_edge','standalone_root_launch','standalone_scientific_launch',
    'root_source_missing_launch','scientific_source_missing_launch','wrong_source_class',
    'standalone_literature_unknown_suffix','standalone_monitor_unknown_suffix')


def planning_observation(v, scenario='selected'):
    assert scenario in PLANNING_CASES
    # Distinguishable actual private portfolios expose accidental global or
    # sibling selection. The existing controlled adapter protocol remains the
    # declared engineering boundary; no actual capability is fabricated.
    portfolios={}
    for prefix in ('root','scientific'):
        values=[]
        for kind in ('api','local','hpc'):
            adapter=ControlledAdapter(kind);adapter.resource_id=prefix+'-'+kind
            values.append(adapter)
        portfolios[prefix]={a.resource_id:a for a in values}
    for home,binding in v.bindings.items():
        binding.adapters=portfolios['scientific' if home.startswith('scientific_process/') else 'root']
    path=v.context.path
    if scenario=='parent':path=v.parent.path
    elif scenario=='root':path=(('annotation','root'),)
    elif scenario=='scientific':path=(('annotation','root'),('scientific_process','science'))
    elif scenario=='recursive_scientific':path=(('annotation','root'),('scientific_process','science'),('scientific_process','revised'))
    elif scenario=='standalone_duplicate':path=(('launch','unowned-standalone'),)
    elif scenario=='invalid_private_parent':path=(('annotation','root'),('launch_local','without-launch'))
    elif scenario in CALLER_CASES:
        prefix,role=scenario.split('_',1)
        roles,=[roles for roles in SOURCE_ROLES if roles[-1]==role]
        path=(('annotation','root'),)
        if prefix=='scientific':path+=(('scientific_process','science'),)
        path+=tuple((role,'original-'+role) for role in roles)
    elif scenario in ('root_missing_launch','scientific_missing_launch'):
        path=(('annotation','root'),)
        if scenario.startswith('scientific'):path+=(('scientific_process','science'),)
    elif scenario=='wrong_resource_child':path=(('annotation','root'),('launch','parent'),('launch_local','child'))
    elif scenario=='nonparticipant':path=(('unrecognized_original_caller','original'),)
    elif scenario=='generic_default':path=(('annotation','root'),('scientific_process','science'))
    elif scenario=='malformed_nonparticipant':path=(('unrecognized_original_caller',''),)
    elif scenario=='malformed_private':path=(('annotation','root'),('launch',''))
    elif scenario in ('standalone_literature_unknown_suffix','standalone_monitor_unknown_suffix'):
        path=((scenario.split('_')[1],'original-source'),('unrecognized_original_caller',''))
    elif scenario=='annotation_science_undeclared':path=(('annotation','root'),('scientific_process','science'))
    elif scenario=='broken_resource_malformed_edge':path=(('annotation','root'),('launch','parent'),('unknown_child',''))
    elif scenario in ('standalone_root_launch','standalone_scientific_launch'):path=(('launch','original-source'),)
    elif scenario in ('annotation_source_undeclared','scientific_source_undeclared',
                      'root_source_missing_launch','scientific_source_missing_launch','malformed_unknown_descendant','wrong_source_class'):
        path=(('annotation','root'),)
        if scenario.startswith('scientific'):path+=(('scientific_process','science'),)
        path+=(('literature','original-source'),)
        if scenario=='malformed_unknown_descendant':path+=(('unrecognized_original_caller',''),)
    members=list(v.bindings.values())
    scientific=v.registry.for_binding_path('scientific_process')
    additional=[]
    source_cases=('annotation_source_undeclared','scientific_source_undeclared',
                  'root_source_missing_launch','scientific_source_missing_launch','malformed_unknown_descendant','wrong_source_class',
                  'standalone_literature_unknown_suffix','standalone_monitor_unknown_suffix')
    if scenario in CALLER_CASES or scenario in source_cases:
        scientific=own('scientific_process.episode').ScientificProcessEpisode(v.services,
            library=scientific.library,tool_library=scientific.tool_library,
            child_roles=(('scientific_process','launch','results','monitor') if scenario=='scientific_source_undeclared'
                         else ('scientific_process','launch','results','literature','monitor')))
        for prefix in ('','scientific_process.'):
            additional.extend(own(prefix+'published_evidence_assessment.episode').create_binding_tree(v.services))
            additional.append(own(prefix+'execution_progress_assessment.episode').MonitorEpisode(v.services))
        if scenario=='wrong_source_class':
            selected=next(binding for binding in additional if binding.binding_path=='published_evidence_assessment')
            class ForeignSourceSubclass(type(selected)):pass
            selected.__class__=ForeignSourceSubclass
    missing_cases=('root_missing_launch','scientific_missing_launch','root_source_missing_launch','scientific_source_missing_launch')
    if scenario in missing_cases:
        missing=('scientific_process/' if scenario.startswith('scientific') else '')+'resource_work_submission'
        members=[binding for binding in members if binding.binding_path!=missing]
    elif scenario in ('standalone_root_launch','standalone_scientific_launch'):
        wanted=scenario=='standalone_scientific_launch'
        members=[binding for binding in members if binding.binding_path.startswith('scientific_process/')==wanted]
    elif scenario=='wrong_registered_class':
        original=v.bindings['resource_work_submission']
        class UnrecognizedResourceSubclass(type(original)):pass
        invalid=UnrecognizedResourceSubclass(v.services,resource_adapters=tuple(original.adapters.values()))
        members=[invalid if binding is original else binding for binding in members]
    elif scenario=='generic_default':
        from .resource_task_checks import forbidden
        tools=own('tools').ToolRegistry(v.store,clients=SimpleNamespace(blast=forbidden))
        members=list(own('scientific_process.episode').create_execution_bindings(v.services,
            store=v.store,run_id=v.journal.run_id,directory=v.output/'planning-generic',
            resources={'selected-api':{'kind':'api','service':'ncbi_blast'}},initial_information={},
            tool_registry=tools,handoff_unit=2,acquired_record_unit=3,log_window_bytes=32,log_roles=[]))
        assert len(members)==5 and all(b.binding_path.startswith('scientific_process/execution_') for b in members)
    registry=own('episode_bindings').EpisodeBindingRegistry((scientific,*members,*additional))
    # Malformed runtime paths must reach planning's own error-order boundary;
    # BindingContext is a separately validated immutable binding view.
    if scenario in ('malformed_nonparticipant','malformed_private','malformed_unknown_descendant',
                    'broken_resource_malformed_edge','standalone_literature_unknown_suffix',
                    'standalone_monitor_unknown_suffix'):
        context=SimpleNamespace(path=path)
    else:
        context=replace(v.context,path=path,role=path[-1][0])
    workflow=object.__new__(v.runtime.Workflow)
    memory=own('execution_memory').ExecutionMemory(v.output/'planning-memory.sqlite3')
    events=[]
    def snapshot():events.append('local_snapshot');return {'jobs':[],'original_local_observation':True}
    workflow.episode_bindings=registry;workflow.annotation_child_roles=('scientific_process','launch','results','literature','monitor')
    if scenario=='annotation_source_undeclared':workflow.annotation_child_roles=('scientific_process','launch','results','monitor')
    elif scenario=='annotation_science_undeclared':workflow.annotation_child_roles=('launch','results','literature','monitor')
    workflow.grain_names=('annotation','improvement')
    workflow.tools=SimpleNamespace(local_resources=SimpleNamespace(snapshot=snapshot),execution_memory=memory,
        local_job_policy=own('local_jobs').LocalJobPolicy(5368709120,1073741824))
    host={'resource_id':'controlled-local-host','observed_at':1234.,'available_memory_bytes':1073741824,
        'total_memory_bytes':5368709120,'logical_cpus':1,'load_average':[0.,0.,0.],
        'meaning':'Controlled host observation; grants no capacity.'}
    planning=own('execution_planning')
    connected=hasattr(planning,'planning_binding')
    original_observe=memory.observe
    def observe(*args,**kwargs):events.append('memory_observe');return original_observe(*args,**kwargs)
    capability_owners={b.binding_path:b for b in members if callable(getattr(b,'capabilities',None))}
    original_capabilities={home:binding.capabilities for home,binding in capability_owners.items()}
    def capabilities(home):
        def read():events.append('capabilities:'+home);return original_capabilities[home]()
        return read
    # Bound original methods still validate and return the real adapter protocol.
    from contextlib import ExitStack
    with ExitStack() as stack:
        stack.enter_context(patch.object(planning,'host_capacity',lambda:deepcopy(host)))
        stack.enter_context(patch.object(memory,'observe',observe))
        for home,binding in capability_owners.items():stack.enter_context(patch.object(binding,'capabilities',capabilities(home)))
        if scenario=='wrong_resource_child':
            original_child=registry._child_binding
            def wrong_child(parent,role):
                if getattr(parent,'binding_path',None)=='resource_work_submission' and role=='launch_local':
                    return registry.for_binding_path('scientific_process/resource_work_submission/local_resource_work_execution')
                return original_child(parent,role)
            stack.enter_context(patch.object(registry,'_child_binding',wrong_child))
        result=capture(lambda:v.runtime.Workflow.resource_context(workflow,context))
    expected_failure=None
    if connected and scenario in missing_cases:
        # a103 label is legacy_annotation: the annotation root resolves to a real parent (a103/episode_bindings.py:450-453, message at :433).
        parent='scientific_process' if scenario.startswith('scientific') else 'legacy_annotation'
        expected_failure=('LookupError','episode_child_not_bound:'+parent+':launch')
    elif connected and scenario=='wrong_registered_class':expected_failure=('ValueError','resource_planning_registered_identity_mismatch')
    elif connected and scenario=='wrong_resource_child':expected_failure=('ValueError','resource_planning_private_edge_mismatch')
    elif connected and scenario=='wrong_source_class':expected_failure=('ValueError','resource_planning_private_edge_mismatch')
    elif connected and scenario in ('malformed_private','broken_resource_malformed_edge'):expected_failure=('ValueError','episode_binding_runtime_path_required')
    elif connected and scenario in ('annotation_source_undeclared','scientific_source_undeclared','annotation_science_undeclared'):
        home=('scientific_process' if scenario=='annotation_science_undeclared' else
              ('scientific_process/' if scenario=='scientific_source_undeclared' else '')+'published_evidence_assessment')
        expected_failure=('ValueError','resource_planning_child_not_declared:'+home)
    if expected_failure:
        kind,message=expected_failure
        assert result=={'status':'raised','type':'builtins.'+kind,'message':message}
        assert events==[] and not memory.path.exists()
    elif not connected and scenario not in (*missing_cases,'generic_default','standalone_root_launch','standalone_scientific_launch'):
        assert result=={'status':'raised','type':'builtins.LookupError','message':'episode_role_requires_parent:launch'}
        assert events==[] and not memory.path.exists()
    elif scenario in ('standalone_duplicate','nonparticipant','malformed_nonparticipant','malformed_unknown_descendant',
                      'standalone_literature_unknown_suffix','standalone_monitor_unknown_suffix'):
        assert result=={'status':'raised','type':'builtins.LookupError','message':'episode_role_requires_parent:launch'}
        assert events==[] and not memory.path.exists()
    elif scenario=='invalid_private_parent':
        # a103 label is legacy_annotation: the annotation root resolves to a real parent (a103/episode_bindings.py:450-453, message at :433).
        assert result=={'status':'raised','type':'builtins.LookupError','message':'episode_child_not_bound:legacy_annotation:launch_local'}
        assert events==[] and not memory.path.exists()
    else:
        # The original unambiguous global lookup chooses the other portfolio in
        # the two missing-parent cases. Record that baseline, never authenticate
        # its numerical/resource identity as the private parent's counterpart.
        prefix=('scientific' if scenario.startswith('root_') else 'root') if not connected and scenario in missing_cases else (
            'scientific' if any(role=='scientific_process' for role,_ in path) else 'root')
        if scenario=='standalone_scientific_launch':prefix='scientific'
        selected=('scientific_process/' if prefix=='scientific' else '')+'resource_work_submission'
        if scenario=='generic_default':selected='scientific_process/execution_job_submission'
        assert result['status']=='returned'
        value=result['value'];assert {row['resource_id'] for row in value['execution_capabilities']}==(
            {'selected-api'} if scenario=='generic_default' else set(portfolios[prefix]))
        assert events==['capabilities:'+selected,'local_snapshot','memory_observe']
        assert value['execution_planning']['remote']=={} and value['execution_planning']['local_pending']==[]
        assert value['execution_planning']['host']['resource_id']==host['resource_id']
        assert value['whole_workflow']['environment_bounds']=={'cpu_percent':100,'memory_bytes':5368709120,'swap_bytes':0}
        retained=memory.latest(host['resource_id'],'capacity',now=host['observed_at'])
        assert retained['state']=='fresh' and retained['data']==host and retained['reference']==value['execution_planning']['host']['reference']
    return {'scenario':scenario,'context_path':[list(part) for part in path],
        'registered_binding_paths':sorted(registry._by_path),
        'connected':connected,'result':result,'events':events,'real_SQLite_memory_created':memory.path.exists(),
        'controlled_ports':['host_capacity','local_resources.snapshot','ControlledAdapter capability protocol'],
        'controlled_source_class_mutation':scenario=='wrong_source_class',
        'commissioning_receipt_authenticated':False,'capacity_reserved':False,'scientific_credit':0}


def planning_recipe_observation(v, scenario='original'):
    """Actual tool snapshot + two actual HPC owners, without remote execution."""
    assert scenario in ('original','unknown_tool','invalid_profile','history_exception')
    workflow=object.__new__(v.runtime.Workflow);events=[]
    memory=own('execution_memory').ExecutionMemory(v.output/'recipe-memory.sqlite3')
    # The actual runtime's original absent-capacity branch returns None. The
    # full capacity path is exercised separately by planning_observation.
    workflow.tools=SimpleNamespace(execution_memory=memory,local_resources=None)
    workflow.annotation_child_roles=('scientific_process','hpc')
    workflow.grain_names=('annotation','improvement')
    previous_science=v.registry.for_path((('annotation','root'),('scientific_process','science')))
    catalog=previous_science.tool_library.catalog()
    tool_library=own('scientific_tool_library').ScientificToolLibrary.freeze(
        v.output/'recipe-tool-library',catalog=catalog)
    def available(scope):events.append('tool_catalog');return deepcopy(catalog)
    services=SimpleNamespace(workflow=workflow,tool_catalog=available)
    scientific=own('scientific_process.episode').ScientificProcessEpisode(services,
        library=previous_science.library,tool_library=tool_library,
        child_roles=('scientific_process','launch','results','hpc'))
    resources={'original-aurora':{'kind':'pbs_ssh','account':'BioReason-Aurora-Test',
        'workspace':'/lus/flare/projects/BioReason-Aurora-Test/chian/runs/planning-only-fixture'}}
    hpc={home:own(home.replace('/','.')+'.episode').HPCEpisode(services,store=v.store,
        run_id=v.journal.run_id,directory=v.output/home,resources=resources,commissions={})
        for home in ('hpc_work_planning','scientific_process/hpc_work_planning')}
    registry=own('episode_bindings').EpisodeBindingRegistry((scientific,*v.bindings.values(),*hpc.values()))
    workflow.episode_bindings=registry
    path=(('annotation','root'),('scientific_process','science'))
    context=replace(v.context,path=path,role='scientific_process')
    planning=own('execution_planning');connected=hasattr(planning,'planning_binding')
    arguments={'name':'fixture.inspect','resources':'local','profiles':[{'resource_id':'original-local',
        'backend':'local','tool':'fixture.inspect','implementation':'original','parameters':'original','hardware':'original'}]}
    if scenario=='unknown_tool':arguments['name']='unknown.fixture'
    elif scenario=='invalid_profile':arguments['profiles'][0]['backend']='foreign'
    marker=OSError('original_compatible_history_io');original_history=memory.history
    def history(*args,**kwargs):
        events.append('history')
        if scenario=='history_exception':raise marker
        return original_history(*args,**kwargs)
    with patch.object(memory,'history',history):
        try:result=planning.read(scientific,context,arguments)
        except Exception as error:
            observed={'status':'raised','type':type(error).__module__+'.'+type(error).__qualname__,'message':str(error)}
            if scenario=='history_exception':assert error is marker
        else:observed={'status':'returned','value':result}
    if scenario=='unknown_tool':
        assert observed=={'status':'raised','type':'builtins.ValueError','message':'scientific_tool_unknown:unknown.fixture:local'}
        assert events==['tool_catalog']
    elif scenario=='invalid_profile':
        assert observed=={'status':'raised','type':'builtins.ValueError','message':'explicit_execution_compatibility_profile_required'}
        assert events==['tool_catalog']
    elif scenario=='history_exception':
        assert observed=={'status':'raised','type':'builtins.OSError','message':str(marker)}
        assert events==['tool_catalog','history']
    else:
        assert observed=={'status':'raised','type':'builtins.LookupError','message':'episode_role_requires_parent:hpc'}
        assert events==['tool_catalog','history']
    return {'scenario':scenario,'connected':connected,'result':observed,'events':events,
        'actual_HPC_homes':sorted(hpc),'empty_validated_commissions':True,
        'controlled_ports':['tool catalog availability','compatible history exception in its named case'],
        'remote_execution':False,'caller_commission_authentication':False}
