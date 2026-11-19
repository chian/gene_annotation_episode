"""The A103 head binding (``gene_context_evidence``) on the generic runner.

Commissioned by the root annotation episode. Its decision behaviour is
``runtime_source.GeneContextEvidenceSource`` (model-selected reasoning commits,
A103 tool actions, narrower ``gene_context_evidence`` children and its other declared children); its credit
is A103's own measured-context projection (``a103_credit.A103ContextCredit``)
over the records this episode holds; its continuation is the yield controller
its construction-time declaration binds to that projection.

Construction operands (all required, nothing defaulted):

- ``library``: the frozen A103 scientific library (``GeneContextEvidenceLibrary``);
  its A103 evidence-axis entry is presented with every decision and its thought
  patterns are the options of the commission's ``thought_pattern`` choice;
- ``tool_registry``: the head's own ``A103ToolRegistry`` over the run's shared Store
  (built by the A103 home factory); its catalog names are the options of the
  commission's ``tools`` subset;
- ``child_roles``: the children this head may commission, itself first;
- ``yield_bindings``: ``{'A103:a103_context_credit': {kind, cutoff, parameters, credit_definition}}``.

The commissioning parent chooses, per commission, one thought pattern
(``ChoiceField``) and a subset of the head's tools (``SubsetField``); the root
also fills the values it holds (``scope``, ``evidence_refs`` and, when the entry
supplied them, ``proposed_annotation_ref`` and ``constraints``).
"""
from __future__ import annotations

from collections.abc import Mapping
import json
from types import MappingProxyType

from episode_runtime import ChoiceField, Commission, DeclaredField, Field, RecordForm, SubsetField, grain_name_for
from method_loop import Episode, EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import A103ContextCredit
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import ContractError, canonical
from gene_annotation_episode.episodic_workflow.episode_support.forms.gene_context_evidence.evidence_axis_contracts import VERSION as EVIDENCE_AXIS_VERSION
from gene_annotation_episode.episodic_workflow.episode_support.instructions.gene_context_evidence.evidence_axis_instructions import VERSION as INSTRUCTION_VERSION, instruction_view
from gene_annotation_episode.episodic_workflow.episode_support.configuration.gene_context_evidence.process_options import evidence_axis_instruction_view
from .contract_binding import REPORT, RETURN_FORM, ContractRecord

AXIS = 'A103'
ROLE = 'gene_context_evidence'
# The children a head may commission: itself (a narrower head) and each top-level A103 child home.
CHILD_PATHS = MappingProxyType({ROLE: ROLE, **{home: ROLE + '/' + home for home in (
    'execution_job_submission', 'execution_progress_assessment', 'execution_result_acquisition',
    'hpc_work_planning', 'resource_work_submission', 'resource_result_acquisition',
    'published_evidence_assessment')}})
CONTINUATION_TASK = AXIS + ':a103_context_credit'
_KINDS = {'accumulation', 'bounded_quality', 'completion'}


def _json(value):
    return json.loads(json.dumps(value, allow_nan=False))


