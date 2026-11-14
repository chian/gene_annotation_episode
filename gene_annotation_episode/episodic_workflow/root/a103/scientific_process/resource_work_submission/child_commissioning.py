"""Private A103 resource child commissioning."""
from __future__ import annotations
from .resource_contracts import RESOURCE_ROLES

class ResourceChildCommissioning:

    def child_roles(self, role):
        return tuple(RESOURCE_ROLES)

    def allowed_children(self, parent, caller_capabilities):
        if parent.role != 'launch':
            return ()
        capabilities = self.capabilities()
        return tuple((role for role, kind in RESOURCE_ROLES.items() if any((value['kind'] == kind and value['resource_id'] in self.adapters and value['tool_names'] and (value['availability'] != 'unavailable') and self._permitted(parent.assignment, value) for value in capabilities))))

    def child_request_assembler(self, role):
        """Select this Resource parent's named child request owner."""
        if role == 'launch_api':
            from .to_child_api_resource_work_execution import assemble_request
            return assemble_request
        if role == 'launch_local':
            from .to_child_local_resource_work_execution import assemble_request
            return assemble_request
        if role == 'launch_hpc':
            from .to_child_hpc_resource_work_execution import assemble_request
            return assemble_request
        return None
