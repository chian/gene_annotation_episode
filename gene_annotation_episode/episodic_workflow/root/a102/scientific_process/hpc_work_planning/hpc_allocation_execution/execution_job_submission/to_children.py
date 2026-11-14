"""Private A102 Launch to children."""
from __future__ import annotations
from .execution_contracts import KINDS, ROLE_KINDS, plain

from .from_child_api_job_execution import receive_report as receive_api_report

from .from_child_local_job_execution import receive_report as receive_local_report

from .from_child_hpc_job_execution import receive_report as receive_hpc_report

class LaunchToChildren:

    def child_roles(self, role):
        return tuple(ROLE_KINDS) if role == 'launch' else ()

    def allowed_children(self, parent, caller_capabilities):
        if parent.role != 'launch':
            return ()
        assignment = self._launch(plain(parent.assignment))
        return tuple((role for role, kind in ROLE_KINDS.items() if any((KINDS[configuration['kind']] == kind and self._permitted(assignment, resource_id) for resource_id, configuration in self.resources.items()))))

    def child_report_receiver(self, role):
        if role == 'launch_api':
            return receive_api_report
        if role == 'launch_local':
            return receive_local_report
        if role == 'launch_hpc':
            return receive_hpc_report
        return None

    def child_request_assembler(self, role):
        """Select the named private outgoing envelope for this Launch child."""
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