class GeneContextEvidenceEpisode:
    """The recursive A103 head: its own model-selected gene-context investigation."""

    binding_path = ROLE
    grain_name = grain_name_for(ROLE)
    goal = ('Improve the gene-context evidence for the assigned subject: received, graded neighbourhood, operon '
            'and synteny observations that support or weaken its proposed annotation')
    unit = 'One selected gene-context action: a reasoning commit, a tool call or a commissioned child investigation'
    result = 'The gene-context evidence report with its graded record references and credit'
    required_collaborators = ('store', 'model_provider')
    return_form = RETURN_FORM
    report_contract = MappingProxyType(dict(REPORT))
    commissioning_parent = 'annotation'

    def __init__(self, *, library, tool_registry, child_roles, yield_bindings):
        if (not isinstance(child_roles, (tuple, list)) or not child_roles or child_roles[0] != ROLE
                or len(set(child_roles)) != len(child_roles)):
            raise ContractError('a103_head_child_roles_invalid')
        undeclared = [role for role in child_roles if role not in CHILD_PATHS]
        if undeclared:
            raise ContractError('a103_head_child_role_not_declared:' + ','.join(undeclared))
        if not callable(getattr(tool_registry, 'execute_async', None)) or not callable(
                getattr(tool_registry, 'current_invocation', None)):
            raise ContractError('a103_head_tool_registry_required')
        self.library, self.tool_registry, self._child_roles = library, tool_registry, tuple(child_roles)
        self.evidence_axis = self._evidence_axis_view(library)
        self.thought_patterns = {
            header['option_ref']['option_id']: self._thought_view(library.resolve(header['option_ref']))
            for header in library.headers() if header['option_ref']['slot'] == 'thought_pattern'}
        self.selectable_tools = tuple(sorted(tool_registry.catalog(None)))
        if not self.thought_patterns or not self.selectable_tools:
            raise ContractError('a103_head_selection_options_required')
        self.credit_projector = A103ContextCredit()
        if not isinstance(yield_bindings, Mapping) or set(yield_bindings) != {CONTINUATION_TASK}:
            raise ContractError('a103_head_yield_binding_required:' + CONTINUATION_TASK)
        declaration = _json(dict(yield_bindings[CONTINUATION_TASK]))
        if (not isinstance(declaration, dict) or set(declaration) != {'kind', 'cutoff', 'parameters', 'credit_definition'}
                or declaration['kind'] not in _KINDS or not isinstance(declaration['parameters'], dict)
                or set(declaration['parameters']) != {'uncertainty_alpha'}):
            raise ContractError('a103_head_yield_binding_invalid:' + CONTINUATION_TASK)
        if canonical(declaration['credit_definition']) != canonical(self.credit_projector.as_record()):
            raise ContractError('a103_head_yield_credit_definition_mismatch:' + CONTINUATION_TASK)
        if declaration['kind'] != self.credit_projector.yield_method:
            raise ContractError('a103_head_yield_method_credit_mismatch:' + CONTINUATION_TASK)
        self.continuation = declaration

    @staticmethod
    def _evidence_axis_view(library):
        entry = library.resolve(library.reference(AXIS))
        if entry.get('entry_version') == INSTRUCTION_VERSION:
            return instruction_view(entry)
        if entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
            return evidence_axis_instruction_view(entry)
        raise ContractError('a103_head_evidence_axis_entry_invalid')

    @staticmethod
    def _thought_view(entry):
        return {name: entry[name] for name in ('id', 'name', 'description', 'use_when', 'live_alternatives',
                                               'decision_guidance', 'outcome_contingencies', 'boundary')
                if name in entry}

    # -- contract hooks -----------------------------------------------------------
    @property
    def child_slots(self):
        return MappingProxyType({role: CHILD_PATHS[role] for role in self._child_roles})

    @property
    def evidence_task(self):
        return {'evidence_axis': AXIS, 'task': CONTINUATION_TASK,
                'credit_definition': self.credit_projector.as_record()}

    @property
    def assignment_form(self):
        return RecordForm({
            'scope': Field('record', 'The subject scope whose gene-context evidence this episode improves'),
            'evidence_task': DeclaredField('record', 'The A103 task and its measured-context credit definition',
                                           self.evidence_task),
            'thought_pattern': ChoiceField('text', 'The library thought pattern this commission investigates with',
                                           tuple(sorted(self.thought_patterns))),
            'tools': SubsetField('text', 'The A103 tools this commission may use', self.selectable_tools),
            'evidence_refs': Field('list', 'Records the commissioning parent received and hands on', required=False),
            'proposed_annotation_ref': Field('text', 'The proposed annotation (hypothesis) this task evaluates',
                                             required=False),
            'constraints': Field('record', "The commissioning parent's constraints", required=False),
        })

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        form = self.assignment_form
        supplied = {name for name, spec in form.fields.items() if not isinstance(spec, DeclaredField)}
        required = {name for name in supplied if form.fields[name].required}
        if not isinstance(entry_input, Mapping) or not required <= set(entry_input) <= supplied:
            raise ContractError('a103_head_entry_requires:' + ','.join(sorted(required)))
        assignment = {**{name: entry_input[name] for name in entry_input}, **form.declared}
        message = ContractRecord({'scope': dict(entry_input['scope'])})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=self.goal, result_contract=dict(REPORT), task_context={'evidence_axis': AXIS})
            return Commission(EpisodeRequest(goal, message), assignment)
        goal = EpisodeGoal.child(parent_goal, objective=self.goal, result_contract=dict(REPORT))
        return Commission(EpisodeRequest(goal, message, ReportContract(**REPORT)), assignment)

    def build_controller(self, bound, collaborators):
        """The head's continuation: the declared yield controller for its own measured-context credit."""
        from yield_control import (AccumulationYieldController, BoundedQualityYieldController,
                                   CompletionYieldController, YieldParameters)
        from .runtime_source import head_scope, initial_known
        if canonical(bound.assignment['evidence_task']) != canonical(self.evidence_task):
            raise ContractError('a103_head_evidence_task_differs')
        store = collaborators['store']
        scope = head_scope(store, bound.assignment['scope'])
        known = initial_known(bound.assignment)
        assignment = ({'scope': scope, 'proposed_annotation_ref': bound.assignment['proposed_annotation_ref']}
                      if 'proposed_annotation_ref' in bound.assignment else None)
        initial = self.credit_projector(store, scope, known_record_refs=known, assignment=assignment)['credit']
        declaration = self.continuation
        parameters = YieldParameters(**declaration['parameters'])
        if declaration['kind'] == 'bounded_quality':
            return BoundedQualityYieldController(bound.episode_id, initial, declaration['cutoff'],
                                                 self.credit_projector.native_score_maximum, parameters)
        if declaration['kind'] == 'completion':
            return CompletionYieldController(bound.episode_id, initial, declaration['cutoff'],
                                             self.credit_projector.as_record()['maximum_credit'], parameters)
        return AccumulationYieldController(bound.episode_id, initial, declaration['cutoff'], parameters)

    def build_episode(self, grain, bound, collaborators, child_builders):
        from .runtime_source import GeneContextEvidenceSource
        source = GeneContextEvidenceSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.result)

    def restore_controller_input(self, record):
        return ContractRecord(dict(record))


__all__ = ['AXIS', 'CONTINUATION_TASK', 'GeneContextEvidenceEpisode', 'CHILD_PATHS', 'ROLE']
