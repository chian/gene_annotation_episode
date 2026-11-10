"""Explicit task-credit and continuation bindings for an investigation.

Scientific owners select credit for their own tasks. A configured finding
calculation is available to owners that explicitly choose it; it is never an
automatic child policy. The optional annotation root receives each
annotation/axis child's earned credit.
Operational credit measures recorded handoff verification and acquired data,
never tool calls or scientific truth. Parameters are caller-owned and saved by
the case harness. This module executes no jobs and makes no episode decisions.
"""
from dataclasses import dataclass, replace
import hashlib
import json
import math

from gene_annotation_episode.case_execution import PolicyBindings
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.monitoring_credit import MonitoringInformationCredit
from gene_annotation_episode.native_timing_information import NativeTimingInformation
from gene_annotation_episode.numerical import (YieldController, AnnotationAxisYieldController,
    YieldParameters, provenance)
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.homology_episodes import ROLES
from gene_annotation_episode.runtime import Workflow


@dataclass(frozen=True)
class JobEvidenceCredit:
    registry_ref: str
    handoff_unit: float
    acquired_record_unit: float

    def __post_init__(self):
        if not isinstance(self.registry_ref, str) or not self.registry_ref:
            raise ValueError('explicit_execution_registry_required')
        for value in (self.handoff_unit, self.acquired_record_unit):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError('explicit_positive_operational_credit_units_required')

    def as_record(self):
        return {'version': 'recorded_job_evidence_credit_v1',
            'registry_ref': self.registry_ref,
            'handoff_unit': self.handoff_unit,
            'acquired_record_unit': self.acquired_record_unit,
            'launch_contribution': 'selected_successful_functional_handoff_verification_once_per_job',
            'results_contribution': 'distinct_canonical_records_with_native_row_witnesses_for_assigned_job',
            'baseline': 'already_recorded_contributions_for_this_physical_job',
            'scope': 'assigned_query_and_physical_job_in_caller_registry',
            'scientific_credit': False,
            'closure_validation': 'does_not_create_an_extra_selected_work_contribution'}

    def __call__(self, store, *, role, assignment, episode_id, run_id):
        # Project durable facts, including inherited facts at episode entry.
        # No live polling, parser work, history hydration or state writes occur.
        if role == 'job_launch':
            exists = store.db.execute('''SELECT 1 FROM runtime_actions
                WHERE json_extract(action,'$.tool')='homology.check_handoff'
                AND json_extract(result,'$.status')='completed'
                AND json_extract(result,'$.result.handoff.job_ref')=?
                AND json_extract(result,'$.result.handoff.registry_ref')=?
                AND json_type(result,'$.result.receipt_ref')='text' LIMIT 1''',
                (assignment['job_ref'], self.registry_ref)).fetchone()
            return self.handoff_unit if exists is not None else 0.
        if role != 'job_results':
            raise ValueError('operational_credit_requires_launch_or_results_role')
        tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('homology_result_snapshots','homology_result_witnesses')")}
        if len(tables) != 2:
            return 0.
        count = store.db.execute('''SELECT count(DISTINCT witness.record_ref)
            FROM homology_result_witnesses witness
            JOIN homology_result_snapshots snapshot ON snapshot.source_ref=witness.snapshot_ref
            WHERE snapshot.query_ref=? AND json_extract(snapshot.body,'$.execution_context.job_ref')=?
            AND json_extract(snapshot.body,'$.execution_context.registry_ref')=?''',
            (assignment['query_ref'], assignment['job_ref'], self.registry_ref)).fetchone()[0]
        return self.acquired_record_unit * count


