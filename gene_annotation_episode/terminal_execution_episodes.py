"""Instruction-led Launch roles using the ordinary episode tool-action loop.

The command executor supplies transport and immutable factual receipts. The LLM
chooses shell code, scripts, environment, recovery and subsequent actions.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .communication import plain, validate_form
from .domain import validate_schema
from .acquisition import AcquisitionError
from .practical_execution_operations import confined
from .practical_execution_records import ASSIGNMENT_SCHEMA, assess_validations, validate_assignment
from .practical_execution_state import PracticalState
from .terminal_execution import TerminalExecution, digest


VERSION = 'terminal_execution_episodes_v1'
ROLE_KINDS = {'launch_local':'local','launch_hpc':'hpc'}


def operation_catalog(kind):
    """General execution capability, identical for every resource."""
    if kind not in {'local','hpc'}:
        raise ValueError('execution_resource_kind_invalid')
    return [{'name':'exec_command','description':
        'Execute the shell command you write on the assigned resource. Use normal shell/file '
        'tools to inspect files, author scripts, prepare an environment, run software, or '
        'submit/observe the actual job as needed. Returns its actual output and saved action receipt. '
        'workdir and env apply to this command; select them explicitly on each action.',
        'input_schema':{'type':'object','properties':{
            'cmd':{'anyOf':[{'type':'string','minLength':1},
                {'type':'array','minItems':1,'items':{'type':'string','minLength':1}}]},
            'workdir':{'type':'string','minLength':1},
            'target':{'type':'string','enum':['resource','coordinator'],
                'description':'Assigned resource (default), or local coordinator run directory for input-file work.'},
            'env':{'type':'object','additionalProperties':{'type':'string'}}},
            'required':['cmd','workdir','env'],'additionalProperties':False}}]


class TerminalExecutionEpisodes:
    def __init__(self, services, *, directory, resources, store=None,
                 initial_information=None, flux_balance_input_reader=None):
        self.services,self.directory,self.store=services,Path(directory),store
        self.resources=json.loads(json.dumps(plain(resources),allow_nan=False))
        if not self.resources or not set(self.resources)<={'local','hpc'}:
            raise ValueError('explicit_execution_resources_required')
        self.initial_information=plain(initial_information or {})
        if not set(self.initial_information)<=set(self.resources):
            raise ValueError('initial_inventory_resource_not_bound')
        # Inventory is historical resource context. It does not define a menu of
        # allowed job stages and is not an observation of current usability.
        self.roles=tuple(role for role,kind in ROLE_KINDS.items() if kind in self.resources)
        self.entry_roles=self.roles
        self._states={}

    def _operations(self,kind):
        from .terminal_scientific_evidence import terminal_artifact_paths
        return TerminalExecution(self.resources[kind],coordinator_workspace=self.directory,
            artifact_selector=terminal_artifact_paths)

    def _assignment(self,context):
        assignment=validate_assignment(plain(context.assignment))
        kind=ROLE_KINDS.get(context.role)
        if assignment['resource_kind']!=kind or kind not in self.resources:
            raise ValueError('execution_resource_assignment_mismatch')
        self._operations(kind).validate_assignment(assignment)
        return assignment

    def _state_directory(self,context):
        # Preserve the host receipt location and source identity. No model must
        # construct this path or maintain an additional job ledger.
        return self.directory/'practical-execution'/digest({
            'run_id':context.run_id,'episode_id':context.episode_id})

    def initialize(self,context):
        assignment=self._assignment(context);directory=self._state_directory(context)
        state=PracticalState(directory,context.run_id,context.episode_id,assignment,
            **({} if (directory/'assignment.json').is_file() else {
                'initial_outcome':{'facts':{}},
                'initial_validations':assess_validations(assignment,{'facts':{}},assignment['initial_context'])}))
        self._states[context.episode_id]=state
        return state

    def state(self,context):
        return self._states.get(context.episode_id) or self.initialize(context)

    def as_record(self):
        return {'binding_id':'terminal_execution','version':VERSION,
            'configuration':{'resources':deepcopy(self.resources),
                'initial_information':deepcopy(self.initial_information)}}

    def child_roles(self,role):return ()
    def credit_kind(self,role):return 'operational'
    def assignment_schema(self,role):return deepcopy(ASSIGNMENT_SCHEMA)
    def permitted_common_actions(self,context):return ('tool',)
    def allowed_children(self,parent,caller_capabilities):return ()

    def prepare_assignment(self,parent,role,selection,scope,operation_key):
        assignment=validate_assignment(plain(selection))
        if ROLE_KINDS.get(role)!=assignment['resource_kind']:
            raise ValueError('execution_resource_assignment_mismatch')
        return self._operations(assignment['resource_kind']).validate_assignment(assignment)

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

    def catalog(self,context):
        return operation_catalog(self._assignment(context)['resource_kind'])

    async def execute(self,context,tool_name,arguments,operation_key):
        arguments=plain(arguments)
        try:
            catalog={entry['name']:entry for entry in self.catalog(context)}
            if tool_name not in catalog:raise ValueError('execution_tool_not_available')
            validate_schema(arguments,catalog[tool_name]['input_schema'])
            operations=self._operations(context.assignment['resource_kind'])
            operations.validate_action(plain(context.assignment),tool_name,arguments)
        except (ValueError,TypeError) as error:
            return {'status':'invalid','record_refs':[],'changed_record_refs':[],'result':None,
                'feedback':{'category':'arguments_or_reference','code':str(error)}}
        state=self.state(context);intent=state.begin(operation_key,tool_name,arguments)
        if intent['state']=='completed':receipt=intent['receipt']
        else:
            try:
                outcome,_=await operations.execute(state,tool_name,arguments,operation_key)
            except (ValueError,TypeError,OSError,AcquisitionError) as error:
                outcome={'facts':{},'native_outcome':{'failure':{
                    'code':'execution_action_failed','exception_type':type(error).__name__,
                    'detail':str(error)}}}
            from .terminal_scientific_evidence import finalize_scientific_command
            outcome=finalize_scientific_command(plain(context.assignment),arguments,outcome)
            before=state.context()
            after=deepcopy(before)
            if arguments.get('target','resource')=='resource' and Path(arguments['workdir']).is_relative_to(context.assignment['workspace']):
                after.update({'cwd':arguments['workdir'],'environment':arguments['env']})
            after['revision']+=int(any(after[name]!=before[name] for name in ('cwd','environment')))
            validations=assess_validations(plain(context.assignment),outcome,after,tool_name=tool_name)
            receipt=state.finish(operation_key,outcome,validations,context_after=after)
        references=[]
        if self.store is not None:
            from .practical_receipt_information import PracticalReceiptInformation
            references.append(PracticalReceiptInformation(self.store,context.run_id).publish(context,receipt))
        return {'status':'completed','record_refs':references,'changed_record_refs':references,
            'operation_ref':digest(operation_key),'result':receipt}

    def completion_for_action(self,context,operation_key):
        proof=self.state(context).completion_proof()
        return proof if proof is not None and proof['operation_key']==operation_key else None

    def practical_estimator(self,context):
        from .practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(self.state(context).verify_completion)

    def fact_sources(self,role):
        return {'practical_completed':{'type':'boolean','meaning':
                'Whether original requested endpoint predicates have a saved validated completion.'},
            'practical_receipt_digests':{'type':'array','meaning':
                'Host-recorded digests of the original selected command receipts.'},
            'practical_receipt_refs':{'type':'array','meaning':
                'Original selected command, actual result and earned operational credit sources.',
                'report_schema':{'type':'array','uniqueItems':True,'items':{
                    'type':'string','format':'reference','x-reference-namespace':'practical_receipt'},
                    'x-source':'practical_receipt_refs'}}}

    def facts(self,context,completion_snapshot):
        state=self.state(context);references=[]
        if self.store is not None:
            from .practical_receipt_information import PracticalReceiptInformation
            information=PracticalReceiptInformation(self.store,context.run_id)
            references=[information.publish(context,receipt) for receipt in state.receipts()]
        return {'practical_completed':state.completion_proof() is not None,
            'practical_receipt_digests':[digest(receipt) for receipt in state.receipts()],
            'practical_receipt_refs':references}

    def resolve(self,context,reference,namespace):
        if self.store is not None and isinstance(reference,str) and reference.startswith('source_'):
            from .practical_receipt_information import PracticalReceiptInformation
            return PracticalReceiptInformation(self.store,context.run_id).resolve(context,reference,namespace)
        return namespace=='practical_receipt' and reference in {digest(row) for row in self.state(context).receipts()}

    def validate_report(self,context,form,original_schema):
        validate_form(form,original_schema,lambda reference,namespace:self.resolve(context,reference,namespace))
        facts=self.facts(context,{})
        for name,node in original_schema.get('properties',{}).items():
            source=node.get('x-source')
            if source in facts and form[name]!=facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')

    def credit_view(self,context,receiver_selection):return self.state(context).credit_view()
