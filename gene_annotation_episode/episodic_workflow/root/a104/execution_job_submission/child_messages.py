"""Launch-owned native request and report endpoints."""
from __future__ import annotations

class LaunchChildMessages:

    def child_request_assembler(self, role):
        if role == 'launch_api':
            from .to_child_api_job_execution import assemble_request
            return assemble_request
        if role == 'launch_local':
            from .to_child_local_job_execution import assemble_request
            return assemble_request
        if role == 'launch_hpc':
            from .to_child_hpc_job_execution import assemble_request
            return assemble_request
        return None

    def child_report_receiver(self, role):
        if role == 'launch_api':
            from .from_child_api_job_execution import receive_report
            return receive_report
        if role == 'launch_local':
            from .from_child_local_job_execution import receive_report
            return receive_report
        if role == 'launch_hpc':
            from .from_child_hpc_job_execution import receive_report
            return receive_report
        return None
