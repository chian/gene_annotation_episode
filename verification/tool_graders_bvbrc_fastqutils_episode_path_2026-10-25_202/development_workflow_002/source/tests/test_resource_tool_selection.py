"""Bound resource information is selectable without granting direct execution.

All transports and decisions are fixtures. No service, native computation or
HPC resource is contacted by these declaration/construction checks.
"""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.assembled_service_setup import bind_assembled_services
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.resource_tool_information import bound_resource_tool_contracts
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_records import selector_selection
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_information import selectors
from gene_annotation_episode.tools import ToolRegistry
from test_hmmer_grading_publication import (QUERY, RetainedClient,
    prohibit_live_network_and_native_execution)
from test_published_axis_workflow import PUBLICATION, ScriptedDecisions, StopBeforeDecision, select


CONFIG = {'version': 'scientific_tool_retrieval_v1', 'mode': 'semantic_fast_v1',
    'model': {'model': 'gpt-6-luna', 'reasoning_effort': 'none'}}
SCIENTIFIC_FORM = {'type': 'object', 'additionalProperties': False,
    'properties': {'records': {'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
        'x-source': 'committed_record_refs'}}, 'required': ['records']}


class ResourceCase:
    def __init__(self, tmp_path, store, *, resources=None, child_roles=None,
                 sequence=QUERY, client=None, retrieval=None):
        self.store, self.directory = store, tmp_path/'run'
        self.run_id = 'resource-tool-information-fixture'
        self.client = client or RetainedClient()
        self.tools = ToolRegistry(store, clients=self.client)
        self.target, = store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs']
        self.scope = {'subject_refs': [self.target]}
        self.resources = {'ebi': {'kind': 'hmmer_api'}} if resources is None else resources
        self.roles = child_roles or ('scientific_process', 'launch', 'results')
        self.retrieval = retrieval or {'version': 'scientific_tool_retrieval_v1', 'mode': 'literal_test_v1'}
        application = self.assemble()
        self.descriptor = application.episode_binding_descriptors[0]
        self.library = ScientificProcessLibrary(self.directory/'scientific-process-library')
        self.controllers = {}

    def assemble(self):
        return bind_assembled_services(self.store, run_id=self.run_id, directory=self.directory,
            job_episodes=None, resource_estimator=None, source_directory=PUBLICATION,
            tool_catalog=self.tools.catalog(), tool_registry=self.tools, tool_retrieval=self.retrieval,
            scientific_child_roles=self.roles, handoff_unit=3, acquired_record_unit=2,
            monitoring_information_unit=.5, literature_outcome_page_size=10,
            monitor_outcome_page_size=10, log_window_bytes=8192, log_roles=('stdout', 'stderr'),
            execution_resources=self.resources, initial_execution_information={})

    def commission(self, selected):
        return {'kind': 'episode_child', 'role': 'scientific_process',
            'goal': 'Investigate the supplied protein using its selected native measurements.',
            'scope': self.scope, 'purpose': 'Return actual acquired numerical records; no function verdict.',
            'schema_json': json.dumps(SCIENTIFIC_FORM), 'initial_report_json': '{}',
            'assignment': {'selection': {'version': 'scientific_process_selection_v3',
                'evidence_axis': self.library.reference('A104'),
                'thought_pattern': self.library.reference('P01'), 'child_tool_info': selected},
                'evidence_refs': [self.target], 'constraints': {'preserve_original_query': True},
                'context': {'molecule': 'protein', 'complete': True}}}

    def workflow(self, provider, *, scientific_actions=2):
        application = self.assemble()
        def controller(path, initial):
            def estimate(history, parameters, contexts):
                count = 1 if path[-1][0] == 'annotation' else scientific_actions
                return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1),
                    parameters, {'fixture': 'explicit_scientific_choices_only'})
            result = YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=estimate if path[-1][0] in {'annotation', 'scientific_process'} else None)
            self.controllers[path] = result
            return result
        return Workflow(self.store, self.tools, provider, self.directory, self.run_id,
            controller_factory=controller, project_credit=lambda *_: 0,
            episode_binding_descriptors=application.episode_binding_descriptors,
            role_credit_bindings=application.role_credit_bindings,
            job_progress_provider=application.job_progress_provider,
            episode_record_receipts=True, initial_known_record_refs=[],
            decision_protocol='decision_exchange_v1', annotation_child_roles=('scientific_process',))


