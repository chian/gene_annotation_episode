"""Scientific-head boundaries with real libraries, Store and binding methods.

Instruction entries and the selected tool are explicit engineering fixtures.
They supply no biological finding, provider decision, score or continuation.
The production assignment, invocation, report and exception paths are real.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from types import SimpleNamespace

import pytest


def write_instruction_source(directory, axis):
    """Keep required synthetic instruction data with the test implementation."""
    evidence = {
        'case_group': 'scientific_head_boundary_fixture',
        'case_id': 'synthetic_instruction',
        'source_url': 'https://example.org/scientific-head-fixture',
        'source_locator': 'synthetic instruction record',
        'observation': 'Engineering instruction data; no scientific result.',
        'limit': 'No biological evidence or target support is asserted.',
    }
    bodies = [{
        'entry_version': 'evidence_axis_instruction_v1', 'id': axis.upper(),
        'slot': 'evidence_axis', 'name': 'Synthetic '+axis.upper()+' instructions',
        'description': 'Exercise this axis binding without interpreting evidence.',
        'investigation_instructions': 'Preserve the original assigned question and unknown result.',
        'evidence': [deepcopy(evidence)],
    }]
    for identity in ('P01', 'P02'):
        bodies.append({
            'id': identity, 'slot': 'thought_pattern', 'name': 'Fixture '+identity,
            'description': 'Compare two explicitly unresolved explanations.',
            'use_when': 'The controlled engineering comparison remains unresolved.',
            'live_alternatives': ['First fixture explanation', 'Second fixture explanation'],
            'decision_guidance': ['Inspect the selected fixture outcome.'],
            'outcome_contingencies': [{'if_observed': 'The fixture is unavailable',
                                      'then_consider': 'Retain the unresolved result.'}],
            'boundary': 'An instruction choice supplies no evidence or credit.',
            'evidence': [deepcopy(evidence)],
        })
    entries, rows = [], []
    for body in bodies:
        identity = body['id']
        relative = 'entries/'+identity+'.json'
        path = directory/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body)+'\n')
        evidence_id = 'E-'+identity+'-01'
        entries.append({**{key: body[key] for key in ('id', 'slot', 'name', 'description')},
                        'detail_path': relative, 'source_evidence_ids': [evidence_id]})
        rows.append({'evidence_id': evidence_id, 'option_id': identity, **evidence})
    (directory/'index.json').write_text(json.dumps({
        'format': 'research_three_slot_options_v1', 'status': 'Engineering fixture only',
        'slots': [{'slot': 'evidence_axis', 'catalog': 'axes.json', 'count': 1},
                  {'slot': 'thought_pattern', 'catalog': 'thoughts.json', 'count': 2}],
        'entries': entries,
    })+'\n')
    (directory/'option_sources.json').write_text(json.dumps({
        'meaning': 'Synthetic instruction provenance, never scientific evidence.', 'rows': rows,
    })+'\n')


class ScientificHeadBoundaryChecks:
    def module(self, name):
        return importlib.import_module(
            'gene_annotation_episode.episodic_workflow.root.'+self.axis+'.'+name)

    @pytest.fixture
    def scientific(self, tmp_path):
        source = tmp_path/'source'
        write_instruction_source(source, self.axis)
        library = self.module('scientific_process_library').ScientificProcessLibrary.freeze(
            tmp_path/'scientific-process-library', source=source)
        obj = self.module('domain').obj
        catalog = [{
            'name': 'fixture.inspect', 'resources': 'local',
            'description': 'Return only the explicitly controlled test outcome.',
            'instructions': 'This operation neither acquires nor interprets scientific evidence.',
            'input_schema': obj({'record': {'type': 'string'}}),
        }]
        tool_library = self.module('scientific_tool_library').ScientificToolLibrary.freeze(
            tmp_path/'scientific-tool-library', catalog=catalog, tool_info=True)
        with self.module('state').Store(tmp_path/'state') as store:
            problem = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
            target = problem['subject_refs'][0]
            scope = {'subject_refs': [target]}
            calls = []
            outcome = {'status': 'unavailable', 'record_refs': [], 'changed_record_refs': [],
                       'result': None, 'feedback': {'code': 'engineering_fixture_unavailable'}}

            def execute(name, arguments, **operands):
                calls.append((name, deepcopy(arguments), self.module('communication').plain(operands)))
                return deepcopy(outcome)

            services = SimpleNamespace(
                tool_catalog=lambda scope: deepcopy(catalog),
                tool_information_catalog=lambda scope: deepcopy(catalog),
                reference_in_scope=lambda ref, scope, namespace: ref == target and namespace in (None, 'subject'),
                protein_structure_reference_access=lambda *args: None,
                execute_tool=execute,
                scientific_credit=lambda context, selection: {'credit': 0},
                scientific_received_results=lambda context: [],
                scientific_frozen_results=lambda context: [],
                scientific_reference=lambda *args: False,
            )
            binding = self.module('scientific_process.episode').ScientificProcessEpisode(
                services, library=library, tool_library=tool_library,
                child_roles=('scientific_process', 'hpc'))
            Context = self.module('episode_bindings').BindingContext
            EpisodeRef = self.module('method_loop.identities').EpisodeRef
            parent_path = (('annotation', 'original_parent'),)
            parent = Context('scientific-head-fixture', EpisodeRef('scientific-head-fixture', parent_path).episode_id,
                'annotation', parent_path, scope, {}, {}, (target,))
            selected = {'version': self.module('scientific_process_records').SELECTION_VERSION,
                'evidence_axis': library.reference(self.axis.upper()),
                'thought_pattern': library.reference('P01'),
                'child_tool_info': [{'name': 'fixture.inspect', 'resources': 'local'}]}
            assignment = {'selection': selected, 'evidence_refs': [target],
                          'constraints': {'fixture_only': True}, 'context': {}}
            form = obj({'status': {'type': 'string', 'enum': ['unresolved']}})
            invocation = {'objective': 'Preserve an explicitly unresolved fixture question',
                          'purpose': 'Return the original unresolved fixture status',
                          'report_schema': form, 'initial_report': {'status': 'unresolved'}}
            prepared = binding.prepare_invocation(parent, 'scientific_process', assignment,
                scope, 'original-scientific-commission', invocation=invocation)
            path = parent_path+(('scientific_process', 'child_0'),)
            records = self.module('scientific_process_records')
            request = {'goal': {'objective': invocation['objective']},
                'report_contract': {'decision': invocation['purpose'], 'measurements': {'schema': form}},
                'message': {'scope': scope, 'episode_assignment': prepared['assignment'],
                    'scientific_process': prepared['scientific_process'],
                    'scientific_invocation_ref': records.scientific_invocation_ref(parent.run_id, path),
                    'initial_report': invocation['initial_report']}}
            context = Context(parent.run_id, EpisodeRef(parent.run_id, path).episode_id,
                'scientific_process', path, scope, prepared['assignment'], request, (target,))
            yield SimpleNamespace(binding=binding, context=context, parent=parent, store=store, directory=tmp_path,
                target=target, library=library, tool_library=tool_library, catalog=catalog,
                selected=selected, assignment=assignment, request=request, prepared=prepared,
                invocation=invocation, form=form, services=services, calls=calls, outcome=outcome)

    def test_fresh_private_descriptor_allows_original_execution(self, scientific):
        v = scientific
        descriptor = v.binding.as_record()
        assert self.module('episode_composition').scientific_binding_compatible(descriptor, descriptor)
        v.binding.validate_execution_context(v.context)

    def test_current_binding_reopens_its_original_frozen_libraries(self, scientific):
        v = scientific
        descriptor = v.binding.as_record()
        reopened = self.module('episode_composition').reopen_scientific_binding(
            v.services, descriptor=descriptor, directory=v.directory)
        assert type(reopened) is type(v.binding)
        assert reopened.as_record() == descriptor
        assert reopened.library.as_record() == v.library.as_record()
        assert reopened.tool_library.as_record() == v.tool_library.as_record()
        reopened.validate_context(v.context)
        assert v.calls == []

    def test_assignment_materializes_actual_tool_and_retains_pinned_inputs(self, scientific):
        v = scientific
        v.binding.validate_context(v.context)
        actual = self.module('communication').plain(v.context.assignment)
        tool, = actual['selection']['child_tool_info']
        assert tool['name'] == 'fixture.inspect' and tool['resources'] == 'local'
        assert tool['description'] == v.catalog[0]['description']
        assert tool['instructions'].startswith(v.catalog[0]['instructions'])
        assert v.assignment['selection'] == v.selected
        assert v.binding.initial_references(v.context) == [v.target]
        assert v.binding.credit_view(v.context, None) == {'credit': 0}
        assert v.calls == []

    @pytest.mark.parametrize('operand', ['assignment', 'purpose', 'path'])
    def test_changed_original_invocation_is_rejected(self, scientific, operand):
        v = scientific
        request = deepcopy(v.request)
        if operand == 'assignment':
            assignment = self.module('communication').plain(v.context.assignment)
            assignment['selection']['thought_pattern'] = v.library.reference('P02')
            changed = replace(v.context, assignment=assignment)
        elif operand == 'purpose':
            request['report_contract']['decision'] = 'A different requested meaning'
            changed = replace(v.context, request=request)
        else:
            changed = replace(v.context, path=v.context.path[:-1]+(('scientific_process', 'different_child'),))
        with pytest.raises(self.module('domain').ContractError, match='scientific_filled_identity_mismatch'):
            v.binding.validate_context(changed)
        assert v.calls == []

    def test_revision_prepares_separate_child_without_mutating_current_assignment(self, scientific):
        v = scientific
        before = self.module('communication').plain(v.context.as_record())
        arguments = {'thought_pattern': v.library.reference('P02'),
                     'child_tool_info': [{'name': 'fixture.inspect', 'resources': 'local'}]}
        result = asyncio.run(v.binding.execute(v.context, 'process.revise', arguments, 'revision-operation'))
        assert result['status'] == 'completed'
        proposal = result['result']
        records = self.module('scientific_process_records')
        assert proposal['parent_selection_sha256'] == records.scientific_digest(before['assignment']['selection'])
        assert proposal['selection']['evidence_axis'] == before['assignment']['selection']['evidence_axis']
        assert proposal['selection']['thought_pattern'] == arguments['thought_pattern']
        assert result['revision_origin']['parent_invocation_ref'] == records.scientific_invocation_ref(v.context.run_id, v.context.path)
        assert result['record_refs'] == result['changed_record_refs'] == []
        assert v.context.as_record() == before and v.calls == []

    @pytest.mark.parametrize('status', ['completed', 'invalid', 'failed', 'unavailable'])
    def test_selected_operation_returns_actual_outcome_unchanged(self, scientific, status):
        v = scientific
        v.outcome['status'] = status
        result = asyncio.run(v.binding.execute(v.context, 'fixture.inspect', {'record': v.target}, 'selected-operation'))
        assert result == v.outcome
        assert v.calls == [('fixture.inspect', {'record': v.target},
                            {'scope': self.module('communication').plain(v.context.scope),
                             'operation_key': 'selected-operation'})]
        assert v.binding.credit_view(v.context, None) == {'credit': 0}

    def test_unselected_tool_is_invalid_without_dispatch(self, scientific):
        v = scientific
        result = asyncio.run(v.binding.execute(v.context, 'fixture.unselected', {}, 'invalid-selection'))
        assert result['status'] == 'invalid' and result['result'] is None
        assert result['feedback']['code'] == 'scientific_operation_unavailable'
        assert result['record_refs'] == result['changed_record_refs'] == [] and v.calls == []

    def test_report_keeps_original_allowed_meaning_and_exception_identity(self, scientific):
        v = scientific
        v.binding.validate_report(v.context, {'status': 'unresolved'}, v.form)
        with pytest.raises(self.module('communication').ReportBoundaryError):
            v.binding.validate_report(v.context, {'status': 'measured'}, v.form)
        assert v.calls == []

    def test_current_callable_change_does_not_silently_replace_frozen_tool(self, scientific):
        v = scientific
        v.catalog[0]['input_schema']['properties']['record'] = {'type': 'integer'}
        with pytest.raises(ValueError):
            v.binding.validate_context(v.context)
        assert v.calls == []
