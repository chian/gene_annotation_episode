"""What this episode is for (carried from the old ``goal.py``, ``OperationalGoal.instructions`` at ``97308b94c``; its
instruction composition is in task.py)."""

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment/execution_job_submission'
GOAL = ('Choose which permitted concrete execution request to commission on an explicit resource_id. Capabilities, '
        'recorded inventory and timing information inform the choice. Preserve the original job, immutable inputs, '
        'constraints and pinned instructions. A resource child carries out iterative execution in the private loop. '
        'Receive its requested typed handoff; no infrastructure chooses an approach. Actual received usable handoff '
        'completes this launch endpoint with exact zero future credit.')
UNIT = ('One selected action: a read of the configured resource capabilities, a typed reasoning commit, or one '
        'commission of the API job execution child that carries out one permitted concrete execution request on an '
        'explicit resource_id')
RESULT = ('The usable handoff facts of the commissioned execution requests: the resources that handed off, whether a '
          'handoff is verified complete, and the references that hold the handoffs')
