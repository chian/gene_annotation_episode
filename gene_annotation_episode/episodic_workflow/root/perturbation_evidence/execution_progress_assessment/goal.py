"""What this episode is for: the monitor of one launched job (old role ``monitor``), in the 'launch, monitor,
extract' design (``docs/axis_restructure_20261117/LAUNCH_MONITOR_EXTRACT_MECHANICS.md``). The intention is carried
from the old ``goal.py`` (``MonitorGoal.instructions``) at 97308b94c; its sentences that carry a decision are kept
in the owner's wording. The goal is the first part of the instructions the model reads (``task.py``)."""

BINDING_PATH = 'perturbation_evidence/execution_progress_assessment'
GOAL = ('You monitor one job. Another episode launched it and your commissioner handed it to you as its handoff '
        'record. The job keeps running whether or not anyone watches it; you do not fetch its results and you do '
        'not stay until it ends. Find out through the job service where the job stands now: its actual state, '
        'whether its results are available, its measured quantities and, when it keeps logs, what they show. Your '
        'commissioner decides from what you return what to do with the job next: check it again later, fetch its '
        'results or cancel it. Liveness establishes process presence only; elapsed time alone establishes neither '
        'productive work nor a stall. Unknown information stays unknown.')
UNIT = ('one selected action: one check of the job (a fresh status request through the job service), one re-read '
        'of a check already held, one window of a log of the job, one wait for the job\'s end event, or one '
        'commissioned monitor for a job the target directly depends on')
RESULT = ('the credit earned by newly informative checks, the finding on the job (whether it was observed, its '
          'state, whether its results are available, when it was observed), the check records in custody, and '
          'the measurements and records the parent selected')
