"""Proposed real default-service/private-owner catalog checks; no execution grant."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
from .resource_task_checks import own, capture, forbidden

CATALOG_CASES = ('resource_no_declarations', 'scientific_only', 'generic_scientific_five',
    'generic_child_configuration_conflict', 'generic_missing_native_child',
    'generic_duplicate_variant','generic_duplicate_route','generic_malformed_route','generic_foreign_native_contract',
    'generic_entry_class_conflict','generic_native_class_conflict',
    'subclass_nonparticipant',
    'custom_return', 'custom_raise', 'ordinary_fallback', 'ordinary_fallback_raise')


def catalog_observation(v, case):
    assert case in CATALOG_CASES
    path = (('annotation','root'),('structural_homology_evidence','science'))
    original_scientific = v.registry.for_path(path)
    connected = hasattr(type(original_scientific), 'resource_information_catalog')
    events = []
    marker = ValueError('original_custom_catalog_failure')
    original_scope = v.scope
    direct = [{'name':'fixture.inspect', 'resources':'local',
        'description':'Controlled ordinary catalog', 'input_schema':own('domain').obj({})}]
    def callback(scope):
        assert scope is original_scope
        events.append('custom' if case.startswith('custom') else 'ordinary')
        if case.endswith('raise'):
            raise marker
        return direct
    if case.startswith('custom') or case.startswith('ordinary'):
        services = SimpleNamespace(tool_catalog=callback)
        if case.startswith('custom'):
            services.tool_information_catalog = callback
        scientific = own('structural_homology_evidence.episode').StructuralHomologyEvidenceEpisode(services,
            library=original_scientific.library, tool_library=original_scientific.tool_library,
            child_roles=('structural_homology_evidence','launch','results'))
        try:
            result = scientific._information_catalog(original_scope)
        except ValueError as error:
            assert error is marker and case.endswith('raise')
            observed = {'status':'raised','type':'builtins.ValueError','message':str(error),
                        'same_original_exception':True}
        else:
            assert result is direct and not case.endswith('raise')
            observed = {'status':'returned','value':result,'same_original_return':True}
        assert events == ['custom' if case.startswith('custom') else 'ordinary']
        return {'case':case,'connected':connected,'result':observed,'events':events}
    workflow = SimpleNamespace(tools=SimpleNamespace(catalog=lambda **kw:deepcopy(direct)))
    services = own('episode_services').WorkflowServices(workflow)
    scientific_type=own('structural_homology_evidence.episode').StructuralHomologyEvidenceEpisode
    if case=='subclass_nonparticipant':
        class Nonparticipant(scientific_type):
            @property
            def resource_information_catalog(self):
                raise AssertionError('nonparticipant hook lookup must not precede original fallback')
        scientific_type=Nonparticipant
    scientific = scientific_type(services,
        library=original_scientific.library, tool_library=original_scientific.tool_library,
        child_roles=('structural_homology_evidence','launch','results'))
    if case == 'scientific_only':
        bindings = []
    elif case == 'resource_no_declarations':
        bindings = list(v.bindings.values())
        assert all(not hasattr(binding, 'resource_tool_contracts') for binding in bindings)
    else:
        tools = v.tools
        # This is the actual factory's five original constructors, not an
        # invented complete tree. No root/HPC counterparts are supplied here.
        bindings = list(own('structural_homology_evidence.episode').create_execution_bindings(
            services,store=v.store,run_id=v.journal.run_id,directory=v.output/'catalog-generic',
            resources={'selected-api':{'kind':'api','service':'ncbi_blast'}},
            initial_information={},tool_registry=tools,handoff_unit=2,acquired_record_unit=3,
            log_window_bytes=32,log_roles=[]))
        assert [binding.binding_path for binding in bindings] == [
            'structural_homology_evidence/execution_job_submission',
            'structural_homology_evidence/execution_job_submission/api_job_execution',
            'structural_homology_evidence/execution_job_submission/local_job_execution',
            'structural_homology_evidence/execution_job_submission/hpc_job_execution',
            'structural_homology_evidence/execution_result_acquisition']
        if case == 'generic_child_configuration_conflict':
            bindings[1].resources['selected-api']['description']='different original configuration'
        elif case == 'generic_missing_native_child':
            bindings = [binding for binding in bindings if binding.roles != ('launch_api',)]
        elif case in {'generic_entry_class_conflict','generic_native_class_conflict'}:
            selected=bindings[0 if case=='generic_entry_class_conflict' else 1]
            class ForeignRegisteredSubclass(type(selected)):pass
            # Controlled negative identity fault; preserve every original
            # constructor operand and operation declaration on this instance.
            selected.__class__=ForeignRegisteredSubclass
    mutation_operation=None
    if case in {'generic_duplicate_variant','generic_duplicate_route','generic_malformed_route','generic_foreign_native_contract'}:
        entry=next(binding for binding in bindings if binding.roles==('launch',))
        original_declare=entry.resource_tool_contracts
        if case=='generic_foreign_native_contract':
            contract=next(row for row in original_declare() if any(route['entry_role']=='launch' for route in row['invocation_route']['routes']))
            mutation_operation=contract['name'];variant=(contract['name'],contract['resources'])
            native=next(binding for binding in bindings if binding.roles==('launch_api',))
            original_native=native.resource_tool_contracts
            def foreign_contract():
                rows=deepcopy(original_native())
                for row in rows:
                    if (row['name'],row['resources'])==variant:row['instructions']='Foreign declaration must not match the selected parent.'
                return rows
            native.resource_tool_contracts=foreign_contract
        else:
            def malformed_contracts():
                rows=deepcopy(original_declare())
                if case=='generic_duplicate_variant':rows.append(deepcopy(rows[0]))
                elif case=='generic_duplicate_route':rows[0]['invocation_route']['routes'].append(deepcopy(rows[0]['invocation_route']['routes'][0]))
                else:rows[0]['invocation_route']['kind']='direct'
                return rows
            entry.resource_tool_contracts=malformed_contracts
    registry = own('episode_bindings').EpisodeBindingRegistry((scientific,*bindings))
    workflow.episode_bindings=registry;workflow.structural_homology_evidence_binding=scientific
    observed = capture(lambda:services.tool_information_catalog(original_scope))
    if case=='generic_malformed_route':
        assert observed=={'status':'raised','type':'builtins.ValueError','message':'resource_tool_information_commission_route_required'}
    elif (not connected and case!='scientific_only') or case=='subclass_nonparticipant':
        expected = ('episode_role_requires_parent:launch' if case=='resource_no_declarations'
                    else 'resource_tool_information_owner_invalid')
        kind = 'LookupError' if case=='resource_no_declarations' else 'ValueError'
        assert observed == {'status':'raised','type':'builtins.'+kind,'message':expected}
    elif case in {'generic_child_configuration_conflict','generic_entry_class_conflict','generic_native_class_conflict'}:
        assert observed == {'status':'raised','type':'builtins.ValueError',
                            'message':'resource_tool_information_owner_invalid'}
    elif case=='generic_missing_native_child':
        assert observed == {'status':'raised','type':'builtins.LookupError',
                            'message':'episode_role_not_bound:launch_api'}
    elif case in {'generic_duplicate_variant','generic_duplicate_route','generic_foreign_native_contract'}:
        message={'generic_duplicate_variant':'resource_tool_information_variant_duplicate',
            'generic_duplicate_route':'resource_tool_information_route_duplicate',
            'generic_foreign_native_contract':'resource_tool_information_owner_conflict:'+str(mutation_operation)}[case]
        assert observed=={'status':'raised','type':'builtins.ValueError','message':message}
    else:
        assert observed['status']=='returned'
        rows = observed['value']
        direct_rows = [row for row in rows if row['invocation_route']['kind']=='direct']
        assert direct_rows == [{**direct[0],'invocation_route':{'kind':'direct'}}]
        commissioned = [row for row in rows if row['invocation_route']['kind']=='commission']
        if case in {'resource_no_declarations','scientific_only'}:
            assert commissioned == []
        else:
            assert commissioned
            expected_entries=set()
            for row in commissioned:
                for route in row['invocation_route']['routes']:
                    expected_entries.add(route['entry_role'])
                    assert route['resource_id']=='selected-api'
                    entry=registry.for_child(path,route['entry_role'])
                    child=(entry if route['entry_role']=='results' else registry.for_child(
                        (*path,('launch','catalog-only')),route['resource_role']))
                    assert child.resources[route['resource_id']]==entry.resources[route['resource_id']]
                    declared = child.resource_tool_contracts()
                    assert any(item['name']==row['name'] and item['resources']==row['resources']
                               and route in item['invocation_route']['routes'] for item in declared)
            assert expected_entries=={'launch','results'}
    return {'case':case,'connected':connected,'result':observed,
            'controlled_declaration_mutation':case if case.startswith(('generic_duplicate','generic_malformed','generic_foreign')) else None,
            'mutation_operation':mutation_operation,
            'actual_binding_paths':[binding.binding_path for binding in bindings],
            'actual_binding_classes':{binding.binding_path:type(binding).__module__+'.'+type(binding).__qualname__ for binding in bindings},
            'controlled_class_mutation':case if case in {'generic_entry_class_conflict','generic_native_class_conflict'} else None,
            'declared_contracts':{binding.binding_path:binding.resource_tool_contracts() for binding in bindings
                                  if callable(getattr(binding,'resource_tool_contracts',None))},
            'resource_configurations':{binding.binding_path:deepcopy(binding.resources) for binding in bindings
                                       if hasattr(binding,'resources')},
            'default_scientific_factory_five':case not in {'resource_no_declarations','scientific_only'},
            'synthetic_HPC_or_root_counterparts_added':False,
            'commissioning_receipt_authenticated':False,'scientific_credit':0}
