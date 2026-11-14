"""Exact captured original callback; test-only comparison asset."""
def initial_decision_context(self, context):
    if self.local_file_sources.applies(context):
        target = self._target(context)
        return {'execution_resource_capabilities': [{'resource_id': target['resource_id'],
            'resource_kind': 'local'}], 'execution_initial_information': {}}
    value = {'execution_resource_capabilities': [self._resource_information(key) for key in self.resources],
        'execution_initial_information': deepcopy(self.initial_information),
        'received_bvbrc_values': [] if self.api_execution is None else
            self.api_execution.received_bvbrc_context(context)}
    if (context.role in {'annotation', 'scientific_process'}
            and self.api_execution is not None
            and any(service.service == 'ncbi_blast' for service in self.api_execution.services.values())):
        jobs = self.api_execution.received_blast_jobs(context, self.job_progress_provider)
        for job in jobs:
            job.update(self._blast_scientific_owner(job['origin_episode_id']))
        value['received_blast_jobs'] = (self._blast_axis_summaries(jobs)
            if context.role == 'annotation' else jobs)
        value['received_blast_jobs_meaning'] = (
            'Saved original BLAST jobs for received handoffs; root sees one summary per '
            'annotation, axis and subject, while the scientific owner sees its original handles. '
            'Status is only as of observed_at; the scheduling estimate is recalculated '
            'locally as of forecast_as_of without a new provider observation. '
            'No status request is made to build this view. The scientific owner can work locally or '
            'return its handoff upward; the annotation root can choose another axis. A later owner '
            'may monitor or fetch the same handoff without a new submission. Waiting earns no '
            'scientific credit.')
    if self.native_rna_structure_returns is not None and context.role in {'annotation', 'scientific_process'}:
        value['received_rna_structure_values'] = self.native_rna_structure_returns.received_context(context)
        value['received_rna_comparison_values'] = self.rna_structure_comparison_returns.received_context(context)
    return value
