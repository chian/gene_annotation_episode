"""Original fixed hpc execution instructions responsibilities; source candidate."""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.communication import plain


class HPCInstructions:
    def initial_decision_context(self,context):
        return {'execution_resource_information':deepcopy(self.initial_information)}

    def _resource_information(self,kind):
        configuration=self.resources[kind]
        return {'resource_kind':kind,'workspace':configuration['workspace'],
            **{name:deepcopy(configuration[name]) for name in (
                'kind','policy','account','ssh_argv','python_executable','scheduler')
                if name in configuration},
            'inventory_snapshot':deepcopy(self.initial_information.get(kind))}

    def _resource_instructions(self,context):
        workflow=getattr(self.services,'workflow',None)
        library=getattr(workflow,'launch_instructions',None)
        if library is None:return None
        return library.for_resource(self.resources[context.assignment['resource_kind']])

    def instructions(self,context):
        instructions=(
            'You are the execution agent for the actual job and resource assigned below. '
            'Use exec_command to write and run the shell code needed for that job. '
            'Choose scripts, environment preparation, software invocation and recovery from '
            'the actual resource instructions and observed results. No sequence of setup or '
            'job-stage operations is prescribed. Preserve the caller\'s scientific inputs, '
            'desired outputs and acceptance criteria. Historical inventory is context, not '
            'proof of present usability. Each command is one ordinary episode action: its '
            'actual result and earned credit enter the iterator, including failure or zero '
            'progress. Host bookkeeping records command versions and actual native job '
            'identities; do not maintain a parallel receipt ledger. If a submission outcome '
            'is uncertain, investigate that original submission rather than create a duplicate. '
            'Use the provided resource-specific instructions, account, storage and existing '
            'authentication route. workdir and env apply to the selected command only. '
            'target=resource runs on the assigned resource; target=coordinator runs in the '
            'local run directory for supplied-input and transport work. Both are ordinary '
            'journaled actions; resource computation belongs on its actual allocation. '
            'For coordinator-side transfers, execution_resource.ssh_argv, when present, '
            'is the exact configured transport prefix. Append the remote shell command '
            'as its final argument and preserve stdin. The supplied configuration gives '
            'the existing connection details. target=resource uses that transport directly. '
            'The episode iterator decides continuation from credit; add no stopping budget.')
        selected=self._resource_instructions(context)
        if selected:
            instructions+='\nResource instructions supplied from the frozen library:\n'+'\n\n'.join(
                section['text'] for section in selected['sections'])
        return instructions

    def decision_context(self,context,current_view):
        state=self.state(context)
        return {'execution_assignment':plain(context.assignment),
            'execution_resource':self._resource_information(context.assignment['resource_kind']),
            'coordinator_workspace':str(self.directory.resolve()),
            'execution_progress':state.credit_view(),
            'execution_completion':state.completion_proof()}

