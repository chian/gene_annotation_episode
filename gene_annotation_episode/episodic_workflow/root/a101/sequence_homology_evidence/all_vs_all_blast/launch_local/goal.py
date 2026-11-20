"""What this episode is for: the launch of one chunk of an all-vs-all search on one assigned local resource. It ends at
handoff."""

BINDING_PATH = 'sequence_homology_evidence/all_vs_all_blast/launch_local'
GOAL = ('Launch the search of one chunk of the commissioned sequence set against the whole set as a detached job on '
        'the assigned local resource, and return its handoff record and its job record')
UNIT = 'One defined launch action: the launch of the assigned chunk'
RESULT = ('The handoff record and the job record of the launched chunk, whether the handoff exists, and the counts '
          'of the launches that were handed off or refused')
