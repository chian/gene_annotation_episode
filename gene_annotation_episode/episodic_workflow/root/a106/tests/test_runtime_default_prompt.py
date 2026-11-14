"""Construct the actual offline workflow and compose its original fallback prompt."""
from ..method_loop import EpisodeGoal, EpisodeRequest
from ..runtime import DecisionSource, Record, Workflow
from ..runtime_prompt import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT
from ..state import Store
from ..tools import ToolRegistry


def test_actual_workflow_composes_prompt_without_native_event_provider(tmp_path):
    def not_selected(*args, **kwargs):
        raise AssertionError('Prompt composition must not select scientific work')

    class UnusedProvider:
        async def complete(self, *args, **kwargs):
            raise AssertionError('Prompt composition must not call a provider')

    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        scope = store.validate_scope()
        workflow = Workflow(store, ToolRegistry(store), UnusedProvider(),
            tmp_path / 'workflow', 'original-default-prompt', not_selected,
            not_selected, episode_binding_factories=())
        request = EpisodeRequest(
            EpisodeGoal.root(objective='Examine the supplied material',
                             result_contract={'role': 'annotation'}),
            Record({'scope': scope, 'initial_report': {}}), None)
        source = DecisionSource(workflow, (('annotation', 'original'),), request, scope)
        instructions = source.instructions({})
        assert instructions.startswith(INSTRUCTIONS)
        assert REASONING_COMMIT_REQUIREMENT in instructions
        assert 'pending_child_' in instructions
        assert 'native_event_targets input' not in instructions
        assert workflow.native_event_information is None
        assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0] == 0
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0
        assert store.db.execute('SELECT COUNT(*) FROM runtime_model_calls').fetchone()[0] == 0
