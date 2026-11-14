"""Nearest original HPC commissioner through the actual private registry.

Uses the existing controlled Store/Journal/planning fixture. No remote
transport, native command or HPC scientific computation is executed. The
historical completed HPC validation cohort retains its original source epoch.
"""
from __future__ import annotations
from dataclasses import replace
import importlib
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a107'
helpers = importlib.import_module(PREFIX + '.tests.launch_connected')
FIXTURE = json.loads((Path(__file__).parent / 'fixtures/organization_original/hpc_launch_suppliers.json').read_text())
ORIGINALS = {row['home']: row for row in FIXTURE['homes']}

def original_callback(home):
    module = importlib.import_module(PREFIX + '.' + home.replace('/', '.') + '.to_child_execution_job_submission')
    namespace = dict(vars(module))
    exec(compile(ORIGINALS[home]['callback'], '<original-own-axis-HPC-launch-supplier>', 'exec'), namespace)
    return namespace['initial_decision_context']

class _HPCLaunchSupplierChecks:
    module = helpers.LaunchConnectedChecks.module
    connected = helpers.LaunchConnectedChecks.connected

    @pytest.fixture(autouse=True)
    def original_resources_fixture(self, monkeypatch):
        # The existing test helper reads this exact JSON from examples/. Keep
        # the required original test operand with these permanent tests so a
        # copied/installed test view does not depend on repository examples.
        raw = (Path(__file__).parent / 'fixtures/organization_original/hpc_launch_resources.json').read_bytes()
        assert hashlib.sha256(raw).hexdigest() == FIXTURE['resources_fixture_sha256']
        monkeypatch.setattr(helpers, 'resources', lambda: json.loads(raw))

    @pytest.fixture(autouse=True)
    def original_recipient_provenance(self, original_resources_fixture, connected):
        # Use the actual original factory/configuration path, as the existing
        # own-axis connected-information fixture does. This supplies the
        # authenticated recipient authority required by today's registry.
        value = connected
        options = value.execution_options
        factory = self.module('execution_service_setup').ExecutionServiceFactory(
            options['resources'], options['initial_information'],
            options['handoff_unit'], options['acquired_record_unit'], 1.,
            log_window_bytes=options['log_window_bytes'], log_roles=options['log_roles'])
        configuration = self.module('library/execution_initial_information/information_configuration').InitialInformationConfiguration.original_global_factory(factory)
        tools = self.module('tools').ToolRegistry(value.store)
        catalog = configuration.construct(store=value.store, run_id=value.run_id,
            directory=value.directory, tool_registry=tools,
            services=SimpleNamespace(annotation_task_required=lambda: False))
        value.registry.configure_initial_information(catalog,
            self.module('annotation_initial_information').initial_information)

    @pytest.mark.parametrize('context_name', ('context', 'native_context'))
    def test_actual_registry_has_only_original_nearest_supplier(self, connected, context_name):
        value = connected
        context = getattr(value, context_name)
        expected = original_callback(value.parent.binding_path)(value.parent, context)
        assert value.registry.for_path(context.path).binding_path.startswith(value.parent.binding_path + '/execution_job_submission')
        actual = value.registry.initial_decision_context(context)
        assert actual['hpc_execution_job'] == expected['hpc_execution_job']
        providers = []
        for binding in value.registry._context_bindings(context):
            callback = getattr(binding, 'initial_decision_context', None)
            result = {} if callback is None else callback(context)
            if 'hpc_execution_job' in result:
                providers.append(binding.binding_path)
                assert result == expected
        assert providers == [value.parent.binding_path]
        supplied = Path(actual['hpc_execution_job']['supplied_input_file'])
        assert json.loads(supplied.read_text()) == value.plan
        before = supplied.read_bytes()
        assert value.registry.initial_decision_context(context)['hpc_execution_job'] == expected['hpc_execution_job']
        assert supplied.read_bytes() == before

    @pytest.mark.parametrize('context_name', ('context', 'native_context'))
    @pytest.mark.parametrize('changed', ('scope', 'assignment'))
    def test_selected_supplier_keeps_original_identity_rejection(self, connected, context_name, changed):
        value = connected
        context = getattr(value, context_name)
        if changed == 'scope':
            altered = replace(context, scope={'subject_refs': []})
        else:
            assignment = value.runtime._plain(context.assignment)
            assignment['unexpected_identity_operand'] = True
            altered = replace(context, assignment=assignment)
        for callback in (original_callback(value.parent.binding_path), type(value.parent).initial_decision_context):
            with pytest.raises(ValueError, match='^hpc_launch_preparation_identity_conflict$'):
                callback(value.parent, altered)

    def test_nonlaunch_context_keeps_original_empty_result(self, connected):
        value = connected
        assert original_callback(value.parent.binding_path)(value.parent, value.parent_context) == {}
        assert value.parent.initial_decision_context(value.parent_context) == {}

    def test_nonnearest_ancestor_rejects_before_ledger_or_file_access(self, connected, monkeypatch):
        value = connected
        candidates = [binding for binding in value.registry._context_bindings(value.context)
            if binding.binding_path in value.parents and binding is not value.parent]
        module = self.module(value.parent.binding_path + '/to_child_execution_job_submission')
        def forbidden(*args, **kwargs):
            pytest.fail('Nonnearest HPC ancestor opened the original ledger')
        monkeypatch.setattr(module.HPCLedger, 'open_existing', forbidden)
        for binding in candidates:
            assert binding.initial_decision_context(value.context) == {}
            assert binding.initial_decision_context(value.native_context) == {}

class TestDirectHPCSupplier(_HPCLaunchSupplierChecks):
    binding_path = 'hpc_work_planning/execution_job_submission'

class TestAllocationSupplier(_HPCLaunchSupplierChecks):
    binding_path = 'hpc_work_planning/hpc_allocation_execution/execution_job_submission'

class TestScientificHPCSupplier(_HPCLaunchSupplierChecks):
    binding_path = 'scientific_process/hpc_work_planning/execution_job_submission'

class TestScientificAllocationSupplier(_HPCLaunchSupplierChecks):
    binding_path = 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
