"""Private A103 scientific internal summary."""
from __future__ import annotations
from .contracts import EVIDENCE_AXIS_VERSION, INSTRUCTION_VERSION, ROLE, SELECTION_VERSION, deepcopy, evidence_axis_instruction_view, instruction_view, plain, scientific_digest, selection_fields, selector_selection, support_observation_kinds

class ScientificSummary:

    def decision_context(self, context, current_view):
        selection = self._original_selection(context)
        annotation, thought = (self.library.resolve(selection[key]) for key in selection_fields(selection)[:2])
        resolved = self._tool_resolution(context, selection)

        def selected_fields(entry, names):
            return {name: deepcopy(entry[name]) for name in names if name in entry}
        fields = selection_fields(selection)
        current = selection['version'] == SELECTION_VERSION
        assignment = plain(context.assignment)
        if current:
            assignment = {**assignment, 'selection': selector_selection(selection)}
        published = annotation.get('entry_version') == INSTRUCTION_VERSION
        if published:
            axis_view = instruction_view(annotation)
        elif annotation.get('entry_version') == EVIDENCE_AXIS_VERSION:
            axis_view = evidence_axis_instruction_view(annotation)
        else:
            axis_view = selected_fields(annotation, ('id', 'name', 'description', 'support'))
        return {'gene_context_evidence': {'selection': selector_selection(selection), 'initial_selection_sha256': scientific_digest(plain(context.assignment['selection'])), 'evidence_axis' if current else 'annotation': axis_view, **({} if published else {'annotation_support_routes': self.services.scientific_support_routes(context, observation_kinds=support_observation_kinds(annotation))}), 'thought_pattern' if current else 'thought': selected_fields(thought, ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance', 'outcome_contingencies', 'boundary')), **({'child_tool_info': deepcopy(selection[fields[2]])} if current else {'tools': deepcopy(resolved)}), 'assignment': assignment, 'permitted_children': list(self.allowed_children(context, None))}}

    def initial_decision_context(self, context):
        if context.role not in {'annotation', ROLE}:
            return {}
        workflow = getattr(self.services, 'workflow', None)
        result = {}
        from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.received_execution_context import received_execution_context
        result.update(received_execution_context(context, workflow))
        return result
