"""Private scientific-process credit behavior for A106."""
from __future__ import annotations
from .scientific_contracts import (ContractError, EVIDENCE_AXIS_VERSION, INSTRUCTION_VERSION, ROLE, selection_fields)

from ..communication import plain
from ..domain import ContractError
from ..investigation_progress import FindingProgressPolicy, ScientificFindingProgress
def original_task_projector(assignment):
    task = plain(assignment).get('context', {}).get('evidence_task')
    if (not isinstance(task, dict) or set(task) != {
            'version', 'kind', 'evidence_axis', 'credit_unit'}
            or task['version'] != 'evidence_axis_task_v1'
            or task['kind'] != 'whole_axis_findings' or task['evidence_axis'] != 'A106'):
        raise ContractError('original_axis_finding_task_required')
    return ScientificFindingProgress(FindingProgressPolicy(task['credit_unit']))

class PerturbationEvidenceCredit:

    def _scientific_credit_invocation(self, services, context, receiver_selection):
        workflow = services.workflow
        local = len(context.path) > 1
        projector = workflow.scientific_projector_for_context(context)
        arguments = {}
        if local:
            request = context.request
            contract = request['report_contract']
            arguments.update(assignment={'goal': plain(request['goal']), 'scope': plain(context.scope), 'purpose': contract['decision'], 'schema': plain(contract['measurements']['schema']), 'initial_report': plain(request['message']['initial_report'])}, episode_id=context.episode_id, run_id=context.run_id)
            annotation = services.proposed_annotation_for(context)
            if annotation is not None:
                arguments['assignment']['proposed_annotation_ref'] = annotation
            elif services.annotation_task_required():
                raise ValueError('scientific_task_requires_original_proposed_annotation')
        arguments.update(workflow.projector_receipt_arguments(projector, context.episode_id))
        result = workflow.projection_view(projector, plain(context.scope), **arguments)
        if local and arguments['assignment'].get('proposed_annotation_ref') is not None:
            result['proposed_annotation_ref'] = arguments['assignment']['proposed_annotation_ref']
        return result

    def credit_kind(self, role):
        self._role(role)
        return "scientific"

    def credit_projector(self, context):
        if context.role != ROLE:
            return None
        if self._yield_bindings is not None and not context.assignment.get("proposed_annotation_ref"):
            raise ContractError("scientific_task_proposed_annotation_required")
        selection = self._original_selection(context)
        axis = selection[selection_fields(selection)[0]]
        if self.library.resolve(axis).get("entry_version") not in (INSTRUCTION_VERSION, EVIDENCE_AXIS_VERSION):
            return None
        return original_task_projector(context.assignment)

    def credit_view(self, context, receiver_selection):
        self.validate_context(context)
        invocation = getattr(self.services, 'scientific_credit_for', None)
        if callable(invocation):
            return invocation(self._scientific_credit_invocation, context, receiver_selection)
        return self.services.scientific_credit(context, receiver_selection)
