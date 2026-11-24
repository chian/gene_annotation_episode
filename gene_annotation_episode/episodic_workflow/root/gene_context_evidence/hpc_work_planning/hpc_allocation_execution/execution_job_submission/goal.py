"""What this episode is for (carried from the old ``goal.py`` at ``97308b94c``; its instruction text is in task.py)."""

BINDING_PATH = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
GOAL = ('Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, '
        'recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs, '
        'constraints and pinned instructions. A resource child owns iterative execution in the shared loop. Receive '
        'its requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff '
        'completes this launch endpoint with exact zero future credit.')
UNIT = ('one read of the bound resources\' capabilities and recorded inventory, or one commission of the resource '
        'child that executes one permitted request on its explicit resource_id')
RESULT = ('the usable handoffs the resource children returned for the permitted requests: their references, '
          'whether a handoff is complete, and the credit they earned')
