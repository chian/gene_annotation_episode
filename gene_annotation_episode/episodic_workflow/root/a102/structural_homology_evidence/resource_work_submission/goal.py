"""What this episode is for: the old ``launch`` responsibility of the resource episode. It chooses the resource
the assigned work is launched on and commissions the resource child of that kind."""

BINDING_PATH = 'structural_homology_evidence/resource_work_submission'
GOAL = ('Choose which actual execution approach is productive within the assigned job and constraints; commission '
        'a resource child when useful')
UNIT = ('One resource tool (a reading of one declared resource or a receiving check of a returned handoff), one '
        'lookup into the tool-knowledge or launch-instruction library, or one '
        'commission of the resource child (api, local or hpc) that launches the assigned work on a chosen resource')
RESULT = ('The credit, the finding (the state of the launched job and the kind of route it was launched on) '
          'and, in custody, the handoff record of the job; its receiving check records when selected')
