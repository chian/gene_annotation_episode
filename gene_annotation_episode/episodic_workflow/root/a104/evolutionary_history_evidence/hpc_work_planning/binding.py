"""The A104 HPC planning (``hpc``) and resource prediction (``hpc_prediction``) bindings.

Constructed by the A104 home factory (``runtime_bindings.a104_home``) for the two roles. Their
decision source, credit and continuation are ``hpc_runtime``; every other hook is the A104
descendant binding's own (``runtime_bindings.DescendantBinding``).
"""
from __future__ import annotations

from ..runtime_bindings import DescendantBinding
from .hpc_runtime import PLANNING, PREDICTION, HPCRuntime


class HPCBinding(HPCRuntime, DescendantBinding):
    """An A104 ``hpc`` or ``hpc_prediction`` episode over the commission's own HPC ledger."""

    def __init__(self, binding_path, role, commissioning_parent, child_slots, roles_by_grain):
        if role not in (PLANNING, PREDICTION):
            raise ValueError('a104_hpc_binding_role_must_be_hpc_or_hpc_prediction:' + str(role))
        super().__init__(binding_path, role, commissioning_parent, child_slots, roles_by_grain)

    @property
    def hpc_role(self):
        return self.role


__all__ = ['HPCBinding']
