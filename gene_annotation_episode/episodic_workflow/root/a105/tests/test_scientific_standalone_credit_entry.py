"""Characterize actual raw Workflow scientific-root construction without work.

The published library is frozen unchanged for this constructor check. The projector is an explicit caller
fixture; no provider, native operation, Episode loop or controller is executed.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a105.runtime import Workflow, TypedReportContract
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.episode import ScientificProcessEpisode
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.task import ScientificTask
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.episodic_workflow.root.a105.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a105.native_timing_information import NativeTimingInformation


@pytest.mark.parametrize('standalone,credit', [(True, 2.5), (True, {'mode': 'annotation_axis_credit', 'arms': []}), (False, 2.5)])
@pytest.mark.parametrize('native_information', [False, True])
def test_original_scientific_projector_and_optional_timing_scope(tmp_path, standalone, credit, native_information):
    library = ScientificProcessLibrary.freeze(tmp_path / 'scientific-process-library',
        source=Path(__file__).resolve().parents[5] / 'research/slotted_process_library/publications/2026-10-24-001')
    tool_library = ScientificToolLibrary.freeze(tmp_path / 'tool-library', catalog=[], tool_info=True)
    calls = []
    class Projector:
        def __call__(self, store, scope, **arguments):
            calls.append(deepcopy(arguments))
            return {'credit': deepcopy(credit), 'proposed_annotations': [], 'comparisons': []}

        def as_record(self):
            return {'kind': 'controlled_scientific_input_projector', 'version': 'fixture_v1'}

    projector = Projector()
    def unused(*args, **kwargs):
        pytest.fail('construction must not execute provider, controller or native work')
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MAAA', molecule='protein')
        scope = store.validate_scope()
        workflow = Workflow(store, ToolRegistry(store, clients=SimpleNamespace()),
            SimpleNamespace(complete=unused), tmp_path / 'run', 'standalone-scientific',
            unused, projector, root_role='scientific_process',
            episode_record_receipts=not standalone, initial_known_record_refs=[],
            native_timing_information=NativeTimingInformation(1) if native_information else None,
            episode_binding_factories=[lambda services: ScientificProcessEpisode(services,
                library=library, tool_library=tool_library, child_roles=('scientific_process',))])
        binding = workflow.scientific_process_binding
        schema = {'type': 'object', 'properties': {'execution_state': {
            'type': 'string', 'enum': ['not_executed', 'executed'],
            'description': 'Whether the constructed engineering fixture has executed a selected unit; this is not an evidence finding.'}},
            'required': ['execution_state'], 'additionalProperties': False}
        initial = {'execution_state': 'not_executed'}
        contract = TypedReportContract('Return the original engineering fixture', schema, lambda *_: True)
        assignment = {'selection': {'version': 'scientific_process_selection_v3',
            'evidence_axis': library.reference('A105'), 'thought_pattern': library.reference('P01'), 'child_tool_info': []},
            'evidence_refs': [], 'constraints': {}, 'context': {'evidence_task': {
                'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings', 'evidence_axis': 'A105', 'credit_unit': 1}}}
        with pytest.raises(ContractError, match='scientific_parent_invocation_required'):
            binding.prepare_assignment(None, 'scientific_process', assignment, scope, 'prepare')
        # This controls preparation inputs only; it grants no journal commission.
        parent = BindingContext(workflow.run_id, 'preparation-context', 'annotation',
            (('annotation', 'preparation'),), scope, {}, {'message': {'scope': scope, 'episode_assignment': {}}})
        prepared = binding.prepare_invocation(parent, 'scientific_process', assignment, scope,
            'engineering:prepare', invocation={'objective': 'Characterize standalone input presentation',
                'purpose': contract.decision, 'report_schema': schema, 'initial_report': initial})
        parent_path = ()
        parent_goal = None
        if not standalone:
            parent_episode = workflow.build('scientific_process', 'commissioning-parent',
                'Characterize standalone input presentation', scope, contract=contract, initial=initial,
                episode_assignment=prepared['assignment'], scientific_process=prepared['scientific_process'])
            actual_parent = workflow.binding_context(parent_episode.source)
            binding.validate_context(actual_parent)
            prepared = binding.prepare_invocation(actual_parent, 'scientific_process', assignment, scope,
                'engineering:prepare-recursive-child', invocation={'objective': 'Characterize standalone input presentation',
                    'purpose': contract.decision, 'report_schema': schema, 'initial_report': initial})
            parent_path = actual_parent.path
            parent_goal = parent_episode.source.request.goal
        calls_before_child = deepcopy(calls)
        episode = workflow.build('scientific_process', 'standalone',
            'Characterize standalone input presentation', scope, contract=contract, initial=initial,
            episode_assignment=prepared['assignment'], scientific_process=prepared['scientific_process'],
            parent_path=parent_path, parent=parent_goal)
        source = episode.source
        assert type(source) is ScientificTask
        assert source.path == (*parent_path, ('scientific_process', 'standalone'))
        context = workflow.binding_context(source)
        binding.validate_context(context)
        actual = workflow.source_credit_view(source)
        if standalone:
            assert workflow.scientific_projector_for_context(context) is projector
            assert actual['credit'] == credit
            assert calls and all(arguments == {} for arguments in calls)
        else:
            assert workflow.scientific_projector_for_context(context).as_record()['kind'] == 'received_scientific_finding_progress'
            assert actual['credit'] == 0 and actual['retained_finding_count'] == 0
            # The current scalar view forwards only its original whitelist.
            assert 'source_contributions' not in actual
            assert calls_before_child and all(arguments == {} for arguments in calls_before_child)
            assert calls == calls_before_child
        if native_information:
            assert actual['monitoring_information_credit'] == 0
            assert actual['monitoring_information_binding']['scientific_credit'] is False
        else:
            assert 'monitoring_information_credit' not in actual
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
