"""What this episode is for (carried from the old ``goal.py``, ``OperationalGoal.instructions`` at ``97308b94c``, role
``launch``). The old text was the ``launch`` responsibility sentence plus the common tail. The contract-information
``discovery`` paragraph (``request_context`` with ``view=composition_information``) described the old decision
exchange and the parent-written return form; neither exists any more (the child declares what it can return and
this episode selects it in ``msg_to_child``), so it is not carried. The instruction composition is in task.py."""

BINDING_PATH = 'sequence_homology_evidence/resource_work_submission'
GOAL = ('Choose which actual execution approach is productive within the assigned job and constraints; commission a '
        'resource child when useful. Revise later choices from actual outcomes. Ordinary operations are tools; '
        'iteration belongs to this shared Episode. Preserve the parent job, input versions, CPU, search and '
        'constraints. Capabilities and duration estimates inform your decisions, without selecting an approach or '
        'imposing an order. Unknown/authentication-required resources remain explicit. Return the original '
        'parent-defined typed form. Only the configured local controller governs continuation.')
UNIT = ('One selected action: a read of the resource capabilities, one resource inspection, one handoff check, a '
        'typed reasoning commit, a library lookup, or one commission of the API, local or HPC resource child on '
        'the one resource it selects')
RESULT = ('The usable execution handoffs the resource children returned or this episode checked, the facts the '
          'resource adapters recorded, and the handoff records held in custody')
