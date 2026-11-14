"""Own A108 provider transport over scripted RPC; no inference or grading.

LiteratureWire preserves the original root provider-delivery test's wire
mechanics. Context and scientific assertions use only A108's actual renderer.
"""
import asyncio
from copy import deepcopy
from types import SimpleNamespace

from ..decision_context import INSTRUCTIONS
from ..providers import ModelConnection, _SessionConnection, load_config
from ..library.literature_a108_prompt import A108_CONTEXT_TASK, A108_READING_TASK
from ..published_evidence_assessment.episode import LiteratureEpisode
from ..published_evidence_assessment.task import LiteratureTask


class LiteratureWire(_SessionConnection):
    """Real session complete/presentation implementation, scripted wire only."""

    def __init__(self, directory):
        super().__init__(load_config(), directory, directory.parent)
        self.sent = []
        self.turns = 0

    async def _rpc(self, method, params):
        self.sent.append((method, deepcopy(params)))
        if method == 'thread/start':
            return {'thread': {'id': 'controlled-literature-thread'},
                    'model': params['model'], 'reasoningEffort': params['config']['model_reasoning_effort']}
        assert method == 'turn/start'
        self.turns += 1
        turn = 'controlled-literature-turn-' + str(self.turns)
        self.pending.extend([
            {'method': 'item/completed', 'params': {'threadId': 'controlled-literature-thread',
                'item': {'type': 'agentMessage', 'text': '{"fixture":true}'}}},
            {'method': 'turn/completed', 'params': {'threadId': 'controlled-literature-thread',
                'turn': {'id': turn, 'status': 'completed'}}},
        ])
        return {'turn': {'id': turn}}

    def turns_sent(self):
        return [params for method, params in self.sent if method == 'turn/start']

class LiteratureModel(ModelConnection):
    """Real default outer methods; only serial transport uses the scripted wire."""

    def __init__(self, wire):
        self.wire = wire
        self.worker_lock = asyncio.Lock()

    async def _complete_serial(self, episode_id, role, instructions, context, output_schema, *, prompt_renderer=None):
        return await self.wire.complete(episode_id, role, instructions, context, output_schema,
                                        prompt_renderer=prompt_renderer)


OBJECTIVE = 'Examine whether the reported organism growth conditions establish the supplied sample conditions.'
QUALIFICATION = 'Growth at the reported temperature does not establish the target sample temperature or protein localization.'
SOURCE_TEXT = 'The source organism grew at 38 C; the target sample temperature and intracellular pH were not measured.'
OBSERVATION = 'observation_context_original'
LOOKUP_TEXT = 'Original methods: growth was measured in culture; intracellular conditions were not reported.'
OUTPUT_SCHEMA = {'type': 'object', 'properties': {'fixture': {'const': True}},
                 'required': ['fixture'], 'additionalProperties': False}
INSTRUCTION_TEXT = A108_CONTEXT_TASK + '\n\n' + A108_READING_TASK + '\n' + INSTRUCTIONS


def snapshot():
    return {
        'goal': {'goal_id': 'PRIVATE_GOAL', 'parent_goal_id': 'PRIVATE_PARENT_GOAL', 'objective': OBJECTIVE},
        'scope': {'subject_refs': ['input_scoped_material']},
        'literature_experimental_work': {'version': 'literature_experimental_task_v1',
            'evidence_axis': 'A108', 'aspect': 'source_context_observation'},
        'literature_assignment': {'version': 'literature_assignment_v1', 'source_refs': ['source_selected'],
                                  'question_context_refs': []},
        'literature_source_custody': [{'source_ref': 'source_selected', 'artifact_ref': 'artifact_selected',
                                      'version': 'retained source representation'}],
        'working_state': {'problem_ref': 'PRIVATE_PROBLEM',
            'subjects': [{'id': 'input_scoped_material', 'molecule': 'protein', 'name': 'supplied target'}],
            'sources': [{'id': 'source_unrequested', 'uri': 'UNREQUESTED_SOURCE_INVENTORY'}],
            'observations': [{'id': 'observation_unrequested', 'value': 'UNREQUESTED_OBSERVATION'}]},
        'tools': [{'name': 'source.read', 'description': 'Read the selected retained source byte window.',
            'input_schema': {'type': 'object', 'properties': {
                'source_ref': {'type': 'string'}, 'representation': {'type': 'string'},
                'offset': {'type': 'integer'}, 'limit': {'type': 'integer'}},
                'required': ['source_ref', 'representation', 'offset', 'limit'], 'additionalProperties': False}}],
        'child_options': 'Examine the selected original source for the commissioned contextual question.',
        'requested_report_purpose': 'Return original contextual observations and unresolved target correspondence.',
        'requested_form': {'type': 'object', 'properties': {
            'finding': {'type': 'string', 'description': 'Actual source subject, claim and qualification.'}},
            'required': ['finding'], 'additionalProperties': False},
        'current_report_update': {}, 'current_report_basis_refs': [], 'last_local_outcome': None, 'feedback': None,
        'current_credit': 0, 'controller': {'epoch': 'PRIVATE_EPOCH', 'estimate': {'turns': 2,
            'expected_next_gain': {'value': .5, 'lower': -.1, 'upper': .9, 'status_code': 0,
                                   'uncertainty_code': 2, 'alpha': .05}}, 'decision': {'continuation_cost': .001}},
        'action_yields': {'version': 'own_decision_yield_table_v1', 'rows': [
            {'category': 'tool/source.read', 'completed_actions': 2, 'latest_gain': -.25}]},
        'restored_episode_history': {'entries': ['PRIVATE_RESTORE_HISTORY']},
        'child_reports': [], 'pending_work': {'items': []},
    }


async def complete(wire, state):
    binding = LiteratureEpisode(SimpleNamespace())
    source = object.__new__(LiteratureTask)
    source.episode_id = 'literature-episode'
    source.workflow = SimpleNamespace(provider=LiteratureModel(wire), specialist=lambda _: binding)
    return await source.decision_completion()(source.episode_id, 'REASONING', INSTRUCTION_TEXT, state, OUTPUT_SCHEMA)


def assert_task(text):
    assert text.startswith('TASK\n\n')
    assert text.count('\n\nSTEERING\n') == 1
    task = text.split('\n\nSTEERING\n', 1)[0]
    assert A108_CONTEXT_TASK in task and A108_READING_TASK in task
    for item in (OBJECTIVE, 'source_selected', 'source.read', 'representation', 'offset', 'limit',
                 'Return original contextual observations and unresolved target correspondence.',
                 'Actual source subject, claim and qualification.'):
        assert item in task
    return task


def assert_no_bookkeeping(text):
    for item in ('PRIVATE_GOAL', 'PRIVATE_PARENT_GOAL', 'PRIVATE_PROBLEM', 'PRIVATE_EPOCH',
                 'PRIVATE_RESTORE_HISTORY', 'UNREQUESTED_SOURCE_INVENTORY', 'UNREQUESTED_OBSERVATION',
                 'decision_bootstrap supplies', 'restored_pending_decision_index',
                 'DO_NOT_RENDER_RESPONSE_TRANSCRIPT', 'base_revision', 'removed_fields'):
        assert item not in text
