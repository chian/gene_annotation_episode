"""The A104 HPC allocation execution (``hpc_execution``) binding.

Constructed by the A104 home factory (``runtime_bindings.a104_home``) for the ``hpc_execution`` role. Its
decision source, credit and continuation are ``allocation_runtime``; every other hook is the A104
descendant binding's own (``runtime_bindings.DescendantBinding``).
"""
from __future__ import annotations

from ...runtime_bindings import DescendantBinding
from .allocation_runtime import EXECUTION, AllocationRuntime


class AllocationBinding(AllocationRuntime, DescendantBinding):
    """An A104 ``hpc_execution`` episode over one frozen plan of its owner's HPC ledger."""

    def __init__(self, binding_path, role, commissioning_parent, child_slots, roles_by_grain):
        if role != EXECUTION:
            raise ValueError('a104_hpc_allocation_binding_role_must_be_hpc_execution:' + str(role))
        super().__init__(binding_path, role, commissioning_parent, child_slots, roles_by_grain)


__all__ = ['AllocationBinding']
