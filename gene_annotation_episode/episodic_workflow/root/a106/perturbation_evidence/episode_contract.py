"""A106 episode bindings under the generic ``episode_runtime`` contract.

Every binding in the ``perturbation_evidence`` subtree mixes in one of the
contracts below and so implements each hook of
docs/axis_restructure_20261117/BINDING_CONTRACT.md. ``home`` is the home factory
that constructs all 15 bindings.

- ``HeadContract`` (``perturbation_evidence``): runs its own model-selected
  decisions (``runtime_source.PerturbationEvidenceSource``) over the standard
  ``store`` and ``model_provider`` collaborators and its own tool registry, and
  its controller is the head's declared yield controller over its A106
  finding-progress credit for the commissioned proposed annotation.
- the seven literature bindings derive from
  ``published_evidence_assessment.literature_binding.LiteratureBinding`` (an
  ``EpisodeContract``): their own model-selected decisions
  (``literature_source.LiteratureSource``) and the commissioned literature
  task's declared continuation.
- the monitor (``execution_progress_assessment/episode.MonitorEpisode``) mixes the
  A106 monitor runtime (``episode_support/jobs/service_calls/perturbation_evidence/monitor_runtime.py``) into ``EpisodeContract``:
  model-selected progress units, received-information credit and its own
  information-accumulation continuation.
- the two launch bindings (``execution_job_submission.submission_source.JobSubmissionContract``):
  model-selected API launch children and completion toward their handoffs.
- the two API job bindings (``execution_job_submission/api_job_execution/binding.ApiJobBinding``):
  model-selected BV-BRC AppService operations and completion toward one usable handoff.
- the two results bindings (``execution_result_acquisition.acquisition_source.ResultAcquisitionBinding``):
  model-selected AppService result operations and completion toward the assigned handoffs.

No stand-in decision source or controller runs anywhere. Credits are never
bounded, clamped or rescaled.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import math
from types import MappingProxyType

from episode_runtime import ChoiceField, Commission, DeclaredField, Field, RecordForm, SubsetField, grain_name_for
from method_loop import ClosedRecord, EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import ContractError

STORE, MODEL_PROVIDER = 'store', 'model_provider'

H = 'perturbation_evidence'
L = H + '/published_evidence_assessment'
S = L + '/evidence_search_strategy_improvement'
R = S + '/source_relevance_assessment'
P = R + '/source_evidence_examination'
# Declared child slots of every binding in the subtree: slot -> child binding_path.
CHILD_SLOTS = MappingProxyType({
    H: {'perturbation_evidence': H, 'literature': L, 'launch': H + '/execution_job_submission',
        'monitor': H + '/execution_progress_assessment', 'results': H + '/execution_result_acquisition'},
    H + '/execution_job_submission': {'launch_api': H + '/execution_job_submission/api_job_execution'},
    H + '/execution_job_submission/api_job_execution': {},
    H + '/execution_progress_assessment': {},
    H + '/execution_result_acquisition': {},
    L: {'literature_strategy': S, 'launch': L + '/execution_job_submission', 'results': L + '/execution_result_acquisition'},
    S: {'literature_search': R},
    R: {'literature_page': P},
    P: {'literature_table': P + '/table_evidence_extraction', 'literature_ordered': P + '/source_coverage_improvement',
        'literature_targeted': P + '/passage_evidence_extraction'},
    P + '/table_evidence_extraction': {},
    P + '/source_coverage_improvement': {},
    P + '/passage_evidence_extraction': {},
    L + '/execution_job_submission': {'launch_api': L + '/execution_job_submission/api_job_execution'},
    L + '/execution_job_submission/api_job_execution': {},
    L + '/execution_result_acquisition': {},
})

SCOPE = Field('record', 'The subject whose function this episode investigates, as its commissioner holds it')
REPORT_CONTRACT = {
    'decision': 'Admit the A106 perturbation findings into the commissioning episode',
    'measurements': {'credit': "This commission's credit on the binding's own unbounded scale"},
    'information': {'finding': 'The retained A106 perturbation findings of this commission'},
}
RETURN_FORM = RecordForm({
    'credit': Field('number', "This commission's credit on the binding's own unbounded scale"),
    'finding': Field('record', 'The retained A106 perturbation findings of this commission'),
})


@dataclass(frozen=True)
class ContractRecord(ClosedRecord):
    """A closed A106 record (request message, controller input or result)."""
    value: Mapping

    def as_record(self):
        return deepcopy(dict(self.value))


def _unit(value, code):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ContractError(code)
    return float(value)


class EpisodeContract:
    """The episode_runtime hooks shared by every A106 binding.

    A binding declares ``goal``, ``unit``, ``result``, ``assignment_form`` and
    ``contract_credit_unit(assignment)``.
    """
    required_collaborators = ()
    return_form = RETURN_FORM
    report_contract = MappingProxyType(REPORT_CONTRACT)

    @property
    def grain_name(self):
        return grain_name_for(self.binding_path)

    @property
    def child_slots(self):
        return MappingProxyType(dict(CHILD_SLOTS[self.binding_path]))

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        if not isinstance(entry_input, Mapping):
            raise ContractError('a106_entry_input_mapping_required')
        expected = {'objective', 'assignment'} | ({'report_contract'} if parent_goal is not None else set())
        if set(entry_input) != expected:
            raise ContractError('a106_entry_input_fields_required:' + ','.join(sorted(expected)))
        assignment = self.assignment_form.admit(entry_input['assignment'], 'a106_entry_assignment')
        self.contract_credit_unit(assignment)
        message = ContractRecord({'assignment': deepcopy(assignment)})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=entry_input['objective'], result_contract=REPORT_CONTRACT)
            return Commission(EpisodeRequest(goal, message), assignment)
        contract = ReportContract.from_record(entry_input['report_contract'])
        goal = EpisodeGoal.child(parent_goal, objective=entry_input['objective'], result_contract=contract.as_record())
        return Commission(EpisodeRequest(goal, message, contract), assignment)

    def restore_controller_input(self, record):
        if not isinstance(record, Mapping) or 'credit' not in record:
            raise ContractError('a106_recorded_controller_input_requires_credit')
        return ContractRecord(dict(record))


class HeadContract(EpisodeContract):
    """The A106 axis head: its own decision source and its declared finding-progress continuation."""
    required_collaborators = (STORE, MODEL_PROVIDER)

    def build_controller(self, bound, collaborators):
        """The head's declared yield controller, opened at the credit this episode holds when it opens.

        When it opens the head holds its initial references: the commissioner's
        evidence references and the commissioned proposed annotation.
        """
        from .runtime_source import head_credit, initial_references, store_scope
        store = collaborators[STORE]
        scope = store_scope(store, bound.assignment['scope'])
        initial = initial_references(store, scope, bound.assignment)
        known = [ref for ref in initial if store.get(ref).get('record_type') == 'assessment']
        initial_credit = head_credit(store, scope, bound.assignment['evidence_task'],
                                     bound.assignment['proposed_annotation_ref'], known)['credit']
        return self.head_continuation(bound.assignment['evidence_task'], initial_credit, bound.episode_id)

    def build_episode(self, grain, bound, collaborators, child_builders):
        """The head's own model-selected units (``runtime_source``) over ``bound`` and its collaborators."""
        from method_loop import Episode
        from .runtime_source import PerturbationEvidenceSource
        source = PerturbationEvidenceSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.result)


