"""Explicit monitoring units for semantic progress facts actually received.

The caller supplies ordered received references and the original baseline.  The
public progress reader owns record, run and scope validation; this projection
does not discover receipts, observe targets or consult observation hashes.  It
is a callable component, not an installed role or continuation policy.
"""
from __future__ import annotations

from collections.abc import Mapping
import math

from .episode_bindings import BindingContext
from .progress_records import (JOB_STATUS_VERSION, RESOURCE_STATUS_VERSION,
    validate_job_status, validate_resource_status)


VERSION = 'received_progress_information_v1'
_LIFECYCLE = {'pending', 'executing', 'returned', 'admitted'}
_NATIVE_STATES = {'not_submitted', 'prepared', 'starting', 'running', 'returned'}
_NATIVE_OUTCOMES = {'pending', 'succeeded', 'failed'}


def _references(values):
    if isinstance(values, (str, bytes, Mapping)):
        raise TypeError('explicit_progress_reference_iterable_required')
    try:
        iterator = iter(values)
    except TypeError as error:
        raise TypeError('explicit_progress_reference_iterable_required') from error
    seen = set()
    for reference in iterator:
        if not isinstance(reference, str) or not reference:
            raise ValueError('nonempty_progress_reference_required')
        if reference not in seen:
            seen.add(reference)
            yield reference


def _facts(snapshot):
    """Return eligible facts; all identities are local to this exact target.

    Committed references have already been restricted to the parent-permitted
    types by the C8 publication boundary.  A source used only as provenance or a
    log representation is not a committed-record availability fact.
    """
    target = snapshot['target_handle']
    status = snapshot['execution_status']
    if not isinstance(target, str) or not target or status.get('handle') != target:
        raise ValueError('progress_credit_target_identity_mismatch')
    facts = set()
    lifecycle = status.get('lifecycle_state')
    if lifecycle in _LIFECYCLE:
        facts.add(('lifecycle_state', lifecycle))
    if type(snapshot.get('result_available')) is bool:
        facts.add(('result_available', snapshot['result_available']))

    version = status.get('version')
    if version in {'execution_status_v1', 'execution_status_v2'}:
        if status.get('liveness') in {'live', 'not_live'}:
            facts.add(('liveness', status['liveness']))
        failure = status.get('failure')
        if failure is not None:
            facts.add(('failure_code', failure['code']))
            facts.update(('failure_affected_ref', failure['code'], reference)
                         for reference in failure['affected_refs'])
    elif version == JOB_STATUS_VERSION:
        # Native jobs have neither C2 return IDs nor acknowledgments/liveness.
        native = validate_job_status(status)['native']
        if native['state'] in _NATIVE_STATES:
            facts.add(('native_state', native['state']))
        if native['outcome'] in _NATIVE_OUTCOMES:
            facts.add(('native_outcome', native['outcome']))
        if native['failure_code'] is not None:
            facts.add(('failure_code', native['failure_code']))
        for output in native['outputs']:
            facts.add(('native_output_available', output['role'], output['available']))
            facts.add(('native_output_writer_closed', output['role'], output['writer_closed']))
        elapsed = native['elapsed_seconds']
        if (native['state'] == 'returned' and native['outcome'] in {'succeeded', 'failed'}
                and type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0):
            facts.add(('completed_native_duration', native['duration_measure'], float(elapsed)))
    elif version == RESOURCE_STATUS_VERSION:
        native = validate_resource_status(status)['native']
        if native['state'] != 'unknown':
            facts.add(('native_state', native['state']))
        if native['returncode'] is not None:
            facts.add(('native_returncode', native['returncode']))
        if native['failure_code'] is not None:
            facts.add(('failure_code', native['failure_code']))
        for output in native['outputs']:
            facts.add(('native_output_available', output['role'], output['available']))
            facts.add(('native_output_writer_closed', output['role'], output['writer_closed']))
        # These are measured, closed intervals. Queue wait can finish while
        # execution continues; unfinished elapsed values remain only native.
        for measurement in native['measurements']:
            facts.add(('completed_native_duration', measurement['measure'],
                       float(measurement['seconds'])))
    else:
        raise ValueError('unsupported_progress_credit_status_version')

    facts.update(('dependency', row['kind'], row['handle'], row['relation_ref'])
                 for row in snapshot['dependencies'])
    facts.update(('committed_record_available', reference)
                 for reference in snapshot['committed_record_refs'])
    return target, facts


