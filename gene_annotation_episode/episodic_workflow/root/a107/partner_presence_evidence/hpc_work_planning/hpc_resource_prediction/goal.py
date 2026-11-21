"""What this episode is for: the resource prediction of A107 hpc work planning (old role ``hpc_prediction``). The old
``goal.py`` (``PredictionGoal.instructions``) at 97308b94c was the whole instruction text; its sentences that carry a
decision are kept in ``task.INSTRUCTIONS``, which the model reads, and the goal here states the target."""

BINDING_PATH = 'partner_presence_evidence/hpc_work_planning/hpc_resource_prediction'
GOAL = ('Predict the time and resources the commissioned HPC work needs and record that expectation in the HPC '
        'ledger of the commission: a time/resource model fitted on measured cases, with its measured held-out '
        'quality, and a comparison of the candidate portfolios under it.')
UNIT = ('one selected operation on the HPC ledger of the commission: fit a model on selected measured cases, observe '
        'the queue once, compare the candidate portfolios, propose a candidate portfolio, run one read-only '
        'discovery command, read a ledger record, or refresh the shared timing history')
RESULT = ('the credit earned by the measured improvement of the resource model, what the ledger holds after the '
          'episode in counts, and the rows of the ledger in custody')
