"""Explicit starting bindings for a model-driven single-gene investigation.

Investigation progress and numerical continuation reuse their existing implementations.
Annotation scoring is unbound while the numerical component sheets are unfinished.
Operational credit measures recorded handoff verification and acquired data,
never tool calls or scientific truth. Parameters are caller-owned and saved by
the case harness. This module executes no jobs and makes no episode decisions.
"""
from dataclasses import dataclass
import hashlib
import math

from gene_annotation_episode.case_execution import PolicyBindings
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.monitoring_credit import MonitoringInformationCredit
from gene_annotation_episode.native_timing_information import NativeTimingInformation
from gene_annotation_episode.numerical import YieldController, YieldParameters, provenance
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
    sections = {'scientific_child', 'scientific_progress', 'operational', 'monitoring', 'controller'}
    if 'scientific' in parameters:
        raise ValueError('categorical_annotation_policy_retired_supply_explicit_numeric_scorer')
    if set(parameters) != sections:
        raise ValueError('explicit_investigation_policy_sections_required')
    if parameters['scientific_child'] != 'received_findings':
        raise ValueError('scientific_continuation_requires_received_findings')
    progress = parameters['scientific_progress']
    if not isinstance(progress, dict) or set(progress) != {
            'finding_unit', 'initial_known_record_refs', 'loss_preview_size'}:
        raise ValueError('explicit_scientific_progress_configuration_required')
    scientific = child = ScientificFindingProgress(
        FindingProgressPolicy(progress['finding_unit']), progress['loss_preview_size'])
    initial_known = progress['initial_known_record_refs']
    operational = JobEvidenceCredit(**parameters['operational'])
    monitoring = MonitoringInformationCredit(**parameters['monitoring'])
    control = dict(parameters['controller'])
    cost = control.pop('cost')
    supplied_role_costs = control.pop('cost_by_role', {})
    if (not isinstance(supplied_role_costs, dict)
            or not set(supplied_role_costs) <= set(Workflow.grain_names + ROLES + episode_roles)):
        raise ValueError('controller_cost_by_role_requires_known_episode_roles')
    # The caller owns thresholds. Freeze them independently of mutable input
    # dictionaries and of the definition exposed to reporting/persistence.
    role_costs = tuple(sorted(supplied_role_costs.items()))
    settings = YieldParameters(**control)
    # Constructor validation is also used for the configured cost. It does not
    # observe an action or supply a second continuation rule.
    YieldController('configuration', 0, cost, settings)
    for _, role_cost in role_costs:
        YieldController('configuration', 0, role_cost, settings)

    def controller(path, initial_credit):
        epoch = hashlib.sha256(canonical(path).encode()).hexdigest()
        selected_cost = dict(role_costs).get(path[-1][0], cost)
        return YieldController(epoch, initial_credit, selected_cost, settings)

    controller_definition = {
        'version': 'existing_yield_controller_explicit_parameters_v1',
        'cost': cost, 'parameters': settings.as_record(), 'estimator': provenance(),
        'continuation': 'available_next_gain_upper_bound_lte_cost',
        'time_resource_estimation': 'separate_information_for_episode_decisions'}
    if role_costs:
        controller_definition.update(
            version='existing_yield_controller_explicit_role_costs_v2',
            cost_by_role=dict(role_costs),
            cost_selection='exact_episode_role_override_otherwise_caller_cost')

    return PolicyBindings(scientific, child, operational, monitoring, controller,
        scientific.as_record(), child.as_record(), operational.as_record(), monitoring.as_record(),
        controller_definition,
        project_annotation_score=None,
        annotation_score_definition=None,
        initial_known_record_refs=initial_known if initial_known is not None else [],
        native_timing_information=NativeTimingInformation(monitoring.information_unit))