class ProgressInformationCredit:
    """One caller-scaled unit per newly informative received snapshot.

    Seed semantic facts from initial refs, then process known refs in their
    supplied order.  Several novel facts in one snapshot still earn one unit.
    Presentation changes, repeated delivery and unfinished elapsed time earn
    nothing.  This object writes no state and supplies no action observations.
    """

    def __init__(self, progress_provider, *, information_unit):
        try:
            valid = (type(information_unit) in (int, float)
                     and math.isfinite(information_unit) and information_unit > 0)
            unit = float(information_unit) if valid else None
        except (OverflowError, ValueError):
            unit = None
        if unit is None:
            raise ValueError('explicit_positive_monitoring_information_unit_required')
        if not callable(getattr(progress_provider, 'read_progress', None)):
            raise TypeError('public_progress_reader_required')
        self.progress_provider = progress_provider
        self.information_unit = unit

    def as_record(self):
        return {'version': VERSION, 'information_unit': self.information_unit,
            'formula': 'information_unit * newly_informative_received_snapshot_count',
            'baseline': 'semantic_facts_in_original_initial_progress_refs_per_target',
            'order': 'known_progress_refs_in_supplied_receipt_order',
            'contribution': 'one_unit_per_snapshot_with_at_least_one_novel_eligible_fact',
            'eligible_information': ['known_lifecycle_and_liveness', 'result_availability',
                'recorded_failure_code_and_affected_refs', 'exposed_dependency_identity_and_relation',
                'parent_permitted_committed_record_availability', 'known_native_state_and_outcome',
                'native_output_availability_and_writer_closure',
                'finite_terminal_native_duration_by_target_and_measure',
                'known_resource_execution_state_and_returncode',
                'finite_closed_resource_interval_by_target_and_measure'],
            'excluded_information': ['unfinished_elapsed_time', 'output_byte_growth',
                'timestamps', 'source_representation_ids', 'raw_log_hashes', 'private_history'],
            'interpretation': 'monitoring_information_not_scientific_progress_or_annotation_support',
            'installation': 'explicit_caller_binding_required'}

    def __call__(self, context: BindingContext, receiver_selection):
        if not isinstance(context, BindingContext):
            raise TypeError('progress_credit_binding_context_required')
        if not isinstance(receiver_selection, Mapping):
            raise TypeError('progress_credit_receiver_selection_required')
        if (receiver_selection.get('run_id') != context.run_id
                or receiver_selection.get('episode_id') != context.episode_id):
            raise ValueError('progress_credit_receiver_identity_mismatch')

        seen_by_target, read = {}, {}

        def selected(reference):
            if reference not in read:
                snapshot = self.progress_provider.read_progress(reference, context.scope)
                if (not isinstance(snapshot, Mapping)
                        or snapshot.get('version') != 'progress_snapshot_v1'
                        or snapshot.get('progress_ref') != reference):
                    raise ValueError('progress_credit_reference_identity_mismatch')
                read[reference] = _facts(snapshot)
            return read[reference]

        initial = list(_references(receiver_selection['initial_progress_refs']))
        for reference in initial:
            target, facts = selected(reference)
            seen_by_target.setdefault(target, set()).update(facts)
        known, contributions = [], []
        for reference in _references(receiver_selection['known_progress_refs']):
            known.append(reference)
            target, facts = selected(reference)
            seen = seen_by_target.setdefault(target, set())
            novel = facts - seen
            if novel:
                contributions.append({'progress_ref': reference, 'target_handle': target,
                    'new_fact_count': len(novel)})
            seen.update(facts)
        credit = self.information_unit * len(contributions)
        if not math.isfinite(credit):
            raise ValueError('finite_monitoring_information_credit_required')
        return {'credit': credit, 'monitoring_information_credit': credit,
            'monitoring_information_binding': self.as_record(),
            'newly_informative_received_snapshot_count': len(contributions),
            'monitoring_information_contributions': contributions,
            'known_progress_refs': known, 'initial_progress_refs': initial}


__all__ = ['ProgressInformationCredit', 'VERSION']
