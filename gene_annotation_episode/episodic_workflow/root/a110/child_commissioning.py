"""Select the existing six annotation entry counterpart implementations."""

def child_request_assembler(role):
    if type(role) is not str:
        return None
    if role == 'launch':
        from .to_child_execution_job_submission import assemble_request
        return assemble_request
    if role == 'monitor':
        from .to_child_execution_progress_assessment import assemble_request
        return assemble_request
    if role == 'results':
        from .to_child_execution_result_acquisition import assemble_request
        return assemble_request
    if role == 'hpc':
        from .to_child_hpc_work_planning import assemble_request
        return assemble_request
    if role == 'scientific_process':
        from .to_child_scientific_process import assemble_request
        return assemble_request
    if role == 'literature':
        from .to_child_published_evidence_assessment import assemble_request
        return assemble_request
    return None

def child_report_receiver(role):
    if type(role) is not str:
        return None
    if role == 'launch':
        from .from_child_execution_job_submission import receive_report
        return receive_report
    if role == 'monitor':
        from .from_child_execution_progress_assessment import receive_report
        return receive_report
    if role == 'results':
        from .from_child_execution_result_acquisition import receive_report
        return receive_report
    if role == 'hpc':
        from .from_child_hpc_work_planning import receive_report
        return receive_report
    if role == 'scientific_process':
        from .from_child_scientific_process import receive_report
        return receive_report
    if role == 'literature':
        from .from_child_published_evidence_assessment import receive_report
        return receive_report
    return None
