"""A102 moved pure policy boundaries; scientific record resolvers are ports."""
from types import SimpleNamespace
from ... import a102_structural_evidence as evidence
from ... import a102_structural_report as reports
from ... import a102_investigation as investigation
from ...domain import ContractError
from ...episode_bindings import BindingContext
from ...state import Store
from .policy_owner_checks import original, owner, observed, paired, root_projector_modules


def context(role='scientific_process'):
    return BindingContext('run', 'episode', role, ((role, 'unit'),), {},
        {'selection': {'evidence_axis': {'option_id': 'A102'}}}, {}, ('received',))


def merged_entry():
    return dict(entry_version=evidence.INSTRUCTION_VERSION, id='A102', slot='evidence_axis',
        name=evidence.NAME, description=evidence.DESCRIPTION,
        investigation_instructions=evidence.INSTRUCTIONS)


def test_projector_original_types_and_invalid_task(monkeypatch):
    old, current = original('binding'), owner('task_projector')
    def scenario(module, patch):
        values = [observed(lambda: module.original_task_projector({}))]
        for name in ('functional_feature_geometry', 'functional_contrast', 'reference_attribution',
                     'local_trait_attribution', 'interface_constraints'):
            assignment = {'context': {'a102_task': evidence.task_context(name)}}
            values.append(observed(lambda: module.original_task_projector(assignment, merged_a102=True)))
        values.append(observed(lambda: module.original_task_projector(
            {'context': {'a102_task': {'name': 'invented'}}}, merged_a102=True)))
        assert values[-1][0:3] == ('error', ContractError, 'a102_unknown_structural_evidence_task')
        return values
    paired(monkeypatch, old, current, scenario)


def test_projector_actual_root_module_maps():
    current = owner('task_projector')
    for module in root_projector_modules():
        assert module is current
        assert type(module.original_task_projector({})) is type(original('binding').original_task_projector({}))


def test_guidance_exact_original_branches(monkeypatch):
    paired(monkeypatch, original('binding'), owner('scientific_guidance'),
        lambda module, patch: [module.scientific_guidance(value) for value in ({}, merged_entry())])


def test_received_context_original_gates(monkeypatch):
    def scenario(module, patch):
        empty = SimpleNamespace(library=SimpleNamespace(headers=lambda: []))
        axis = {'option_id': 'A102'}
        binding = SimpleNamespace(library=SimpleNamespace(headers=lambda: [{'option_ref': axis}],
            resolve=lambda ref: merged_entry()))
        result = [module.received_structural_context(empty, context(), None),
                  observed(lambda: module.received_structural_context(binding, context(), None))]
        assert result[1][0:3] == ('error', ContractError, 'a102_report_store_required')
        return result
    paired(monkeypatch, original('binding'), owner('received_structural_context'), scenario)


def test_received_context_real_repository_and_forwarded_operands(monkeypatch, tmp_path):
    with Store(tmp_path / 'store') as store:
        workflow = SimpleNamespace(store=store, run_id='run')
        axis = {'option_id': 'A102'}; seen = []
        binding = SimpleNamespace(library=SimpleNamespace(headers=lambda: [{'option_ref': axis}],
            resolve=lambda ref: merged_entry()))
        def scenario(module, patch):
            events = []
            def received(actual_store, **kwargs):
                repository = kwargs['structure_repository']
                assert actual_store is store and repository.store is store and repository.run_id == 'run'
                events.append((type(repository), kwargs['context'].as_record(), kwargs['axis_reference']))
                return ['actual-supplied-record-port']
            patch.setattr(module, 'received_reports', received)
            return module.received_structural_context(binding, context(), workflow), events
        paired(monkeypatch, original('binding'), owner('received_structural_context'), scenario)


def test_structural_report_receiver_gate_precedes_resolver(monkeypatch):
    def scenario(module, patch):
        events = []; axis = {'option_id': 'A102'}
        services = SimpleNamespace(workflow=object(), record_selection=lambda ctx:
            {'run_id': 'wrong', 'episode_id': ctx.episode_id, 'known_record_refs': []})
        binding = SimpleNamespace(library=SimpleNamespace(reference=lambda key: axis,
            resolve=lambda ref: merged_entry()), services=services)
        patch.setattr(module, 'resolve_report', lambda *args, **kwargs: events.append('unexpected-resolve'))
        result = observed(lambda: module.validate_structural_report(binding, context('annotation'), {}, reports.report_schema()))
        assert result[0:3] == ('error', ContractError, 'a102_report_receiver_mismatch') and not events
        assert module.validate_structural_report(binding, context(), {}, {}) is None
        return result, events
    paired(monkeypatch, original('validation'), owner('report_validation'), scenario)


def test_structural_report_error_translation_and_current_context(monkeypatch, tmp_path):
    with Store(tmp_path / 'store') as store:
        def scenario(module, patch):
            axis = {'option_id': 'A102'}; events = []; results = []
            binding = SimpleNamespace(library=SimpleNamespace(reference=lambda key: axis, resolve=lambda ref: merged_entry()),
                services=SimpleNamespace(workflow=SimpleNamespace(store=store, run_id='run'),
                    record_selection=lambda ctx: {'run_id':ctx.run_id,'episode_id':ctx.episode_id,'known_record_refs':['current']}))
            for code in ('a102_comparative_status_differs_from_delivered_evidence',
                         'a102_experimental_status_differs_from_delivered_evidence', 'other-original-failure'):
                def resolve(actual_store, form, **kwargs):
                    assert actual_store is store
                    events.append((form, kwargs['context'].received_record_refs,
                        type(kwargs['structure_repository'])))
                    raise ContractError(code)
                patch.setattr(module, 'resolve_report', resolve)
                results.append(observed(lambda: module.validate_structural_report(
                    binding, context('annotation'), {'actual':'form'}, reports.report_schema())))
            assert results[0][3]['field'] == 'comparative_status'
            assert results[1][3]['field'] == 'experimental_status'
            assert results[2][1] is ContractError
            return results, events
        paired(monkeypatch, original('validation'), owner('report_validation'), scenario)


def test_investigation_original_schemas_and_lazy_resolver(monkeypatch):
    def scenario(module, patch):
        events = []; store = object()
        binding = SimpleNamespace(services=SimpleNamespace(workflow=SimpleNamespace(store=store)))
        def resolve(actual_store, form, *, scope):
            assert actual_store is store; events.append((form, scope))
        patch.setattr(investigation, 'resolve_report', resolve)
        for schema in (investigation.report_schema(), investigation.legacy_report_schema(), {}):
            module.validate_investigation_report(binding, context(), {'x':1}, schema)
        assert len(events) == 2
        return events
    paired(monkeypatch, original('validation'), owner('report_validation'), scenario)
