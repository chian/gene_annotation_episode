"""The A104 local job execution bindings (role ``launch_local``) on the generic runner.

The A104 table (``runtime_bindings.EPISODES``) declares three local job execution episodes (below the
head, below HPC work planning and below HPC allocation execution). Each is a ``LocalJobBinding``: an
A104 descendant (its path, role, commissioning parent, ``{scope, assignment}`` assignment form and
``{credit, report}`` return form) whose hooks are the A104 local job runtime
(``episode_support/jobs/local_execution/evolutionary_history_evidence/local_job_runtime.py``): exec_command decisions over its own ``TerminalExecution`` on
the configured local resource, practical requirement credit and completion continuation.

``construct`` is called by ``runtime_bindings.a104_home`` with ``services['a104']['local_job_execution']``:
``resource``, ``coordinator_workspace``, ``state_directory``, ``launch_instruction_directory`` and
``continuation`` (``{'cutoff', 'uncertainty_alpha'}``), each required.
"""
from __future__ import annotations

from collections.abc import Mapping

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.evolutionary_history_evidence.local_job_runtime import A104LocalJobRuntime

from ...runtime_bindings import DescendantBinding

ROLE = 'launch_local'
OPERANDS = frozenset({'resource', 'coordinator_workspace', 'state_directory', 'launch_instruction_directory',
                      'continuation'})


class LocalJobBinding(A104LocalJobRuntime, DescendantBinding):
    """One A104 local job execution episode."""

    def __init__(self, binding_path, role, commissioning_parent, child_slots, roles_by_grain, **operands):
        if role != ROLE:
            raise ContractError('a104_local_job_binding_role_must_be_launch_local:' + binding_path)
        DescendantBinding.__init__(self, binding_path, role, commissioning_parent, child_slots, roles_by_grain)
        A104LocalJobRuntime.__init__(self, **operands)


def construct(operands, path, role, parent, child_slots, roles_by_grain):
    """The local job binding at ``path`` with its own TerminalExecution over the configured local resource."""
    if not isinstance(operands, Mapping) or set(operands) != OPERANDS:
        raise ContractError('a104_local_job_execution_operands_require_exactly:' + ','.join(sorted(OPERANDS)))
    return LocalJobBinding(path, role, parent, child_slots, roles_by_grain, **dict(operands))


__all__ = ['LocalJobBinding', 'OPERANDS', 'construct']
