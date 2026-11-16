"""Prediction instructions and exact HPC operands, without provider/native execution."""
from copy import deepcopy
import hashlib
import importlib
from types import SimpleNamespace

import pytest

from .hpc_prediction_inputs import commission, resources


class PredictionPromptChecks:
    def module(self, suffix):
        return importlib.import_module('gene_annotation_episode.episodic_workflow.root.'+self.axis+'.'+suffix)

    def prompt_setup(self, tmp_path, *, protocol=None):
        module = self.module(self.binding_path.replace('/', '.')+'.episode')
        binding = module.HPCEpisode(None, store=None, run_id='prompt', directory=tmp_path,
            resources=resources(), commissions={'commission': commission()})
        task = object.__new__(binding.decision_source_type)
        task.episode_id = 'prediction'
        task.path = (('hpc', 'original'), ('hpc_prediction', 'original'))
        task.scope = {'subject_refs': []}
        context = SimpleNamespace(role='hpc_prediction')
        task.workflow = SimpleNamespace(specialist=lambda source: binding, binding_context=lambda source: context,
            is_job_source=lambda source: False, permits_common_action=lambda source, action: action == 'tool',
            native_event_information=None, decision_protocol=protocol,
            knowledge=SimpleNamespace(instructions='\nOriginal knowledge guidance.'),
            launch_instructions=SimpleNamespace(instructions='\nOriginal resource-library guidance.'),
            services=SimpleNamespace(instructions=self.module('runtime_prompt').instructions))
        if self.axis in ('a102', 'a103', 'a104'):
            task.workflow.services = self.module('episode_services').WorkflowServices(task.workflow)
        return task, binding, context

    def renderer(self, binding):
        if self.axis == 'a104':
            return self.module('library.hpc_prompt').render_hpc_prompt
        if hasattr(binding, 'decision_prompt_renderer'):
            return binding.decision_prompt_renderer
        return self.module('hpc_prompt').render_hpc_prompt

    @pytest.mark.parametrize('protocol', [None, 'decision_exchange_v1'])
    @pytest.mark.parametrize('knowledge,launch', [(False, False), (False, True), (True, False), (True, True)])
    def test_exact_goal_and_selected_library_guidance(self, tmp_path, protocol, knowledge, launch):
        task, binding, context = self.prompt_setup(tmp_path, protocol=protocol)
        fields = {**({'tool_knowledge': {}} if knowledge else {}),
                  **({'launch_instruction_library': {}} if launch else {})}
        text = task.instructions(fields)
        assert text.startswith(binding.instructions(context))
        assert ('Original knowledge guidance.' in text) == knowledge
        assert ('Original resource-library guidance.' in text) == launch
        assert 'fixed reference and validation set cannot change' in text
        assert 'Unknown inputs stay unknown' in text
        assert 'same_source_claim_as_ref' not in text and 'assessment.investigation_finding' not in text
        assert 'A pending_child_ handle' not in text and 'native_event_targets input' not in text

    def test_frozen_candidate_identity_and_utf8_bytes_are_preserved(self, tmp_path):
        _, binding, _ = self.prompt_setup(tmp_path)
        raw = '# original α bytes\n'
        state = {'hpc_commission': {'objective': 'Compare original candidates'},
            'hpc_candidates': [{'id': 'original-candidate', 'files': [
                {'path': 'original-input.py', 'text': raw, 'sha256': 'original-declared-digest'}]}],
            'hpc_model_ref': 'model-original', 'hpc_model_support': {'quality': None},
            'last_local_outcome': {'status': 'invalid', 'feedback': {'code': 'original-missing-model'}},
            'requested_action_history': [{'outcome': {'status': 'failed', 'result': {'stderr': 'original-diagnostic'}}}]}
        original = deepcopy(state)
        text = self.renderer(binding)(state, 'Original task')
        assert state == original
        assert raw not in text and hashlib.sha256(raw.encode()).hexdigest() in text
        assert 'text_size_bytes: '+str(len(raw.encode())) in text
        for expected in ('original-candidate', 'original-input.py', 'original-declared-digest',
                         'model-original', 'quality: unknown', 'original-missing-model', 'original-diagnostic'):
            assert expected in text

    def test_requested_report_facts_and_unknown_lookup_remain_distinct(self, tmp_path):
        _, binding, _ = self.prompt_setup(tmp_path)
        state = {'hpc_commission': {'objective': 'Original prediction'},
            'requested_form': {'properties': {'answer': {'x-source': 'requested_result'}}},
            'available_report_facts': {'requested_result': 'source-original', 'hpc_model_ref': 'model-original',
                'unrequested_science': 'unrequested-source'}}
        text = self.renderer(binding)(state, 'Original task', lookup_results=[{'status': 'unavailable', 'estimate': None}])
        assert 'source-original' in text and 'model-original' in text
        assert 'unrequested-source' not in text
        assert 'unavailable' in text and 'estimate: unknown' in text

    def test_ordinary_provider_rendering_preserves_actual_operands(self, tmp_path):
        _, binding, _ = self.prompt_setup(tmp_path)
        providers = self.module('providers')
        connection = object.__new__(providers._SessionConnection)
        connection.scientific_prompt_states = {}
        state = {'hpc_commission': {'objective': 'Original prediction'}, 'hpc_model_ref': 'model-original'}
        text, instructions = connection._presentation('prediction', 'REASONING', 'Original task', state)
        assert text == self.renderer(binding)(state, 'Original task')
        assert instructions == providers.text_instructions('Original task')
        assert connection.scientific_prompt_states[('prediction', 'REASONING')] == state

    @pytest.mark.parametrize('declared', [False, True])
    def test_provider_frames_retain_model_updates_and_received_lookup(self, tmp_path, declared):
        _, binding, _ = self.prompt_setup(tmp_path)
        runtime, providers = self.module('runtime'), self.module('providers')
        connection = object.__new__(providers._SessionConnection)
        connection.scientific_prompt_states = {}
        first = {'hpc_commission': {'objective': 'Original prediction'}, 'hpc_model_ref': 'model-before'}
        second = {**first, 'hpc_model_ref': 'model-after'}
        options = {'prompt_renderer': binding.decision_prompt_renderer} if declared else {}
        for frame, state in ((runtime.state_frame(first), first), (runtime.state_frame(second, first), second)):
            text, _ = connection._presentation('prediction', 'REASONING', 'Original task', frame, **options)
            assert text == self.renderer(binding)(state, 'Original task')
        result = {'status': 'unavailable', 'model_quality': None}
        frame = {'version': runtime.DECISION_CONTEXT_VERSION, 'kind': 'decision_lookup_result',
            'decision_index': 0, 'exchange_index': 1, 'result': result}
        text, _ = connection._presentation('prediction', 'REASONING', 'Original task', frame, **options)
        assert text == self.renderer(binding)(second, 'Original task', lookup_results=[result])
        assert connection.scientific_prompt_states[('prediction', 'REASONING')] == second

    def test_private_composer_omits_unavailable_child_repair(self, tmp_path, monkeypatch):
        task, binding, context = self.prompt_setup(tmp_path)
        if self.axis in ('a102', 'a103', 'a104'):
            monkeypatch.setattr(self.module('runtime_prompt'), 'instructions', lambda *args: pytest.fail('Axis composer selected'))
        else:
            task.workflow.services.instructions = lambda *args: pytest.fail('Axis composer selected')
        assert task.instructions({}) == binding.instructions(context)
        assert 'pending_child_delivery' not in task.instructions({})
        assert binding.allowed_children(context, {}) == ()
        assert binding.permitted_common_actions(context) == ('tool',)

    @pytest.mark.parametrize('protocol', [None, 'decision_exchange_v1'])
    @pytest.mark.parametrize('declared', [False, True])
    def test_actual_decision_dispatch_and_saved_replay_keep_private_presentation(self, tmp_path, protocol, declared):
        import asyncio
        import json
        from .hpc_prediction_parent_exchange import PredictionReceiptDatabase
        task, binding, _ = self.prompt_setup(tmp_path, protocol=protocol)
        runtime = self.module('runtime')
        database = PredictionReceiptDatabase(tmp_path/'prompt-journal.sqlite')
        journal = self.module('episode_journal').Journal(database, 'run')
        self.module('episode_completion').CompletionLedger(database, journal)
        exchanges = self.module('decision_exchanges').DecisionExchanges(journal)
        task.calls = 0
        task._model_snapshot = task._presented_conversation_key = None
        task.decision_inputs = lambda context, index, profile: context
        task.workflow.run_id = 'run'
        task.workflow.store = database
        task.workflow.journal = journal
        task.workflow.decision_exchanges = exchanges
        task.workflow.controller_binding = {}
        task.workflow.contract_information_profile = lambda source: None
        task.workflow.receipts = None
        task.workflow.available_child_roles = lambda source: ()
        task.workflow.scientific_library_available = lambda source: False
        task.workflow.services.decision_exchange_instructions = lambda: self.module('decision_context').INSTRUCTIONS
        state = {'hpc_commission': {'objective': 'Original prediction question'}, 'hpc_model_ref': 'model-original'}
        selection = {'kind': 'tool', 'tool': 'hpc.read', 'arguments': {'reference': 'model-original'}}
        response = {'selection': selection, 'report_update': {}}
        wire = {'response': {'response_type': 'select_action', **response}} if protocol else response
        calls = []
        async def complete(*args, **kwargs):
            calls.append((args, kwargs))
            return wire
        if declared and self.axis == 'a104':
            controlled = self.module('tests.provider_dispatch_fixtures')
            task.workflow.provider = controlled.controlled_serial_model(
                controlled.controlled_config(), tmp_path / 'controlled-provider', tmp_path, complete)
            task.workflow.provider.has_session = lambda *args: True
        elif declared:
            task.workflow.provider = SimpleNamespace(has_session=lambda *args: True,
                complete_with_presentation=complete, complete=lambda *args: pytest.fail('Declared renderer was omitted'))
        else:
            task.workflow.provider = SimpleNamespace(has_session=lambda *args: True, complete=complete)
        schema = runtime._object({'selection': runtime._object({'kind': {'const': 'tool'},
            'tool': {'const': 'hpc.read'}, 'arguments': runtime._object({'reference': {'type': 'string'}})}),
            'report_update': runtime._object({})})
        try:
            assert asyncio.run(task.call(state, schema))[0] == response
            assert len(calls) == 1 and calls[0][0][:2] == ('prediction', 'REASONING')
            if declared:
                assert calls[0][1]['prompt_renderer'] is binding.decision_prompt_renderer
            else:
                assert calls[0][1] == {}
            presented = calls[0][0][3]
            if protocol:
                presented = runtime.apply_state_frame(None, presented)
                assert exchanges.rows('prediction', 0)[0]['request']['instructions'] == calls[0][0][2]
            assert presented['hpc_model_ref'] == 'model-original'
            assert calls[0][0][2].startswith(binding.instructions(SimpleNamespace(role='hpc_prediction')))
            assert 'pending_child_delivery' not in calls[0][0][2]
            saved = journal.row('runtime_model_calls', 'prediction', 0)
            assert json.loads(saved['response']) == response
            task.calls = 0
            assert asyncio.run(task.call(state, schema))[0] == response
            assert len(calls) == 1
            assert database.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0
        finally:
            database.db.close()