def head_form(credit_unit, thought_patterns, tools):
    """The head's assignment, as the original A106 commission.

    The commissioner fills ``scope``, the proposed annotation the commission
    evaluates, its evidence references and constraints, and chooses the A106
    process: one library thought pattern and a subset of the head's tools. The
    A106 whole-axis finding task is the head's own declaration.
    """
    task = {'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings', 'evidence_axis': 'A106',
            'credit_unit': _unit(credit_unit, 'a106_evidence_task_credit_unit_required')}
    return RecordForm({
        'scope': SCOPE,
        'evidence_task': DeclaredField('record', 'The A106 whole-axis finding task this head declares: one '
                                                 'credit_unit per distinct retained finding', task),
        'proposed_annotation_ref': Field('text', 'The proposed annotation (hypothesis record) this commission '
                                                 'evaluates'),
        'evidence_refs': Field('list', 'Records the commissioner holds that this commission receives as evidence'),
        'constraints': Field('record', 'The constraints of this investigation'),
        'thought_pattern': ChoiceField('text', 'The library thought pattern this A106 commission investigates with',
                                       tuple(thought_patterns)),
        'tools': SubsetField('text', 'The A106 tools (<name>@<resources>) this commission may use', tuple(tools)),
    })


OPERATIONAL_FORM = RecordForm({
    'scope': SCOPE,
    'assignment': Field('record', 'The commissioned launch, monitor or results assignment of this operational child'),
})


