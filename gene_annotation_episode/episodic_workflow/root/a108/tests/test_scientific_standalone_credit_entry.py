"""Characterize actual raw Workflow scientific-root construction without work.

The captured library is immutable input. The projector is an explicit caller
fixture; no provider, native operation, Episode loop or controller is executed.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a108.runtime import Workflow, TypedReportContract
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.episode import ScientificProcessEpisode
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.task import ScientificTask
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.episodic_workflow.root.a108.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.episodic_workflow.root.a108.state import Store
from gene_annotation_episode.episodic_workflow.root.a108.tools import ToolRegistry


@pytest.mark.parametrize('credit', [2.5, {'mode': 'annotation_axis_credit', 'arms': []}])
def test_raw_scientific_root_keeps_actual_caller_projector(tmp_path, credit):
    library = ScientificProcessLibrary(Path(__file__).parent / 'fixtures/retained_protein_reader_336/run/scientific-process-library')
    tool_library = ScientificToolLibrary.freeze(tmp_path / 'tool-library', catalog=[], tool_info=True)
    calls = []
    def projector(store, scope, **arguments):
        calls.append(deepcopy(arguments))
        return {'credit': deepcopy(credit), 'proposed_annotations': [], 'comparisons': []}
    projector.as_record = lambda: {'kind': 'controlled_standalone_projector', 'unit': 1.0}
    def unused(*args, **kwargs):
        pytest.fail('construction must not execute provider, controller or native work')
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MAAA', molecule='protein')
        scope = store.validate_scope()
        workflow = Workflow(store, ToolRegistry(store, clients=SimpleNamespace()),
            SimpleNamespace(complete=unused), tmp_path / 'run', 'standalone-scientific',
            unused, projector, root_role='scientific_process',
            episode_binding_factories=[lambda services: ScientificProcessEpisode(services,
                library=library, tool_library=tool_library, child_roles=('scientific_process',))])
        binding = workflow.scientific_process_binding
        schema = {'type': 'object', 'properties': {'inspection_status': {
            'type': 'string', 'enum': ['not_started'],
            'description': 'Controlled construction fixture; no action or evidence assessment performed.'}},
            'required': ['inspection_status'], 'additionalProperties': False}
        contract = TypedReportContract('Return the original engineering fixture', schema, lambda *_: True)
        assignment = {'selection': {'version': 'scientific_process_selection_v3',
            'evidence_axis': library.reference('A108'), 'thought_pattern': library.reference('P01'), 'child_tool_info': []},
            'evidence_refs': [], 'constraints': {}, 'context': {'evidence_task': {
                'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings', 'evidence_axis': 'A108', 'credit_unit': 1}}}
        with pytest.raises(ContractError, match='scientific_parent_invocation_required'):
            binding.prepare_assignment(None, 'scientific_process', assignment, scope, 'prepare')
        # This controls preparation inputs only; it grants no journal commission.
        parent = BindingContext(workflow.run_id, 'preparation-context', 'annotation',
            (('annotation', 'preparation'),), scope, {}, {'message': {'scope': scope, 'episode_assignment': {}}})
        prepared = binding.prepare_invocation(parent, 'scientific_process', assignment, scope,
            'engineering:prepare', invocation={'objective': 'Characterize standalone input presentation',
                'purpose': contract.decision, 'report_schema': schema, 'initial_report': {'inspection_status': 'not_started'}})
        episode = workflow.build('scientific_process', 'standalone',
            'Characterize standalone input presentation', scope, contract=contract, initial={'inspection_status': 'not_started'},
            episode_assignment=prepared['assignment'], scientific_process=prepared['scientific_process'])
        source = episode.source
        assert type(source) is ScientificTask
        assert source.path == (('scientific_process', 'standalone'),)
        context = workflow.binding_context(source)
        binding.validate_context(context)
        assert workflow.scientific_projector_for_context(context) is projector
        assert workflow.source_credit_view(source)['credit'] == credit
        assert calls and all(arguments == {} for arguments in calls)
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
