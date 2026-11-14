"""A103 moved pure policy boundaries with explicit record-reading ports."""
from types import SimpleNamespace
from ... import a103_investigation as investigation
from ... import a103_hpc as hpc
from ...domain import ContractError
from ...episode_bindings import BindingContext
from .policy_owner_checks import original, owner, observed, paired, root_projector_modules


def context(axis='A103', role='scientific_process'):
    return BindingContext('run', 'episode', role, ((role, 'unit'),), {},
        {'selection': {'evidence_axis': {'option_id': axis}}}, {}, ('received', 'received'))


def test_projector_original_type_and_actual_root_maps(monkeypatch):
    current = owner('task_projector')
    paired(monkeypatch, original('binding'), current,
        lambda module, patch: observed(lambda: module.original_task_projector({'actual':'assignment'})))
    for module in root_projector_modules():
        assert module is current
        assert module.original_task_projector is current.original_task_projector


def test_original_child_whitelist_and_tool_refusal(monkeypatch):
    old = original('binding')
    def roles(module, patch):
        observed_roles = []
        def supplied():
            for role in ('launch', 'scientific_process', 'literature', 'monitor', 'literature', 'results'):
                observed_roles.append(role); yield role
        result = module.allowed_child_roles(supplied())
        assert result == ('scientific_process', 'literature', 'literature')
        return result, observed_roles
    paired(monkeypatch, old, owner('child_policy'), roles)
    def tools(module, patch):
        result = [observed(lambda: module.validate_tool_name(name))
                  for name in ('sequence.align', 'sequence.inspect', 'unknown')]
        assert result[0][0:3] == ('error', ContractError, 'a103_new_sequence_comparison_requires_shared_parent')
        assert result[1:] == [('value', None), ('value', None)]
        return result
    paired(monkeypatch, old, owner('tool_policy'), tools)


def test_exact_original_guidance(monkeypatch):
    paired(monkeypatch, original('binding'), owner('scientific_guidance'),
        lambda module, patch: module.scientific_guidance())


def test_received_facts_gate_and_missing_store(monkeypatch):
    def scenario(module, patch):
        binding = SimpleNamespace(services=SimpleNamespace(workflow=None))
        schema = {'properties': {'facts': {'x-source': investigation.CONTEXT_RECORD_SOURCE}}}
        assert module.received_report_facts(binding, context(), {}, {}) == {}
        result = observed(lambda: module.received_report_facts(binding, context(), {}, schema))
        assert result[0:3] == ('error', ContractError, 'a103_report_store_required')
        return result
    paired(monkeypatch, original('binding'), owner('received_context_report'), scenario)


def test_received_facts_original_receipt_operands(monkeypatch):
    def scenario(module, patch):
        events = []; store = object()
        binding = SimpleNamespace(services=SimpleNamespace(workflow=SimpleNamespace(store=store)))
        def received(actual_store, refs, scope, *, committed):
            assert actual_store is store; events.append((refs, scope, committed)); return ['supplied-record-port']
        patch.setattr(module, 'received_context_records', received)
        schema = {'properties': {'facts': {'x-source': investigation.CONTEXT_RECORD_SOURCE}}}
        value = module.received_report_facts(binding, context(), {'committed_record_refs': ['committed']}, schema)
        assert value == {investigation.CONTEXT_RECORD_SOURCE: ['supplied-record-port']}
        assert events == [(('received', 'received'), {}, ['committed'])]
        return value, events
    paired(monkeypatch, original('binding'), owner('received_context_report'), scenario)


def test_execution_context_actual_axis_gates_and_lazy_provider(monkeypatch):
    def scenario(module, patch):
        events = []; store = object()
        workflow = SimpleNamespace(store=store, tools=SimpleNamespace(a103_execution_resources=object()))
        def findings(actual_store, ctx, refs):
            assert actual_store is store; events.append((ctx.role, ctx.assignment['selection']['evidence_axis']['option_id'], refs))
            return ['supplied-execution-port']
        patch.setattr(hpc, 'execution_findings', findings)
        values = [module.received_execution_context(context(), None),
            module.received_execution_context(context('A102'), workflow),
            module.received_execution_context(context('A103'), workflow),
            module.received_execution_context(context('A107'), workflow),
            module.received_execution_context(context('A102', 'annotation'), workflow)]
        assert values[:2] == [{}, {}]
        assert len(events) == 3 and all(event[2] == {'received'} for event in events)
        return values, events
    paired(monkeypatch, original('binding'), owner('received_execution_context'), scenario)


def test_legacy_report_original_exception_translation(monkeypatch):
    def scenario(module, patch):
        events = []; results = []; store = object()
        binding = SimpleNamespace(services=SimpleNamespace(workflow=SimpleNamespace(store=store)))
        codes = ('a103_association_statement_requires_actual_measurement',
            'a103_system_statement_requires_qualified_context',
            'a103_function_interpretation_requires_explicit_hypothesis_and_assessment',
            'a103_trait_statement_requires_local_feature_attribution',
            'a103_contrast_statement_requires_context_panel',
            'a103_discriminating_contrast_requires_qualified_separated_bounds', 'other-original-failure')
        for code in codes:
            def resolve(actual_store, form, *, scope):
                assert actual_store is store; events.append((form, scope)); raise ContractError(code)
            patch.setattr(module, 'resolve_report', resolve)
            results.append(observed(lambda: module.validate_axis_report(binding, context(), {'x':1},
                investigation.legacy_report_schema())))
        assert results[0][3]['field'] == 'context_summary'
        assert all(result[3]['field'] == 'functional_support' for result in results[1:6])
        assert results[-1][1] is ContractError
        return results, events
    paired(monkeypatch, original('validation'), owner('report_validation'), scenario)


def test_measurement_report_and_other_axis_preserve_admission(monkeypatch):
    def scenario(module, patch):
        store = object(); events = []
        binding = SimpleNamespace(services=SimpleNamespace(workflow=SimpleNamespace(store=store)))
        def resolve(actual_store, form, *, scope):
            assert actual_store is store; events.append((form, scope))
        patch.setattr(module, 'resolve_measurement_report', resolve)
        module.validate_axis_report(binding, context(), {'x':1}, investigation.measurement_report_schema())
        module.validate_axis_report(binding, context('A107'), {'x':1}, investigation.measurement_report_schema())
        module.validate_axis_report(binding, context(), {'x':1}, {})
        assert events == [({'x':1}, {})]
        binding.services.workflow = None
        missing = observed(lambda: module.validate_axis_report(binding, context(), {}, investigation.measurement_report_schema()))
        assert missing[0:3] == ('error', ContractError, 'a103_report_store_required')
        return events, missing
    paired(monkeypatch, original('validation'), owner('report_validation'), scenario)
