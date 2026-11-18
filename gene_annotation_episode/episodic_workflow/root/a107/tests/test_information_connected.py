"""Actual own-axis recipients/readers; no model, native command or network."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources, commission, recorded_queue

AXIS = 'a107'
PREFIX = 'gene_annotation_episode.episodic_workflow.root.' + AXIS + '.'
PARENTS = ('', 'partner_presence_evidence', 'hpc_work_planning',
    'hpc_work_planning/hpc_allocation_execution', 'partner_presence_evidence/hpc_work_planning',
    'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution')


def module(name):
    return importlib.import_module(PREFIX + name.replace('/', '.'))


class InformationCase:
    def __init__(self, directory, *, partial=False, received_resources=None, clients=None, connect=True):
        self.directory = directory
        self.store = module('state').Store(directory / 'store')
        subject, = self.store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        self.scope = {'subject_refs': [subject]}
        self.run_id = AXIS + '-original-information'
        self.journal = module('episode_journal').Journal(self.store, self.run_id)
        self.services = SimpleNamespace(annotation_task_required=lambda: False)
        self.tools = module('tools').ToolRegistry(self.store, **({} if clients is None else {'clients': clients}))
        self.resources = deepcopy(received_resources or resources())
        initial = {key: {'configured_by': 'actual_original_global_factory',
            'retained_inventory': {'resource': key, 'nested': [1, False, None]}} for key in self.resources}
        self.factory = module('execution_service_setup').ExecutionServiceFactory(
            self.resources, initial, 3., 2., 1., log_window_bytes=1024, log_roles=('stdout', 'stderr'))
        self.definition = module('communication').plain(self.factory.as_record())
        library = SimpleNamespace(as_record=lambda: {}, headers=lambda: [])
        science = module('partner_presence_evidence/episode').PartnerPresenceEvidenceEpisode(self.services,
            library=library, tool_library=library,
            child_roles=('partner_presence_evidence', 'hpc', 'launch', 'results', 'monitor', 'literature'))
        self.bindings, self.execution, self.parents, self.contexts = [science], {}, {}, []
        self.hpc_plans, self.hpc_initialization = {}, []
        self.root = self.context((('annotation', 'root'),), {})
        scientific = self.context(self.root.path + (('partner_presence_evidence', 'science'),),
            {'proposed_annotation_ref': 'hypothesis_fixture',
                'selection': {'evidence_axis': {'option_id': AXIS.upper()}}})
        self.parents.update({'': self.root, 'partner_presence_evidence': scientific})
        for home in ('hpc_work_planning', 'partner_presence_evidence/hpc_work_planning'):
            parent = scientific if home.startswith('partner_presence_evidence/') else self.root
            planner = self.context(parent.path + (('hpc', 'planner'),), {'commission_id': 'commission'})
            allocation = self.context(planner.path + (('hpc_execution', 'allocation'),),
                {'commission_id': 'commission', 'owner_episode_id': planner.episode_id})
            self.parents.update({home: planner, home + '/hpc_allocation_execution': allocation})
            for suffix in ('', '/hpc_allocation_execution', '/hpc_resource_prediction'):
                binding = module(home + suffix + '/episode').HPCEpisode(self.services,
                    store=self.store, run_id=self.run_id, directory=directory / 'workflow',
                    resources=resources(), commissions={'commission': commission()})
                self.bindings.append(binding)
                if suffix != '/hpc_resource_prediction':
                    context = self.parents[home + suffix]
                    binding.initialize(context)
                    ledger = binding.state(context)
                    queue_ref = ledger.put('queue', {'snapshot': recorded_queue(module('hpc_queue'))})
                    outcome = asyncio.run(binding.execute(context, 'hpc.plan',
                        {'candidate_id': ledger.commission['candidates'][0]['id'],
                         'model_ref': 'reference_model', 'queue_ref': queue_ref},
                        'information-fixture-plan:' + home + suffix))
                    assert outcome['status'] == 'completed', outcome
                    plan = ledger.read(outcome['result']['plan_ref'])
                    self.hpc_plans[home + suffix] = plan
                    self.hpc_initialization.append({'binding_path': binding.binding_path,
                        'context': context.as_record(), 'owner': ledger.read('owner'),
                        'plan_ref': outcome['result']['plan_ref'], 'plan': plan,
                        'outcome': outcome, 'native_or_provider_operations': 0})
            self.contexts.append(self.context(planner.path + (('hpc_prediction', 'prediction'),),
                {'commission_id': 'commission', 'owner_episode_id': planner.episode_id}))
        for parent_home in PARENTS[2:] if partial else PARENTS:
            prefix = parent_home + '/' if parent_home else ''
            homes = [prefix + 'execution_job_submission',
                *([prefix + 'execution_job_submission/api_job_execution'] if AXIS == 'a107' else []),
                prefix + 'execution_job_submission/local_job_execution',
                prefix + 'execution_job_submission/hpc_job_execution', prefix + 'execution_result_acquisition']
            instances = [module(home + '/episode').ExecutionEpisode(self.services,
                store=self.store, run_id=self.run_id, directory=directory / 'workflow', tool_registry=self.tools,
                **{key: self.definition[key] for key in ('resources', 'initial_information',
                    'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles')}) for home in homes]
            self.execution[parent_home] = {owner.roles[0]: owner for owner in instances}
            self.bindings.extend(instances)
            self.bindings.append(module(prefix + 'execution_progress_assessment/episode').MonitorEpisode(self.services))
            parent = self.parents[parent_home]
            plan = self.hpc_plans.get(parent_home)
            launch_assignment = ({'information_fixture': 'no native admission'}
                if plan is None else plan['launch_assignment'])
            native_assignment = {} if plan is None else plan['practical_assignment']
            launch = self.context(parent.path + (('launch', 'launch'),), launch_assignment)
            self.contexts.extend((launch, self.context(launch.path + (('launch_hpc', 'native'),), native_assignment),
                self.context(parent.path + (('results', 'results'),), {'version': 'execution_results_assignment_v1',
                    'handoff_ref': 'no-native-observation', 'selector': {}})))
            monitor = self.context(parent.path + (('monitor', 'monitor'),),
                {'target_handle': 'no-native-observation', 'requested_fields': ['execution_status']})
            self.contexts.extend((monitor, self.context(monitor.path + (('monitor', 'dependency'),),
                module('communication').plain(monitor.assignment))))
        assert len(self.hpc_plans) == len(self.hpc_initialization) == 4
        (directory / 'hpc-initialization.json').write_text(json.dumps(self.hpc_initialization, indent=2) + '\n')
        self.contexts[0:0] = list(self.parents.values())
        self.registry = module('episode_bindings').EpisodeBindingRegistry(self.bindings)
        expected = (31 if partial else 43) if AXIS == 'a107' else (27 if partial else 37)
        assert len(self.bindings) == expected
        self.owner = next(iter(self.execution.values()))['launch']
        self.configuration = self.catalog = None
        if not connect:
            return
        self.configuration = module('library/execution_initial_information/information_configuration').InitialInformationConfiguration.original_global_factory(self.factory)
        self.catalog = self.configuration.construct(store=self.store, run_id=self.run_id,
            directory=directory / 'workflow', tool_registry=self.tools, services=self.services)
        annotation = module('annotation_initial_information').initial_information
        self.registry.configure_initial_information(self.catalog, annotation)

    def context(self, path, assignment):
        ident = module('method_loop/identities').EpisodeRef(self.run_id, path).episode_id
        request = {'message': {'scope': self.scope, 'episode_assignment': assignment}}
        canonical = module('execution_contracts').canonical
        self.journal.save('runtime_episodes', {'episode_id': ident, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'running'})
        return module('episode_bindings').BindingContext(self.run_id, ident, path[-1][0], path,
            self.scope, assignment, request)

    def close(self):
        self.store.close()


def private_information(case, context):
    if case.catalog is None:
        return case.owner.initial_decision_context(context)
    return case.registry._recipient_initial_information(context)


@pytest.fixture(params=[False, True], ids=['full-private-tree', 'hpc-only-private-tree'])
def case(tmp_path, request):
    value = InformationCase(tmp_path, partial=request.param)
    try:
        yield value
    finally:
        value.close()


def test_reader_identity_mismatch_is_rejected_without_record_changes(case):
    before = list(case.store.db.iterdump())
    with pytest.raises(ValueError, match='initial_information_receiver_identity_conflict'):
        case.registry._recipient_initial_information(replace(case.root, episode_id='unrelated'))
    assert list(case.store.db.iterdump()) == before


def test_selected_explicit_factory_must_match_actual_execution_operands(case):
    Type = type(case.configuration)
    definition = deepcopy(case.definition)
    definition['initial_information'] = {}
    unrelated = module('execution_service_setup').ExecutionServiceFactory.from_record(definition)
    bad = Type.original_global_factory(unrelated).construct(store=case.store, run_id=case.run_id,
        directory=case.directory / 'workflow', tool_registry=case.tools, services=case.services)
    with pytest.raises(ValueError, match='initial_information_recipient_configuration_conflict'):
        case.registry.configure_initial_information(bad, module('annotation_initial_information').initial_information)


def test_multifactory_unknown_custom_recipient_cannot_fall_back(case):
    Type = type(case.configuration)
    rows = [{'recipient': binding.binding_path, 'authority_id': 'explicit'} for binding in case.bindings]
    rows.append({'recipient': '@annotation', 'authority_id': 'explicit'})
    catalog = Type([('explicit', case.factory)], rows).construct(store=case.store,
        run_id=case.run_id, directory=case.directory / 'workflow', tool_registry=case.tools, services=case.services)
    with pytest.raises(ValueError, match='initial_information_recipient_provenance_missing'):
        catalog.original_global_information(case.root)