def full_resources(tmp_path):
    return {'ebi': {'kind': 'hmmer_api'}, 'ebi-second': {'kind': 'hmmer_api'},
        'uniprot': {'kind': 'api', 'service': 'uniprot'},
        'blast': {'kind': 'api', 'service': 'ncbi_blast'},
        'bvbrc': {'kind': 'api', 'service': 'bvbrc_data'},
        'here': {'kind': 'local', 'workspace': str(tmp_path/'local'), 'policy': {
            'memory_bytes': 20*1024**3, 'scratch_bytes': 4*1024**3, 'wall_seconds': None}},
        'configured-pbs': {'kind': 'pbs_ssh', 'workspace': str(tmp_path/'pbs'),
            'ssh_argv': ['unexecuted-ssh', 'fixture'], 'python_executable': '/usr/bin/python3',
            'account': 'EpiCalib'}}


def test_actual_bound_contracts_include_resource_variants_and_no_assignment_or_execution(tmp_path, monkeypatch):
    with Store(tmp_path/'state') as store:
        case = ResourceCase(tmp_path, store, resources=full_resources(tmp_path))
        workflow = case.workflow(ScriptedDecisions([]))
        family = workflow.episode_bindings.for_role('launch')
        def prohibited(*args, **kwargs):
            pytest.fail('information retrieval used a context-dependent operation or prepared work')
        monkeypatch.setattr(family, 'catalog', prohibited)
        monkeypatch.setattr(family, 'prepare_assignment', prohibited)
        monkeypatch.setattr(family.api_execution, 'catalog', prohibited)
        monkeypatch.setattr(family.api_execution, 'validate_assignment', prohibited)
        before = [tuple(row) for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        direct = workflow.services.tool_catalog(case.scope)
        available = workflow.services.tool_information_catalog(case.scope)
        indexed = {(row['name'], row['resources']): row for row in available}
        for name in ('api.hmmer.result', 'api.blast.fetch', 'api.uniprot.collect', 'api.bvbrc.result'):
            assert indexed[name, 'api']['invocation_route']['kind'] == 'commission'
            assert name not in {row['name'] for row in direct}
        routes = indexed['api.hmmer.result', 'api']['invocation_route']['routes']
        assert routes == [{'entry_role': 'results', 'resource_id': resource,
                          'resource_role': 'results'} for resource in ('ebi', 'ebi-second')]
        for kind in ('local', 'hpc'):
            assert indexed['practical.job.start', kind]['invocation_route']['kind'] == 'commission'
            assert ('sequence.align', 'hpc') not in indexed
            assert ('homology.submit', kind) not in indexed
        assert indexed['sequence.inspect', 'local']['invocation_route'] == {'kind': 'direct'}
        assert all(row['invocation_route']['kind'] == 'commission'
                   for row in bound_resource_tool_contracts(family))
        assert workflow.services.tool_catalog(case.scope) == direct
        assert case.client.calls == []
        assert [tuple(row) for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")] == before
        for table in ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'tool_operations'):
            assert store.db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0


@pytest.mark.parametrize('child_roles', [('scientific_process',), ('scientific_process', 'launch')])
def test_information_requires_the_bound_service_and_the_scientific_child_edge(tmp_path, child_roles):
    with Store(tmp_path/'state') as store:
        case = ResourceCase(tmp_path, store, child_roles=child_roles)
        workflow = case.workflow(ScriptedDecisions([]))
        library = workflow.scientific_process_binding.tool_library
        available = workflow.services.tool_information_catalog(case.scope)
        actual = {(r['name'], r['resources']) for r in library.parent_tool_info(available)}
        assert ('api.hmmer.result', 'api') not in actual  # No results edge.
        assert (('api.hmmer.submit', 'api') in actual) == ('launch' in child_roles)
        assert ('api.uniprot.collect', 'api') not in actual  # Globally described; service unbound.
        assert ('practical.job.start', 'hpc') not in actual
        assert ('api.uniprot.collect', 'api') in {(r['name'], r['resources']) for r in library.parent_tool_info()}
        with pytest.raises(ValueError, match='contract_changed'):
            workflow.scientific_process_binding._assignment(case.commission([
                {'name': 'api.uniprot.collect', 'resources': 'api'}])['assignment'], case.scope, materialize=True)


def test_multiple_resource_variants_materialize_frozen_information_but_never_direct_calls(tmp_path):
    with Store(tmp_path/'state') as store:
        case = ResourceCase(tmp_path, store, resources=full_resources(tmp_path))
        selected = [{'name': 'sequence.inspect', 'resources': 'local'},
            {'name': 'api.hmmer.result', 'resources': 'api'},
            *({'name': 'practical.job.start', 'resources': kind} for kind in ('local', 'hpc'))]
        commission = case.commission(selected)
        provider = ScriptedDecisions([select(commission), StopBeforeDecision()])
        workflow = case.workflow(provider)
        root = workflow.build('annotation', 'root', 'Investigate supplied sequence', case.scope)
        with pytest.raises(StopBeforeDecision):
            asyncio.run(root.run_async(workflow.context))
        child = workflow.selected(root.source, commission, 0).child
        context = workflow.binding_context(child.source)
        binding = workflow.scientific_process_binding
        info = context.assignment['selection']['child_tool_info']
        assert all(set(row) == {'name', 'description', 'resources', 'instructions'} for row in info)
        assert info[2]['instructions'] != info[3]['instructions']
        assert {row['name'] for row in binding.catalog(context)} == {'sequence.inspect', 'process.revise'}
        assert workflow.catalog(case.scope, source=root.source) == []
        for name in ('api.hmmer.result', 'practical.job.start'):
            result = asyncio.run(binding.execute(context, name, {}, 'forbidden-direct'))
            assert result['status'] == 'invalid' and result['feedback']['code'] == 'scientific_operation_unavailable'
            assert name not in binding.common_tool_names(context)
        assert case.client.calls == [] and store.db.execute('SELECT count(*) FROM tool_operations').fetchone()[0] == 0


@pytest.mark.parametrize('mutation', ['schema', 'name', 'instructions', 'description', 'unknown'])
def test_frozen_selection_rejects_changed_contract_information_and_unknown_operations(tmp_path, mutation):
    with Store(tmp_path/'state') as store:
        case = ResourceCase(tmp_path, store)
        workflow = case.workflow(ScriptedDecisions([]))
        binding = workflow.scientific_process_binding
        library = binding.tool_library
        selected = [{'name': 'api.hmmer.result', 'resources': 'api'}]
        available = workflow.services.tool_information_catalog(case.scope)
        if mutation in {'schema', 'name'}:
            row = next(r for r in available if r['name'] == 'api.hmmer.result')
            if mutation == 'schema':
                row['input_schema'] = {'type': 'object', 'properties': {'wrong': {'type': 'string'}}}
            else:
                row['name'] = 'different.operation'
            with pytest.raises(ValueError, match='contract_changed'):
                library.resolve_tool_info(selected, available)
        else:
            if mutation == 'unknown':
                selected[0]['name'] = 'api.imagined.result'
            else:
                selected = library.resolve_tool_info(selected, available)
                selected[0][mutation] += ' invented change'
            with pytest.raises(ValueError, match='unknown|info_changed'):
                library.resolve_tool_info(selected, available)
        assert case.client.calls == []


def test_revised_child_resource_selection_preserves_original_owner_and_frozen_records(tmp_path):
    with Store(tmp_path/'state') as store:
        case = ResourceCase(tmp_path, store)
        original = case.commission([{'name': 'sequence.inspect', 'resources': 'local'}])
        arguments = {'thought_pattern': case.library.reference('P02'),
            'child_tool_info': [{'name': 'api.hmmer.result', 'resources': 'api'}]}
        provider = ScriptedDecisions([select(original), select({'kind': 'tool', 'tool': 'process.revise',
            'arguments': arguments}), StopBeforeDecision()])
        workflow = case.workflow(provider)
        root = workflow.build('annotation', 'root', 'Investigate supplied sequence', case.scope)
        with pytest.raises(StopBeforeDecision):
            asyncio.run(root.run_async(workflow.context))
        owner = workflow.selected(root.source, original, 0).child
        before = deepcopy(owner.request.as_record())
        outcome = json.loads(workflow.journal.row('runtime_actions', owner.source.episode_id, 0)['result'])
        assert outcome['status'] == 'completed'
        revised = case.commission(selectors(outcome['result']['selection']['child_tool_info']))
        revised['assignment']['selection'] = selector_selection(outcome['result']['selection'])
        revised['assignment']['revision_origin'] = outcome['revision_origin']
        child = workflow.selected(owner.source, revised, 1).child
        context = workflow.binding_context(child.source)
        assert context.assignment['selection']['child_tool_info'][0]['name'] == 'api.hmmer.result'
        assert {r['name'] for r in workflow.scientific_process_binding.catalog(context)} == {'process.revise'}
        assert owner.request.as_record() == before
        assert case.client.calls == []
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
        frozen = (case.directory/'scientific-tool-library/index.json').read_bytes()
        restored = case.workflow(ScriptedDecisions([]))
        restored_root = restored.build('annotation', 'root', 'Investigate supplied sequence', case.scope)
        restored_owner = restored.selected(restored_root.source, original, 0).child
        restored_child = restored.selected(restored_owner.source, revised, 1).child
        assert restored_child.request.as_record() == child.request.as_record()
        assert (case.directory/'scientific-tool-library/index.json').read_bytes() == frozen


def test_explicit_declared_instructions_are_frozen_exactly_and_reject_changed_binding(tmp_path):
    with Store(tmp_path/'state') as store:
        case = ResourceCase(tmp_path, store)
        workflow = case.workflow(ScriptedDecisions([]))
        contract = next(row for row in bound_resource_tool_contracts(
            workflow.episode_bindings.for_role('launch')) if row['name'] == 'api.hmmer.result')
        contract['instructions'] = ('Fixture-only supplied instructions: retain exact native bytes, '
            'grade the original query and return the requested numerical records through results.')
        directory = tmp_path/'explicit-information'
        descriptor = prepare_scientific_binding(run_directory=directory, source_directory=PUBLICATION,
            tool_catalog=case.tools.catalog(), child_roles=case.roles,
            resource_catalogs={'api': [contract]})
        library = ScientificToolLibrary(directory/'scientific-tool-library')
        selected = [{'name': 'api.hmmer.result', 'resources': 'api'}]
        info, = library.resolve_tool_info(selected, [contract])
        assert info['instructions'] == contract['instructions']
        assert set(info) == {'name', 'description', 'resources', 'instructions'}
        saved = (library.directory/'index.json').read_bytes()
        reopened = ScientificToolLibrary.freeze(library.directory, catalog=case.tools.catalog(),
            tool_info=True, resource_catalogs={'api': [contract]})
        assert reopened.as_record() == descriptor['configuration']['tool_library']
        altered = deepcopy(contract)
        altered['instructions'] += ' Changed.'
        with pytest.raises(ValueError, match='contract_changed'):
            library.resolve_tool_info(selected, [altered])
        with pytest.raises(ValueError, match='catalog_changed'):
            ScientificToolLibrary.freeze(library.directory, catalog=case.tools.catalog(),
                tool_info=True, resource_catalogs={'api': [altered]})
        assert (library.directory/'index.json').read_bytes() == saved
