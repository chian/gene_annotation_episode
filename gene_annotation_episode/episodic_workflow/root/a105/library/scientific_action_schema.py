"""Shared scientific child form templates and typed action policy for actual private configured bindings and preserved custom fallback. Binding permissions, children and assignment schemas remain private."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a105 import runtime as _original_runtime

def action_schema(self, source):
    form_example = _original_runtime._object({'changed_annotation_refs': {'type': 'array', 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'annotation'}, 'x-source': 'changed_annotation_refs', 'description': 'Actual annotation revisions changed during this investigation; these references are not a claim that every revision is still current.'}, 'changed_assessment_refs': {'type': 'array', 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'assessment'}, 'x-source': 'changed_assessment_refs', 'description': 'Actual changed source-linked assessment revisions, retaining their hypotheses, observations, relations and applicability.'}, 'changed_interpretation_account_refs': {'type': 'array', 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'interpretation_account'}, 'x-source': 'changed_interpretation_account_refs', 'description': _original_runtime.FACT_MEANINGS['changed_interpretation_account_refs']}, 'scoped_credit': {'type': 'number', 'x-source': 'credit', 'description': 'Credit projected for the fixed child scope at completion, not an accuracy verdict or a stopping instruction.'}})
    interpretive_example = _original_runtime._object({'interpreted_assessment_refs': _original_runtime._array({'type': 'string', 'format': 'reference', 'x-reference-namespace': 'assessment', 'description': 'Assessments the child selects as bearing on the assigned distinction. Each resolves to its actual hypothesis, observation, relation, conditions and assumptions; a non-discriminating result remains useful information.'}), 'unresolved_hypothesis_refs': _original_runtime._array({'type': 'string', 'format': 'reference', 'x-reference-namespace': 'hypothesis', 'description': 'In-scope alternatives the child currently considers unresolved; an empty array makes no claim that every possible explanation was tested.'}), 'changed_annotation_refs': form_example['properties']['changed_annotation_refs'], 'interpretation_basis_refs': {'type': 'array', 'items': {'type': 'string', 'format': 'reference'}, 'x-source': 'interpretation_basis_refs', 'description': _original_runtime.FACT_MEANINGS['interpretation_basis_refs']}, 'observations_after_report_basis': {'type': 'array', 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'observation'}, 'x-source': 'observations_after_report_basis', 'description': _original_runtime.FACT_MEANINGS['observations_after_report_basis']}})
    scope_schema = {'type': 'object', 'additionalProperties': False, 'required': ['subject_refs'], 'properties': {'subject_refs': _original_runtime._array({'type': 'string'}), 'read_selection_refs': _original_runtime._array({'type': 'string'}), 'segments': _original_runtime._array({'type': 'object', 'additionalProperties': False, 'required': ['target_ref', 'start', 'end', 'unit'], 'properties': {'target_ref': {'type': 'string'}, 'member_ref': {'type': 'string'}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}, 'unit': {'type': 'string', 'enum': ['nt', 'aa', 'symbol']}}})}}
    specialist = self.specialist(source)
    common_actions = specialist.permitted_common_actions(self.binding_context(source)) if specialist is not None else ('tool', 'reason', 'child', 'wait', 'redeliver_report')
    if not self.permits_common_action(source, 'wait'):
        common_actions = tuple((action for action in common_actions if action != 'wait'))
    from gene_annotation_episode.episodic_workflow.root.a105.commissioning_policy import filter_annotation_action_options
    common_actions = filter_annotation_action_options(self, source, common_actions)
    options = [] if self.is_job_source(source) or 'reason' not in common_actions else [self.reasoning_action_schema(source)]
    if 'wait' in common_actions:
        options.append(_original_runtime._object({'kind': {'type': 'string', 'const': 'wait'}, 'condition': _original_runtime._wait_condition_schema()}))
    for item in self.catalog(source.scope, source=source) if 'tool' in common_actions else ():
        branch = _original_runtime._object({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': item['name']}, 'arguments': _original_runtime._embedded_tool_schema(item['input_schema'])})
        if item.get('argument_transport') is not None:
            if item['argument_transport'] != _original_runtime.CONTRACT_ARGUMENT_TRANSPORT:
                raise ValueError('unsupported_tool_argument_transport')
            branch['x-argument-transport'] = _original_runtime.CONTRACT_ARGUMENT_TRANSPORT
        options.append(branch)
    scientific_child = _original_runtime._object({'kind': {'type': 'string', 'const': 'child'}, 'goal': {'type': 'string', 'description': "A substantive improvement the child can pursue iteratively and revise from outcomes. A fully specified one-off lookup/calculation belongs to an ordinary tool. Numerical yield controls the child's continuation."}, 'scope': scope_schema, 'purpose': {'type': 'string', 'description': 'Explain what information you need for your later scientific decision and what your selected form fields mean.'}, 'schema_json': {'type': 'string', 'description': 'JSON encoding of your parent-defined closed return form: explicit required fields, additionalProperties false, typed arrays, and strings restricted to enum codes or declared semantic formats. A reference can declare format reference and x-reference-namespace. Optional top-level x-source selectors bind recorded facts named in available_report_facts; do not ask a model to invent those facts. These examples are optional API guidance; choose fields and meanings for your actual later decision. Fact-only example: ' + _original_runtime._json(form_example) + ' Interpretive example, selecting actual assessment records rather than a findings paragraph: ' + _original_runtime._json(interpretive_example)}, 'initial_report_json': {'type': 'string', 'description': 'JSON containing exactly the interpretation fields you chose (those without x-source), with parent-supplied initial values. Use {} for the fact-only example; for the interpretive example use {"interpreted_assessment_refs":[],"unresolved_hypothesis_refs":[]}. Those initial arrays are not new child judgments. If you request other interpreted fields, define their allowed meanings and initialize them explicitly. The runtime does not choose fields or unknown values for you.'}})
    if not self.is_job_source(source):
        explicit_roles = None if self.annotation_child_roles is None and (not (len(source.path) == 1 and getattr(self.project_credit, 'task_credit', False))) else self.available_child_roles(source)
        if specialist is None and self.scientific_process_binding is None and ('child' in common_actions) and (explicit_roles is None or 'improvement' in explicit_roles):
            options.append(scientific_child)
        if self.job_episodes is not None and specialist is None:
            options.extend((option for option in self.job_episodes.commission_schemas(scientific_child) if explicit_roles is None or option['properties']['role']['const'] in explicit_roles))
        if 'child' in common_actions:
            roles = tuple((role for role in explicit_roles if role in self.episode_bindings.roles)) if explicit_roles is not None else specialist.allowed_children(self.binding_context(source), self.services.capabilities()) if specialist is not None else self.episode_bindings.entry_roles
            declared = set(specialist.child_roles(source.path[-1][0])) if specialist else set(roles)
            if not set(roles) <= declared:
                raise _original_runtime.WorkflowError('available_child_outside_declared_type_edges')
            for role in roles:
                binding = self.episode_bindings.for_child(source.path, role)
                child_schema = getattr(binding, 'child_assignment_schema', None)
                properties = {**scientific_child['properties'], 'kind': {'type': 'string', 'const': 'episode_child'}, 'role': {'type': 'string', 'const': role}, 'assignment': child_schema(self.binding_context(source), role) if child_schema is not None else binding.assignment_schema(role)}
                if self.root_child_return_sources(source, role):
                    properties.pop('schema_json')
                    properties.pop('initial_report_json')
                options.append(_original_runtime._object(properties))
    if not self.is_job_source(source) and 'redeliver_report' in common_actions:
        options.append(_original_runtime._object({'kind': {'type': 'string', 'const': 'redeliver_report'}, 'delivery_ref': {'type': 'string', 'description': 'Copy the delivery_ref from report_deliveries or report_delivery_failure for the saved child report.'}, 'purpose': {'type': 'string'}, 'schema_json': {'type': 'string'}}))
    return _original_runtime._object({'selection': {'anyOf': options}, 'report_update': source.interpret_schema})
