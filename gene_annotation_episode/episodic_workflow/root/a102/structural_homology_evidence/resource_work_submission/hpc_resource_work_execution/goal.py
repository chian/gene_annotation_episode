"""What this episode is for.

Carried from the old ``goal.py`` (``ResourceGoal.instructions``: the responsibility sentence and the common tail).
``contract_information_profile`` returned ``None`` for this episode, so the ``request_context`` discovery paragraph
was never added."""

BINDING_PATH = 'structural_homology_evidence/resource_work_submission/hpc_resource_work_execution'
GOAL = ('Investigate the selected actual environment, queue, staging and execution interfaces. Revise later '
        'choices from actual outcomes. Ordinary operations are tools; iteration belongs to this shared Episode. '
        'Preserve the parent job, input versions, CPU, search and constraints. Capabilities and duration '
        'estimates inform your decisions, without selecting an approach or imposing an order. '
        'Unknown/authentication-required resources remain explicit. Return the original parent-defined typed '
        'form. Only the configured local controller governs continuation.')
UNIT = ('One resource operation: a read of the capabilities, an inspection of the resource, a handoff check or '
        'one tool of the selected HPC resource')
RESULT = ('The usable execution handoffs found for the commissioned job on the selected HPC resource, held in '
          'custody, with credit and the finding')
