"""What this episode is for (old ``goal.py``: ``ResourceGoal.instructions``).

The old goal also carried, when a contract information profile was configured, the paragraph that described
``request_context`` with ``episode.return_contract``. That is the decision-exchange protocol, which is not carried
(the parent selects among the child's declared return fields in ``msg_to_child``), so the paragraph is not part of
the goal."""

BINDING_PATH = 'gene_context_evidence/resource_work_submission'
GOAL = ('Choose which actual execution approach is productive within the assigned job and constraints; commission '
        'a resource child when useful. Revise later choices from actual outcomes. Ordinary operations are tools; '
        'iteration belongs to this shared Episode. Preserve the parent job, input versions, CPU, search and '
        'constraints. Capabilities and duration estimates inform your decisions, without selecting an approach or '
        'imposing an order. Unknown/authentication-required resources remain explicit. Return the original '
        'parent-defined typed form. Only the configured local controller governs continuation.')
UNIT = ('One resource tool, typed reasoning commitment or wait, or one commission of a resource child '
        '(api, local or hpc) for the assigned job')
RESULT = ('The execution handoff facts gathered from the resource children and the receiving checks, with the '
          'handoff records in custody')
