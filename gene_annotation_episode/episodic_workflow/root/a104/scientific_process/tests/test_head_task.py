"""Actual A104 original/private task, instructions, state and numerical boundaries."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace
import pytest

from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import ScientificHeadBoundaryChecks
from .head_cases import TASKS, build_case, capture, executed, forbidden, identity, logical_rows, own, plain, COMMISSION_ONLY_TASKS, original_build_denial
from ...tests.provider_dispatch_fixtures import controlled_serial_model, controlled_config

def retained(record_property, name, value):
    record_property(name, json.dumps(plain(value), sort_keys=True, allow_nan=False))

class TestA104ScientificTask:
    axis = 'a104'
    scientific = ScientificHeadBoundaryChecks.scientific
    module = ScientificHeadBoundaryChecks.module

    @pytest.fixture(autouse=True)
    def no_external_operations(self, monkeypatch):
        monkeypatch.setattr('subprocess.Popen', forbidden)
        monkeypatch.setattr('socket.socket.connect', forbidden)
        monkeypatch.setattr('socket.socket.connect_ex', forbidden)

    @pytest.mark.parametrize('task_name', (None, *TASKS))
    @pytest.mark.parametrize('standalone', (False, True))
    def test_actual_build_projector_controller_and_request(self, scientific, task_name, standalone, record_property):
        if standalone and task_name in COMMISSION_ONLY_TASKS:
            denied = original_build_denial(scientific, task_name=task_name)
            retained(record_property, 'original_standalone_build_denial', denied)
            return
        value = build_case(scientific, task_name=task_name, standalone=standalone)
        original = identity(value)
        assert type(value.task) is getattr(value.binding, 'decision_source_type', value.runtime.DecisionSource)
        if hasattr(value.binding, 'decision_source_type'):
            assert 'next' in type(value.task).__dict__
            assert not isinstance(value.task, value.runtime.DecisionSource)
        assert value.acquired == []
        retained(record_property, 'original_identity', original)

    @pytest.mark.parametrize('status', ('completed', 'partial', 'invalid', 'failed', 'unavailable'))
    @pytest.mark.parametrize('saved', (False, True))
    @pytest.mark.parametrize('standalone', (False, True))
    def test_returned_outcome_enters_original_iterator_and_replays(self, scientific, status, saved, standalone, record_property):
        value = build_case(scientific, standalone=standalone)
        retained(record_property, 'original_executed_outcome', executed(value, status, saved=saved))

    @pytest.mark.parametrize('kind,saved', (('reason', False), ('reason', True), ('wait', True)))
    def test_actual_reasoning_and_saved_wait_keep_original_paths(self, scientific, kind, saved, record_property):
        value = build_case(scientific)
        assert 'wait' not in value.binding.permitted_common_actions(value.workflow.binding_context(value.task))
        retained(record_property, 'original_reason_or_saved_wait', executed(value, 'completed', saved=saved, kind=kind))

    @pytest.mark.parametrize('mode', ('returned', 'raised'))
    def test_custom_service_instructions_keep_original_precedence(self, scientific, mode, record_property):
        value = build_case(scientific); task, workflow = value.task, value.workflow
        calls = []; payload = object(); error = ValueError('original-custom-scientific-instructions')
        supplied = {'original': ['context']}
        def custom(source, context):
            assert source is task and context is supplied; calls.append('original_callback')
            if mode == 'raised': raise error
            return payload
        workflow.services = SimpleNamespace(instructions=custom)
        workflow.specialist = workflow.is_job_source = workflow.permits_common_action = forbidden
        if mode == 'raised':
            with pytest.raises(ValueError) as caught: task.instructions(supplied)
            assert caught.value is error
        else: assert task.instructions(supplied) is payload
        assert calls == ['original_callback'] and value.acquired == []
        retained(record_property, 'custom_callback_identity', {'mode': mode, 'calls': calls, 'exact_object_preserved': True})

    @pytest.mark.parametrize('protocol', (None, 'decision_exchange_v1'))
    def test_default_instructions_keep_actual_publication_and_original_read_order(self, scientific, protocol, record_property):
        value = build_case(scientific); host, task = value.workflow, value.task
        host.decision_protocol = protocol
        supplied = {'tool_knowledge': {}, 'launch_instruction_library': {}}
        assert value.binding.replaces_default_instructions is True
        seen = []; specialist = host.specialist
        def observed(source): seen.append(source.episode_id); return specialist(source)
        host.specialist = observed
        expected = own('runtime_prompt').instructions(task, supplied); original_reads = list(seen); seen.clear()
        actual = task.instructions(supplied)
        assert actual == expected and seen == original_reads and original_reads == [task.episode_id] * 3
        context = host.binding_context(task)
        retained(record_property, 'original_instruction_and_summary', {'instructions': actual,
            'summary': value.binding.decision_context(context, None),
            'initial_context': value.binding.initial_decision_context(context),
            'replaces_default_instructions': value.binding.replaces_default_instructions,
            'specialist_reads': seen})

    @pytest.mark.parametrize('publication', ('instruction_only', 'legacy', 'mixed'))
    def test_actual_publication_controls_default_instruction_replacement(self, scientific, tmp_path, publication, record_property):
        from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import write_instruction_source
        source = tmp_path / 'publication-source'; write_instruction_source(source, 'a104')
        if publication != 'instruction_only':
            metadata = own('scientific_support_metadata')
            original = json.loads((source / 'entries/A104.json').read_bytes())
            identifier = 'A999' if publication == 'mixed' else 'A104'
            assessment = metadata._ASSESSMENT
            legacy = {'entry_version': metadata.SUPPORT_ENTRY_VERSION, 'id': identifier,
                'slot': 'annotation_distinction', 'name': 'Original legacy engineering instructions',
                'description': 'Instruction metadata only; no scientific evidence.',
                'support': {'proposition': 'Controlled unresolved engineering proposition',
                    'operands': [{'operand_id': 'original_fixture',
                        'observation_kinds': [metadata.OBSERVATION_KINDS[0]],
                        'hypothesis_predicates': [metadata.PREDICATES[0]],
                        'assessment_relations': [assessment['relation']['enum'][0]],
                        'applicabilities': [assessment['applicability']['enum'][0]],
                        'extent_bases': [assessment['extent_basis']['enum'][0]],
                        'finding_qualifications': [metadata.FINDING_QUALIFICATIONS[0]],
                        'instruction': 'Keep the source question unresolved.'}],
                    'qualifications': ['Engineering instruction metadata only.'],
                    'boundary': 'No evidence, acquired action or credit is asserted.'},
                'evidence': deepcopy(original['evidence'])}
            metadata.validate_support_entry(legacy)
            if publication == 'mixed':
                legacy = {key: deepcopy(legacy[key]) for key in ('id', 'name', 'description', 'evidence')}
                legacy.update(slot='evidence_axis',
                    claim_scope='Historical engineering instruction metadata only.',
                    distinctions=['Retain the original unresolved engineering distinction.'],
                    not_established=['No biological result or target support is established.'],
                    boundary='Original legacy instruction metadata supplies no scientific evidence or credit.')
            (source / 'entries' / (identifier + '.json')).write_text(json.dumps(legacy) + '\n')
            index = json.loads((source / 'index.json').read_bytes())
            row = {'id': identifier, 'slot': legacy['slot'], 'name': legacy['name'], 'description': legacy['description'],
                'detail_path': 'entries/' + identifier + '.json', 'source_evidence_ids': ['E-' + identifier + '-01']}
            if publication == 'legacy':
                index['entries'] = [row if entry['id'] == 'A104' else entry for entry in index['entries']]
                index['slots'][0]['slot'] = 'annotation_distinction'
            else:
                index['entries'].append(row)
                axis_slots = [slot for slot in index['slots'] if slot['slot'] == 'evidence_axis']
                assert len(axis_slots) == 1 and axis_slots[0]['count'] == 1
                axis_slots[0]['count'] = 2
                sources = json.loads((source / 'option_sources.json').read_bytes())
                sources['rows'].append({'evidence_id': 'E-' + identifier + '-01', 'option_id': identifier, **legacy['evidence'][0]})
                (source / 'option_sources.json').write_text(json.dumps(sources) + '\n')
            (source / 'index.json').write_text(json.dumps(index) + '\n')
        library = own('scientific_process_library').ScientificProcessLibrary.freeze(tmp_path / 'publication-library', source=source)
        binding = own('scientific_process.episode').ScientificProcessEpisode(scientific.services,
            library=library, tool_library=scientific.tool_library, child_roles=('scientific_process', 'hpc'))
        assert binding.replaces_default_instructions is (publication == 'instruction_only')
        assignment = deepcopy(scientific.assignment)
        assignment['selection']['evidence_axis'] = library.reference('A104')
        assignment['selection']['thought_pattern'] = library.reference('P01')
        prepared = binding.prepare_invocation(scientific.parent, 'scientific_process', assignment,
            scientific.context.scope, 'publication-invocation', invocation=scientific.invocation)
        request = deepcopy(scientific.request)
        request['message']['episode_assignment'] = prepared['assignment']
        request['message']['scientific_process'] = prepared['scientific_process']
        context = replace(scientific.context, assignment=prepared['assignment'], request=request)
        binding.validate_context(context)
        source_type = getattr(binding, 'decision_source_type', own('runtime').DecisionSource)
        # This test invokes instruction composition only. Actual constructors
        # and build are covered separately; no initialized loop is claimed here.
        task = object.__new__(source_type); task.path = context.path; task.episode_id = context.episode_id
        host = SimpleNamespace(specialist=lambda source: binding, binding_context=lambda source: context,
            is_job_source=lambda source: False, permits_common_action=lambda source, action:
                action in binding.permitted_common_actions(context), native_event_information=None,
            decision_protocol=None)
        host.services = own('episode_services').WorkflowServices(host); task.workflow = host
        expected = own('runtime_prompt').instructions(task, {})
        assert task.instructions({}) == expected
        baseline = own('runtime_prompt').INSTRUCTIONS
        assert expected.startswith(baseline) is (publication != 'instruction_only')
        retained(record_property, 'original_publication_instructions', {'publication': publication,
            'replaces_default_instructions': binding.replaces_default_instructions,
            'instructions': expected, 'library_descriptor': library.as_record()})

    @pytest.mark.parametrize('case', ('ordinary', 'unrecognized', 'bootstrap', 'update', 'lookup',
        'lost_task', 'hpc_priority', 'missing_base'))
    def test_actual_provider_preserves_complete_presentation_precedence(self, scientific, tmp_path, case, record_property):
        value = build_case(scientific); context = value.workflow.binding_context(value.task)
        original_state = {'goal': {'objective': scientific.invocation['objective']}, 'scope': plain(context.scope),
            **value.binding.decision_context(context, None)}
        frames = own('decision_context')
        connection = object.__new__(own('providers')._SessionConnection)
        connection.scientific_prompt_states = {}; key = (value.task.episode_id, 'REASONING')
        frame = deepcopy(original_state)
        if case == 'unrecognized': frame = {'unrecognized': True}
        elif case == 'bootstrap': frame = frames.state_frame(original_state)
        elif case in ('update', 'lookup', 'lost_task'):
            connection.scientific_prompt_states[key] = deepcopy(original_state)
            frame = ({'version': frames.VERSION, 'kind': 'decision_lookup_result', 'result': {'original': True}}
                if case == 'lookup' else frames.state_frame({} if case == 'lost_task' else
                    {**original_state, 'last_local_outcome': {'status': 'invalid'}}, original_state))
        elif case == 'hpc_priority': frame = {**original_state, 'hpc_commission': {'objective': 'Original HPC context'}}
        elif case == 'missing_base': frame = frames.state_frame(original_state, {'missing': 'base'})
        initial = deepcopy(connection.scientific_prompt_states)
        expected = capture(lambda: connection._presentation(value.task.episode_id, 'REASONING',
            'Original scientific instructions', deepcopy(frame)))
        expected_cache = deepcopy(connection.scientific_prompt_states); connection.scientific_prompt_states = initial
        async def complete(episode, role, guidance, inputs, schema, **kwargs):
            return connection._presentation(episode, role, guidance, inputs, **kwargs)
        value.workflow.provider = controlled_serial_model(controlled_config(), tmp_path / 'presentation-model', tmp_path, complete)
        callback = (lambda: value.task.decision_completion()(value.task.episode_id, 'REASONING',
            'Original scientific instructions', deepcopy(frame), {})) if hasattr(value.task, 'decision_completion') else (
            (lambda: value.task.complete_decision('Original scientific instructions', deepcopy(frame), {})) if hasattr(
                value.task, 'complete_decision') else (lambda: value.workflow.provider.complete(value.task.episode_id, 'REASONING',
                    'Original scientific instructions', deepcopy(frame), {})))
        actual = capture(lambda: asyncio.run(callback()))
        assert actual == expected and connection.scientific_prompt_states == expected_cache
        retained(record_property, 'original_presentation', {'case': case, 'frame': frame, 'outcome': actual,
            'cache': [[list(k), v] for k, v in sorted(expected_cache.items())]})

    @pytest.mark.parametrize('mode', ('scalar', 'annotation_axis_credit'))
    @pytest.mark.parametrize('answered', (False, True))
    @pytest.mark.parametrize('protocol', (None, 'decision_exchange_v1'))
    def test_actual_saved_model_context_and_zero_exchange_restore(self, scientific, tmp_path, mode, answered, protocol, record_property):
        value = build_case(scientific); host, task = value.workflow, value.task
        host.decision_protocol = protocol
        host.decision_exchanges = own('decision_exchanges').DecisionExchanges(host.journal)
        context = {'scope': plain(task.scope), 'current_credit': 0.,
            **value.binding.decision_context(host.binding_context(task), None)}
        if mode == 'annotation_axis_credit':
            # Explicit saved-context control exercises the original accepted
            # transport branch, not an assertion of a live A104 root controller.
            context['current_credit'] = {'mode': mode, 'root_score': 0.}
            context['controller'] = {'arms': [], 'annotation_credits': [], 'root_score': 0., 'decision': None}
        schema = own('domain').obj({'selection': own('domain').obj({'kind': {'const': 'tool'},
            'tool': {'const': 'fixture.inspect'}, 'arguments': own('domain').obj({'record': {'type': 'string'}})}),
            'report_update': own('domain').obj({})})
        response = {'selection': {'kind': 'tool', 'tool': 'fixture.inspect', 'arguments': {'record': scientific.target}},
            'report_update': {}}
        saved = {'context': deepcopy(context), 'schema': schema}
        if protocol: saved['decision_protocol'] = protocol
        host.journal.save('runtime_model_calls', {'episode_id': task.episode_id, 'call_index': 0,
            'purpose': 'decision', 'request': value.runtime._json(saved),
            'response': value.runtime._json(response) if answered else None})
        calls = []
        async def complete(*args, **kwargs):
            calls.append({'args': plain(args), 'presentation_declared': 'prompt_renderer' in kwargs})
            return ({'response': {'response_type': 'select_action', **response}} if protocol else deepcopy(response))
        host.provider = controlled_serial_model(controlled_config(), tmp_path / 'saved-model', tmp_path, complete)
        host.provider.has_session = lambda *args: True  # Same explicit saved-session transport fixture.
        before_actions = logical_rows(value.store).get('runtime_actions', [])
        first = asyncio.run(task.call({'ignored_fresh_context': True}, {})); task.calls = 0
        second = asyncio.run(task.call({'ignored_fresh_context': False}, {}))
        assert plain(first) == plain(second) and first[0] == response
        assert len(calls) == (0 if answered else 1)
        assert json.loads(host.journal.row('runtime_model_calls', task.episode_id, 0)['request']) == saved
        assert logical_rows(value.store).get('runtime_actions', []) == before_actions and value.acquired == []
        exchanges = host.decision_exchanges.rows(task.episode_id, 0)
        assert len(exchanges) == (1 if protocol and not answered else 0)
        retained(record_property, 'original_saved_model_context', {'mode': mode, 'answered': answered,
            'protocol': protocol, 'saved_request': saved, 'first': plain(first), 'second': plain(second),
            'provider_calls': len(calls), 'exchange_count': len(exchanges)})

    def test_actual_saved_checkpoint_suspension_and_form_replay(self, scientific, record_property):
        value = build_case(scientific); task, host = value.task, value.workflow
        returned = {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [],
            'feedback': {'code': 'original_saved_invalid'}}
        host.journal.save('runtime_actions', {'episode_id': task.episode_id, 'decision_index': 8,
            'action': value.runtime._json({'kind': 'tool', 'tool': 'fixture.inspect', 'arguments': {'record': scientific.target}}),
            'result': value.runtime._json(returned), 'credit': 0.})
        task._restored_source_state = {'last_outcome_index': 8, 'feedback': deepcopy(returned['feedback'])}
        task.restore_checkpoint()
        assert task.last_outcome == returned and task.feedback == returned['feedback']
        task.restore_checkpoint(); assert task.last_outcome_index == 8
        changes = []; handle = object(); host.execution_handle = handle
        def change(actual, condition): assert actual is handle; changes.append(deepcopy(condition))
        host.execution_backend = SimpleNamespace(set_suspension=change)
        task.suspension_changed({'original_dependency': True}); task.suspension_changed(None)
        expected = {'episode_id': task.episode_id, 'dependency': {'original_dependency': True}}
        assert changes == [expected, None]
        form = deepcopy(scientific.invocation['initial_report'])
        host.journal.save('runtime_forms', {'episode_id': task.episode_id, 'facts': '{}', 'form': value.runtime._json(form)})
        released = []
        async def release(episode): released.append(episode)
        host.provider = SimpleNamespace(release=release); host.facts = forbidden
        first = asyncio.run(task.finish(value.runtime.Record({'credit': 0.})))
        second = asyncio.run(task.finish(value.runtime.Record({'credit': 0.})))
        assert first.as_record() == second.as_record() == {'form': form}
        assert released == [task.episode_id, task.episode_id] and value.acquired == []
        retained(record_property, 'original_saved_state', {'outcome': returned, 'suspension': changes,
            'form': form, 'releases': released})

    def test_ready_owned_child_precedes_another_decision(self, scientific, record_property):
        value = build_case(scientific); ready = object(); calls = []
        value.task._execution_context = SimpleNamespace(_ready_owned_child=lambda path: calls.append(plain(path)) or ready)
        outcome = asyncio.run(value.task.next(SimpleNamespace(units_consumed=0)))
        assert outcome is ready and calls == [plain(value.task.path)] and value.task.calls == 0
        retained(record_property, 'original_ready_child', {'paths': calls, 'model_calls': value.task.calls, 'exact_child_returned': True})
