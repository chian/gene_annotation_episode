"""Original own-A103 Scientific received_execution_context."""


def received_execution_context(context, workflow):
    if (workflow is None or getattr(workflow.tools, 'a103_execution_resources', None) is None
            or (context.role != 'annotation' and context.assignment.get('selection', {}).get(
                'evidence_axis', {}).get('option_id') not in {'A103', 'A107'})):
        return {}
    from ..a103_hpc import execution_findings
    return {'received_gene_context_execution': execution_findings(
        workflow.store, context, set(context.received_record_refs))}
