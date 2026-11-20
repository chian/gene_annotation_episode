"""What this episode is for. The intention is the old ``launch_local`` role (``goal.py`` at ``97308b94c``), stated
plainly: its parent commissions it with the words "Carry out the assigned job on the selected local resource and
return its usable execution handoff" (``../messages/msg_to_child.py``), and the old return was the usable execution
handoff (the latest received check of the job on that resource) with the resource's facts. The old tail sentences
(preserve the parent's job; capabilities and estimates inform but do not select; unknown or authentication-required
resources stay explicit; only the controller continues) are kept, in the same meaning."""

BINDING_PATH = 'sequence_homology_evidence/resource_work_submission/local_resource_work_execution'
GOAL = ('Carry out the parent\'s assigned job on the one local resource it selected, and end with a usable '
        'execution handoff: the job started on that resource and a receiving check that shows its results can be '
        'received. Work through the resource\'s own interfaces: prepare the job and its inputs, run it, and check '
        'that it can be received. Choose each step from what the resource\'s tools and your earlier outcomes show. '
        'The resource\'s capabilities and duration estimates inform the choice; they do not fix an approach or an '
        'order. Keep the parent\'s job, input versions, CPU, search and constraints as given. If the resource is '
        'unknown or needs authentication, say so; do not work around it. Record your interpretation of the work '
        'for the parent with the report action. You do not decide when to stop: only the configured local '
        'controller does.')
UNIT = ('one tool of the selected local resource, one typed reasoning commit, one wait on native job events or '
        'one recorded interpretation of the report')
RESULT = ('the credit, the finding on the selected local resource and, when selected, the execution handoffs, '
          'the resource facts and the recorded interpretation')

