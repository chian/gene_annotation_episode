"""Private annotation decision snapshot and presentation."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a108 import runtime as _original_runtime

def improvement_decision_snapshot(self, view):
    with self.workflow.store.read_snapshot():
        state = self.workflow.working_state(self)
        row = self.workflow.journal.db.execute("SELECT CASE\n                        WHEN json_extract(action,'$.kind')='tool'\n                         AND json_extract(action,'$.tool')='image.view'\n                         AND json_extract(result,'$.status')='completed'\n                        THEN json_extract(result,'$.visual_inputs') ELSE NULL END\n                        FROM runtime_actions WHERE run_id=? AND episode_id=?\n                        AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1", (self.workflow.run_id, self.episode_id)).fetchone()
        visual_evidence = _original_runtime.json.loads(row[0]) if row and row[0] is not None else []
        subset = getattr(self.workflow.store, 'reference_subset', None)
        presented_outcome = self.workflow.local_outcome_preview(self.last_outcome, decision_index=self.last_outcome_index)
        presented_feedback = self.feedback
        if isinstance(self.last_outcome, _original_runtime.Mapping) and self.feedback is self.last_outcome.get('feedback') and isinstance(presented_outcome, _original_runtime.Mapping):
            presented_feedback = presented_outcome.get('feedback')
        credit_view = self.workflow.source_credit_view(self)
        annotation_axes = isinstance(credit_view['credit'], _original_runtime.Mapping) and credit_view['credit'].get('mode') == 'annotation_axis_credit'
        forms = [(self.report_values, self.interpret_schema)]
        if not annotation_axes:
            forms.extend(((report.as_record(), _original_runtime._plain(report.contract.measurements['schema'])) for report in view.child_reports))
        controller_state = _original_runtime._plain(view.controller_state)
        if annotation_axes:
            state = {}
            controller_state = {key: controller_state[key] for key in ('arms', 'annotation_credits', 'root_score', 'decision')}
            if presented_outcome is not None and self.last_outcome_index is not None:
                prior = self.workflow.journal.row('runtime_actions', self.episode_id, self.last_outcome_index)
                if prior is not None and _original_runtime.json.loads(prior['action']).get('kind') in {'child', 'episode_child', 'job_child'}:
                    presented_outcome = {'status': presented_outcome.get('status'), 'record_ref_count': len(presented_outcome.get('record_refs') or ()), 'changed_record_ref_count': len(presented_outcome.get('changed_record_refs') or ())}
                    presented_feedback = None
        basis = _original_runtime._references_in({'working_state': state, 'last_local_outcome': presented_outcome, 'visual_evidence': visual_evidence}, self.workflow.store.get, forms=forms, reference_subset=(lambda refs: subset(refs, self.scope)) if subset is not None else None)
        context = view.model_inputs({'goal': self.request.goal.as_record(), 'scope': self.scope, 'working_state': state, 'visible_record_refs': basis, 'current_credit': {'mode': 'annotation_axis_credit', 'root_score': controller_state['root_score']} if annotation_axes else credit_view['credit'], 'current_evidence_vector': credit_view.get('axis_components'), **({'investigation_progress': {key: credit_view[key] for key in ('retained_finding_count', 'inactive_dependencies', 'detail_pages') if key in credit_view}} if self.workflow.receipt_projection(self) else {}), 'credit_binding': self.workflow.source_credit_binding(self), 'time_accounting': self.workflow.journal.elapsed_view(self.episode_id), 'pending_work': self.workflow.pending_work(self), 'last_local_outcome': presented_outcome, 'feedback': presented_feedback, 'visual_evidence': visual_evidence, 'report_deliveries': self.workflow.delivery_status(self.episode_id), 'controller': controller_state, 'controller_binding': self.workflow.controller_binding, 'tools': self.workflow.catalog(self.scope, source=self), 'tool_knowledge': self.workflow.knowledge.context(), 'job_episode_options': self.workflow.job_episode_options(self), 'available_report_facts': {name: {'type': 'number' if name == 'credit' else 'reference_array', 'meaning': _original_runtime.FACT_MEANINGS[name]} for name in sorted(_original_runtime.FACT_SOURCES)} | self.workflow.extra_report_sources(self), 'requested_report_purpose': self.request.report_contract.decision if self.request.report_contract else None, 'requested_form': self.request.report_contract.schema if self.request.report_contract else None, 'current_report_update': self.report_values, 'current_report_basis_refs': self.report_basis, 'report_lifecycle': 'Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment.'}, reports=() if annotation_axes else view.child_reports)
        if self.workflow.is_scientific_source(self):
            if annotation_axes:
                context.update(proposed_annotations=[{key: row[key] for key in ('proposed_annotation_ref', 'subject_ref', 'predicate', 'value', 'context_refs', 'scope', 'score', 'support', 'opposition', 'status')} for row in credit_view['proposed_annotations']], annotation_comparisons=credit_view['comparisons'])
            else:
                context.update(self.workflow.annotation_context(self.scope, source=self))
        if 'monitoring_information_credit' in credit_view:
            context.update({key: credit_view[key] for key in ('monitoring_information_credit', 'monitoring_information_binding')})
        specialist = self.workflow.specialist(self)
        if specialist is not None:
            context.update(specialist.decision_context(self.workflow.binding_context(self), view))
        context['_completed_work_axis_results'] = {key: credit_view[key] for key in ('a101_sheet', 'a102_sheet', 'a103_sheet', 'a104_sheet', 'target_sheets', 'tool_attachments', 'source_contributions') if key in credit_view}
        contract_catalog = getattr(self.workflow.tools, 'model_contract_catalog', None)
        if callable(contract_catalog):
            context['available_report_facts'] = contract_catalog(context)
    return context


# This parent owns its complete option policy, including original late
# job/specialist/custom-provider reads; initial selection never prunes them.
def action_schema(self, source):
    form_example = _original_runtime._object({'changed_annotation_refs': {'type': 'array', 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'annotation'}, 'x-source': 'changed_annotation_refs', 'description': 'Actual annotation revisions changed during this investigation; these references are not a claim that every revision is still current.'}, 'changed_assessment_refs': {'type': 'array', 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'assessment'}, 'x-source': 'changed_assessment_refs', 'description': 'Actual changed source-linked assessment revisions, retaining their hypotheses, observations, relations and applicability.'}, 'changed_interpretation_account_refs': {'type': 'array', 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'interpretation_account'}, 'x-source': 'changed_interpretation_account_refs', 'description': _original_runtime.FACT_MEANINGS['changed_interpretation_account_refs']}, 'scoped_credit': {'type': 'number', 'x-source': 'credit', 'description': 'Credit projected for the fixed child scope at completion, not an accuracy verdict or a stopping instruction.'}})
    interpretive_example = _original_runtime._object({'interpreted_assessment_refs': _original_runtime._array({'type': 'string', 'format': 'reference', 'x-reference-namespace': 'assessment', 'description': 'Assessments the child selects as bearing on the assigned distinction. Each resolves to its actual hypothesis, observation, relation, conditions and assumptions; a non-discriminating result remains useful information.'}), 'unresolved_hypothesis_refs': _original_runtime._array({'type': 'string', 'format': 'reference', 'x-reference-namespace': 'hypothesis', 'description': 'In-scope alternatives the child currently considers unresolved; an empty array makes no claim that every possible explanation was tested.'}), 'changed_annotation_refs': form_example['properties']['changed_annotation_refs'], 'interpretation_basis_refs': {'type': 'array', 'items': {'type': 'string', 'format': 'reference'}, 'x-source': 'interpretation_basis_refs', 'description': _original_runtime.FACT_MEANINGS['interpretation_basis_refs']}, 'observations_after_report_basis': {'type': 'array', 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'observation'}, 'x-source': 'observations_after_report_basis', 'description': _original_runtime.FACT_MEANINGS['observations_after_report_basis']}})
    scope_schema = {'type': 'object', 'additionalProperties': False, 'required': ['subject_refs'], 'properties': {'subject_refs': _original_runtime._array({'type': 'string'}), 'read_selection_refs': _original_runtime._array({'type': 'string'}), 'segments': _original_runtime._array({'type': 'object', 'additionalProperties': False, 'required': ['target_ref', 'start', 'end', 'unit'], 'properties': {'target_ref': {'type': 'string'}, 'member_ref': {'type': 'string'}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}, 'unit': {'type': 'string', 'enum': ['nt', 'aa', 'symbol']}}})}}
    specialist = self.specialist(source)
    common_actions = specialist.permitted_common_actions(self.binding_context(source)) if specialist is not None else ('tool', 'reason', 'child', 'wait', 'redeliver_report')
    if not self.permits_common_action(source, 'wait'):
        common_actions = tuple((action for action in common_actions if action != 'wait'))
    from gene_annotation_episode.episodic_workflow.root.a108.commissioning_policy import filter_annotation_action_options
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