def create_policy(parameters, *, episode_roles: tuple[str, ...] = ()):
    """Case policy factory; all effective starting settings are explicit inputs."""
    if (not isinstance(episode_roles, tuple)
            or any(not isinstance(role, str) or not role for role in episode_roles)
            or len(set(episode_roles)) != len(episode_roles)):
        raise ValueError('explicit_unique_episode_roles_required')
    sections = {'scientific_progress', 'operational', 'monitoring', 'controller'}
    if 'scientific' in parameters:
        raise ValueError('categorical_annotation_policy_retired_supply_explicit_numeric_scorer')
    if 'scientific_child' in parameters:
        raise ValueError('role_wide_scientific_child_credit_policy_retired')
    if not sections <= set(parameters) <= sections | {'annotation_support', 'root_task'}:
        raise ValueError('explicit_investigation_policy_sections_required')
    progress = parameters['scientific_progress']
    if not isinstance(progress, dict) or set(progress) != {
            'finding_unit', 'initial_known_record_refs', 'loss_preview_size'}:
        raise ValueError('explicit_scientific_progress_configuration_required')
    scientific = ScientificFindingProgress(
        FindingProgressPolicy(progress['finding_unit']), progress['loss_preview_size'])
    initial_known = progress['initial_known_record_refs']
    operational = JobEvidenceCredit(**parameters['operational'])
    monitoring = MonitoringInformationCredit(**parameters['monitoring'])
    control = dict(parameters['controller'])
    cost = control.pop('cost')
    supplied_role_costs = control.pop('cost_by_role', {})
    supplied_task_costs = control.pop('cost_by_task', {})
    supplied_scientific_yield = control.pop('yield_cutoff_by_task', {})
    if (not isinstance(supplied_role_costs, dict)
            or not set(supplied_role_costs) <= set(Workflow.grain_names + ROLES + episode_roles)):
        raise ValueError('controller_cost_by_role_requires_known_episode_roles')
    # The caller owns thresholds. Freeze them independently of mutable input
    # dictionaries and of the definition exposed to reporting/persistence.
    role_costs = tuple(sorted(supplied_role_costs.items()))
    job_roles = {'job_launch', 'job_monitor', 'job_results', 'launch', 'monitor',
        'results', 'hpc', 'hpc_prediction', 'hpc_execution'}
    def valid_task_cutoffs(values, *, allowed):
        return (isinstance(values, dict)
            and all(isinstance(key, str) and ':' in key and key.split(':', 1)[1]
                and (key.split(':', 1)[0] in allowed if allowed is not None
                     else key.split(':', 1)[0] in {'A101', 'A102', 'A103', 'A104',
                         'A105', 'A106', 'A107', 'A108', 'A110'})
                for key in values))
    if not valid_task_cutoffs(supplied_task_costs, allowed=job_roles):
        raise ValueError('cost_by_task_requires_long_running_job_task')
    if not valid_task_cutoffs(supplied_scientific_yield, allowed=None):
        raise ValueError('scientific_yield_cutoff_requires_axis_task_and_credit_definition')
    for supplied in (supplied_task_costs, supplied_scientific_yield):
        for value in supplied.values():
            if (not isinstance(value, dict) or set(value) != {'cutoff', 'credit_definition'}
                    or not isinstance(value['credit_definition'], dict)
                    or not value['credit_definition']):
                raise ValueError('explicit_yield_cutoff_and_credit_definition_required')
    # An optional task-specific yield threshold is tied to the original units.
    task_costs = json.loads(canonical(supplied_task_costs))
    scientific_yield = json.loads(canonical(supplied_scientific_yield))
    root_task = parameters.get('root_task')
    axis_cutoffs = None
    if root_task is not None:
        if (not isinstance(root_task, dict) or set(root_task) != {'kind', 'cutoffs'}
                or root_task['kind'] != 'annotation_axis_credit'
                or not isinstance(root_task['cutoffs'], dict)
                or set(root_task['cutoffs']) != {'A101', 'A102', 'A103', 'A104', 'A105',
                    'A106', 'A107', 'A108', 'A110'}):
            raise ValueError('explicit_annotation_axis_root_task_and_cutoffs_required')
        axis_cutoffs = dict(root_task['cutoffs'])
    settings = YieldParameters(**control)
    # Constructor validation is also used for the configured cost. It does not
    # observe an action or supply a second continuation rule.
    YieldController('configuration', 0, cost, settings)
    for _, role_cost in role_costs:
        YieldController('configuration', 0, role_cost, settings)
    for configured in (*task_costs.values(), *scientific_yield.values()):
        YieldController('configuration', 0, configured['cutoff'], settings)
    if axis_cutoffs is not None:
        AnnotationAxisYieldController('configuration',
            {'mode': 'annotation_axis_credit', 'arms': []}, axis_cutoffs, settings)

    def controller(path, initial_credit, *, context=None, task_key=None,
                   credit_definition=None):
        epoch = hashlib.sha256(canonical(path).encode()).hexdigest()
        if len(path) == 1 and axis_cutoffs is not None:
            return AnnotationAxisYieldController(epoch, initial_credit, axis_cutoffs, settings)
        scientific_child = len(path) > 1 and (path[-1][0] in {'scientific_process', 'improvement'}
            or path[-1][0].startswith('literature'))
        if scientific_child:
            if (context is None or tuple(context.path) != tuple(path)
                    or not isinstance(task_key, str) or not task_key
                    or not isinstance(credit_definition, dict) or not credit_definition):
                raise ValueError('scientific_child_yield_requires_original_task_credit')
            configured = scientific_yield.get(task_key)
            if configured is not None and credit_definition != configured['credit_definition']:
                raise ValueError('episode_yield_cutoff_credit_definition_mismatch:' + task_key)
            selected_cost = (configured['cutoff'] if configured is not None
                else dict(role_costs).get(path[-1][0], cost))
        elif task_key is not None:
            role = path[-1][0]
            if (role not in job_roles or not task_key.startswith(role + ':')
                    or context is None or tuple(context.path) != tuple(path)):
                raise ValueError('cost_by_task_requires_long_running_job_task')
            if task_key not in task_costs:
                raise ValueError('job_task_cost_not_declared:' + task_key)
            configured = task_costs[task_key]
            if credit_definition != configured['credit_definition']:
                raise ValueError('job_task_cost_credit_definition_mismatch:' + task_key)
            selected_cost = configured['cutoff']
        elif len(path) == 1 and path[-1][0] == 'annotation':
            selected_cost = cost
        else:
            configured = dict(role_costs)
            selected_cost = configured.get(path[-1][0], cost)
        return YieldController(epoch, initial_credit, selected_cost, settings)

    # Historical factories retain their original two-argument interface. This
    # factory declares its task input before construction; no controller wrapper
    # changes a cutoff or credit calculation afterwards.
    controller.requires_original_task = True

    controller_definition = {
        'version': 'existing_yield_controller_explicit_parameters_v1',
        'cost': cost, 'parameters': settings.as_record(), 'estimator': provenance(),
        'continuation': 'available_next_gain_upper_bound_lte_cost',
        'time_resource_estimation': 'separate_information_for_episode_decisions'}
    if role_costs:
        controller_definition.update(
            version='existing_yield_controller_explicit_role_costs_v3',
            cost_by_role=dict(role_costs),
            cost_selection='episode_role_yield_override_or_base_yield_cutoff')
    controller_definition.update(
        version='existing_yield_controller_original_task_yield_v5',
        cost_by_task=json.loads(canonical(task_costs)),
        yield_cutoff_by_task=json.loads(canonical(scientific_yield)),
        scientific_yield_selection='original_task_override_or_role_or_base_yield_cutoff',
        job_cost_selection='cost_by_task_only_for_long_running_job_roles')
    if axis_cutoffs is not None:
        controller_definition['root_task'] = {
            'kind': 'annotation_axis_credit', 'cutoffs': dict(axis_cutoffs),
            'unit': 'earned_credit_from_received_axis_child_in_its_declared_local_units',
            'root_score': 'max_per_annotation_sum_of_received_axis_child_credit',
            'forecast': 'another_whole_axis_invocation',
            'continuation': 'every_annotation_axis_available_upper_bound_lte_own_cutoff'}

    annotation = None
    if 'annotation_support' in parameters:
        from .root_axis_scalars import VERSION as ROOT_SCALAR_VERSION
        from .signed_evidence_root import SignedEvidenceRootSupport
        support = parameters['annotation_support']
        if (not isinstance(support, dict)
                or not {'version'} <= set(support) <= {
                    'version', 'assertion_ref', 'comparison_ref', 'selections'}
                or support['version'] != ROOT_SCALAR_VERSION
                or not isinstance(support.get('selections', {}), dict)):
            raise ValueError('explicit_signed_root_annotation_support_required')
        annotation = SignedEvidenceRootSupport(support.get('assertion_ref'), support.get('comparison_ref'),
            tuple(support.get('selections', {}).items()))
    if root_task is not None:
        if annotation is None or annotation.provides_single_annotation_score:
            raise ValueError('annotation_axis_root_requires_collection_scorer')
        scientific = replace(annotation, task_credit=True)

    return PolicyBindings(scientific, None, operational, monitoring, controller,
        scientific.as_record(), None, operational.as_record(), monitoring.as_record(),
        controller_definition,
        project_annotation_score=annotation,
        annotation_score_definition=annotation.as_record() if annotation is not None else None,
        episode_record_receipts=annotation is not None,
        initial_known_record_refs=initial_known if initial_known is not None else [],
        native_timing_information=NativeTimingInformation(monitoring.information_unit))