def scientific_credit_unit(assignment):
    """Head credit unit: the A106 whole-axis finding task's ``credit_unit``."""
    from .credit import original_task_projector
    return original_task_projector({'context': {'evidence_task': assignment['evidence_task']}}).policy.finding_unit


# The two API job-execution bindings (role launch_api): each is constructed with its own ToolRegistry.
API_JOB_PATHS = (H + '/execution_job_submission/api_job_execution', L + '/execution_job_submission/api_job_execution')


def home(services):
    """The A106 home factory: construct all 15 bindings of the perturbation_evidence subtree.

    ``services['store']`` is the run's one shared ``gene_annotation_episode.state.Store``.
    ``services['perturbation_evidence']`` maps every binding path to that binding's explicit constructor
    configuration; a path without one raises. The head's, the monitor's, each API job binding's (``API_JOB_PATHS``) and
    each literature binding's ``tools`` entry holds the settings of its own A106 ``ToolRegistry``, built here over the
    shared store (an API job binding's AppService services use it). The seven literature bindings are
    bound to their literature children, and the head to its literature binding.
    """
    from importlib import import_module
    from gene_annotation_episode.episodic_workflow.episode_support.tools.perturbation_evidence.tools import ToolRegistry
    from .published_evidence_assessment.literature_binding import LiteratureBinding, ROLE_PATHS
    try:
        store, configuration = services['store'], services['perturbation_evidence']
    except KeyError as error:
        raise ContractError('a106_home_factory_requires_service:' + str(error.args[0])) from error
    if not isinstance(configuration, Mapping) or set(configuration) != set(CHILD_SLOTS):
        raise ContractError('a106_home_configuration_for_every_binding_required')
    bindings = {}
    for path in CHILD_SLOTS:
        module = import_module(__package__.rsplit('.', 1)[0] + '.' + path.replace('/', '.') + '.episode')
        found = [value for value in vars(module).values() if isinstance(value, type)
                 and value.__module__ == module.__name__ and getattr(value, 'binding_path', None) == path]
        if len(found) != 1:
            raise ContractError('a106_home_binding_class_not_unique:' + path)
        settings = dict(configuration[path])
        literature = issubclass(found[0], LiteratureBinding)
        if path in (H, H + '/execution_progress_assessment') + API_JOB_PATHS or literature:
            if 'tools' not in settings:
                raise ContractError('a106_home_tool_registry_settings_required:' + path)
            settings['tool_registry'] = ToolRegistry(store, **dict(settings.pop('tools')))
        bindings[path] = found[0](**settings) if literature else found[0](services, **settings)
    by_role = {role: bindings[path] for role, path in ROLE_PATHS.items()}
    for role, path in ROLE_PATHS.items():
        bindings[path].bind_children({child: by_role[child] for child in bindings[path].child_role_names})
    bindings[H].bind_literature(bindings[L])
    return tuple(bindings.values())


def a106_progress_provider(store, *, run_id):
    """The progress monitors' ``a106_progress_provider`` runtime collaborator for one run.

    A106's ``ProgressProvider`` over the run's shared Store, watching A106's own jobs: its job provider
    (``episode_support/jobs/service_calls/perturbation_evidence/job_provider.JobProvider``) reads the AppService tasks this subtree's API job execution
    bindings recorded in that Store under ``run_id`` (every target raises: its receipts hold no scope).
    """
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.perturbation_evidence.job_provider import JobProvider
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.perturbation_evidence.progress_provider import ProgressProvider
    return ProgressProvider(store, run_id=run_id, job_provider=JobProvider(store, run_id=run_id))


__all__ = ['CHILD_SLOTS', 'ContractRecord', 'EpisodeContract', 'HeadContract',
           'MODEL_PROVIDER', 'OPERATIONAL_FORM', 'REPORT_CONTRACT',
           'RETURN_FORM', 'STORE', 'a106_progress_provider', 'head_form', 'home', 'scientific_credit_unit']
