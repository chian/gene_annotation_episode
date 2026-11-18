"""Private A107 scientific report_integrity."""
from __future__ import annotations
from .scientific_assignment_contracts import AXIS, ContractError, ReportBoundaryError, plain

class ScientificReportIntegrity:

    def _validate_component_axis_report(self, context, form, schema):
        from dataclasses import replace
        from gene_annotation_episode.episodic_workflow.root.a107.component_axis_reports import report_axis, resolve_report
        axis = report_axis(schema)
        if axis is None:
            return
        if axis != AXIS:
            raise ContractError('component_axis_report_requires_original_axis')
        workflow = getattr(self.services, 'workflow', None)
        if workflow is None:
            raise ContractError('component_axis_report_store_required')
        received = self.services.record_selection(context)
        if received.get('run_id') != context.run_id or received.get('episode_id') != context.episode_id:
            raise ContractError('component_axis_report_receiver_mismatch')
        current = replace(context, received_record_refs=tuple(received['known_record_refs']))
        try:
            resolve_report(workflow.store, plain(form), context=current, services=self.services, axis=AXIS)
        except ContractError as error:
            raise ReportBoundaryError('The axis report requires its actual received component evidence', code=str(error)) from error
