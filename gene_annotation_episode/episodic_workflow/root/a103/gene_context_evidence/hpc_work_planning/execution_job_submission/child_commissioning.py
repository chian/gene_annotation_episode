"""Private A103 launch child commissioning."""
from __future__ import annotations
from .contracts import KINDS, ROLE_KINDS, plain

from .from_child_api_job_execution import receive_api_job_report
from .from_child_local_job_execution import receive_local_job_report
from .from_child_hpc_job_execution import receive_hpc_job_report

from .to_child_api_job_execution import assemble_api_job_execution_request
from .to_child_local_job_execution import assemble_local_job_execution_request
from .to_child_hpc_job_execution import assemble_hpc_job_execution_request

class LaunchChildCommissioning:

    def child_roles(self, role):
        return tuple(ROLE_KINDS) if role == 'launch' else ()

    def allowed_children(self, parent, caller_capabilities):
        if parent.role != 'launch':
            return ()
        assignment = self._launch(plain(parent.assignment))
        return tuple((role for role, kind in ROLE_KINDS.items() if any((KINDS[configuration['kind']] == kind and self._permitted(assignment, resource_id) for resource_id, configuration in self.resources.items()))))

    def child_report_receiver(self, role):
        if role == 'launch_api':
            return receive_api_job_report
        if role == 'launch_local':
            return receive_local_job_report
        if role == 'launch_hpc':
            return receive_hpc_job_report
        return None

    def child_request_assembler(self, role):
        """Select this parent's private outgoing request envelope."""
        if role == 'launch_api':
            return assemble_api_job_execution_request
        if role == 'launch_local':
            return assemble_local_job_execution_request
        if role == 'launch_hpc':
            return assemble_hpc_job_execution_request
        return None
