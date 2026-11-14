"""Local monitoring information, independent of science and execution forecasts.

Only this child's selected execution observations, original parent-supplied facts and frozen
per-action forecasts are read. No live job poll, global history read, scientific
state or another child's private history participates in the projection.
"""
from copy import deepcopy
import json
import math

from .homology_jobs import SAMPLE_SCHEMA, STATUS_SCHEMA
from .resource_estimation import ESTIMATE_SCHEMA


VERSION = 'job_monitoring_information_v2'
OUTPUT_ROLES = ['native_text', 'native_stderr', 'hit_table', 'domain_table']


def _object(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


FINDING_SCHEMA = _object({
    'sample': deepcopy(SAMPLE_SCHEMA),
    'new_state': {'type': 'boolean'},
    'new_outcome': {'type': 'boolean'},
    'new_completed_timing': {'type': 'boolean'},
    'new_output_states': {'type': 'array', 'uniqueItems': True, 'items': _object({
        'role': {'type': 'string', 'enum': OUTPUT_ROLES},
        'available': {'type': 'boolean'}, 'writer_closed': {'type': 'boolean'}})},
    'new_timing_overruns': {'type': 'array', 'items': deepcopy(ESTIMATE_SCHEMA)},
})


# A check remains a check. Nullable sample fields do not manufacture a poll
# identity, and the original checked timestamp remains its receiving identity.
EXECUTION_OBSERVATION_SCHEMA = _object({
    'observation_kind': {'type': 'string', 'enum': ['monitor_sample', 'handoff_check']},
    'sample_ref': {'type': ['string', 'null'], 'format': 'reference',
                   'x-reference-namespace': 'job_sample'},
    'sampled_at_unix_seconds': {'type': ['number', 'null'], 'minimum': 0},
    'checked_at_unix_seconds': {'type': ['number', 'null'], 'minimum': 0},
    **deepcopy(STATUS_SCHEMA['properties']),
})
CHECK_AWARE_FINDING_SCHEMA = deepcopy(FINDING_SCHEMA)
CHECK_AWARE_FINDING_SCHEMA['properties']['sample'] = EXECUTION_OBSERVATION_SCHEMA


def _output(output):
    return output['role'], output['available'], output['writer_closed']


def _completed_timing(sample):
    """The total measured duration of an execution with an observed outcome."""
    elapsed = sample.get('elapsed_seconds')
    if (sample.get('outcome') not in {'succeeded', 'failed'}
            or type(elapsed) not in (int, float)
            or not math.isfinite(elapsed) or elapsed < 0):
        return None
    return sample['job_ref'], sample['duration_measure'], float(elapsed)


def _overrun(estimate):
    # Forecast IDs include sample identity. Credit identity instead describes
    # the actual benchmark: resampling a crossing never creates another fact.
    return (estimate['phase'], estimate['cpu_threads'], estimate['forecast_duration_measure'],
            estimate['observed_max_seconds'])


class MonitoringInformationCredit:
    """One explicit caller-scaled unit per newly informative observation.

    Multiple changes in the same observation constitute one information contribution,
    with every contributing fact retained in its typed finding. Byte growth,
    time passing, repeated IDs and unchanged polls are not contributions. This
    is an execution-information score, never annotation progress or gain/time.
    """
    def __init__(self, *, information_unit, include_handoff_checks=False):
        if type(information_unit) not in (int, float) or not math.isfinite(information_unit) or information_unit <= 0:
            raise ValueError('explicit_positive_monitoring_information_unit_required')
        self.information_unit = float(information_unit)
        if type(include_handoff_checks) is not bool:
            raise ValueError('explicit_boolean_handoff_information_setting_required')
        # Historical runs retain the exact sample-only projection/definition.
        # New callers explicitly select check-aware information accounting.
        self.include_handoff_checks = include_handoff_checks

    @property
    def information_roles(self):
        return (('job_launch', 'job_monitor', 'job_results') if self.include_handoff_checks
                else ('job_monitor',))

    def as_record(self):
        record = {'version': VERSION, 'information_unit': self.information_unit,
            'contribution': 'new_sample_information_not_poll_count',
            'timing_information': 'new_completed_duration_or_first_crossing_of_frozen_successful_duration_maximum'}
        if self.include_handoff_checks:
            record.update(version='selected_execution_information_v3', include_handoff_checks=True,
                contribution='new_selected_execution_information_not_poll_or_check_count',
                information_roles=list(self.information_roles),
                controller_effect='separate_from_caller_selected_operational_or_scientific_score')
        return record

    @staticmethod
    def report_source():
        return {'type': 'array', 'meaning': ('New execution information from this monitoring child, '
            'relative to the immutable samples and checked statuses supplied by its parent. Unchanged polls, byte growth '
            'and elapsed time alone are excluded. New completed durations earn monitoring credit; '
            'execution receipts separately update shared time expectations. Timing overruns use the original per-action benchmark. '
            'This is neither scientific evidence nor a cancellation or scheduling instruction.'),
            'report_schema': {'type': 'array', 'items': deepcopy(FINDING_SCHEMA), 'x-source': 'monitoring_findings'}}

    def information_report_source(self):
        if not self.include_handoff_checks:
            return self.report_source()
        return {'type': 'array', 'meaning': (
            'New execution information acquired by this episode through its selected samples or handoff checks, '
            'relative to parent-supplied knowledge. A handoff check retains its checked-status identity; '
            'it is not relabeled as a monitoring sample. Closure checks and refreshes earn nothing. '
            'This is separate from operational/scientific credit and duration forecasts.'),
            'report_schema': {'type': 'array', 'items': deepcopy(CHECK_AWARE_FINDING_SCHEMA),
                              'x-source': 'monitoring_findings'}}

    def information_view(self, store, *, assignment, episode_id, run_id):
        findings = self.findings(store, assignment=assignment, episode_id=episode_id, run_id=run_id)
        value = self.information_unit*len(findings)
        if not math.isfinite(value):
            raise ValueError('finite_monitoring_information_credit_required')
        return {'monitoring_information_credit': value,
                'monitoring_findings': findings, 'monitoring_information_binding': self.as_record()}

    def findings(self, store, *, assignment, episode_id, run_id):
        prior = [*assignment.get('prior_samples', []), *assignment.get('prior_checked_statuses', [])]
        states = {sample['state'] for sample in prior}
        outcomes = {sample['outcome'] for sample in prior}
        outputs = {_output(output) for sample in prior for output in sample['outputs']}
        completed_timings = {timing for sample in prior if (timing := _completed_timing(sample)) is not None}
        maximum_elapsed = {}
        def remember(sample):
            if sample.get('elapsed_seconds') is not None:
                measure = sample['duration_measure']
                maximum_elapsed[measure] = max(maximum_elapsed.get(measure, 0), sample['elapsed_seconds'])
        for sample in prior:
            remember(sample)
        overruns, findings = set(), []
        # JSON extraction reads only the fields needed for local scoring;
        # archived native/scientific payloads are not loaded into memory.
        selected = "json_extract(result,'$.operational_sample_ref') IS NOT NULL"
        if self.include_handoff_checks:
            selected = '('+selected+" OR (json_extract(action,'$.tool')='homology.check_handoff' " \
                "AND json_type(result,'$.result.sample')='object'))"
        rows = store.db.execute('''SELECT json_extract(result,'$.result'),
            json_extract(result,'$.resource_tool_estimates'),
            json_extract(result,'$.operational_sample_ref') FROM runtime_actions
            WHERE run_id=? AND episode_id=? AND json_extract(result,'$.status')='completed'
            AND '''+selected+' ORDER BY decision_index', (run_id, episode_id))
        for row in rows:
            body = json.loads(row[0])
            sample = body if row[2] is not None else {
                **body['sample'], 'checked_at_unix_seconds': body['checked_at_unix_seconds']}
            if sample['job_ref'] != assignment['job_ref']:
                raise ValueError('monitoring_sample_job_mismatch')
            estimates = json.loads(row[1]) if row[1] else []
            timing = _completed_timing(sample)
            fresh_outputs = [output for output in sample['outputs'] if _output(output) not in outputs]
            fresh_overruns = []
            for estimate in estimates:
                if estimate['status'] != 'available' or estimate['timing_relation'] != 'exceeds_observed_maximum':
                    continue
                identity = _overrun(estimate)
                if identity in overruns:
                    continue
                known = maximum_elapsed.get(estimate['forecast_duration_measure'], 0) > estimate['observed_max_seconds']
                overruns.add(identity)
                if not known:
                    fresh_overruns.append(estimate)
            finding = {'sample': sample, 'new_state': sample['state'] not in states,
                'new_outcome': sample['outcome'] not in outcomes,
                'new_completed_timing': timing is not None and timing not in completed_timings,
                'new_output_states': [{key: output[key] for key in ('role', 'available', 'writer_closed')}
                                      for output in fresh_outputs], 'new_timing_overruns': fresh_overruns}
            if self.include_handoff_checks:
                finding['sample'] = {**sample,
                    'observation_kind': 'monitor_sample' if row[2] is not None else 'handoff_check',
                    'sample_ref': sample.get('sample_ref'),
                    'sampled_at_unix_seconds': sample.get('sampled_at_unix_seconds'),
                    'checked_at_unix_seconds': sample.get('checked_at_unix_seconds')}
            if (finding['new_state'] or finding['new_outcome'] or finding['new_completed_timing']
                    or fresh_outputs or fresh_overruns):
                findings.append(finding)
            if timing is not None:
                completed_timings.add(timing)
            states.add(sample['state'])
            outcomes.add(sample['outcome'])
            outputs.update(_output(output) for output in sample['outputs'])
            remember(sample)
        return findings

    def __call__(self, store, *, role, assignment, episode_id, run_id):
        if role not in self.information_roles:
            raise ValueError('monitoring_credit_requires_monitoring_episode')
        return self.information_view(store, assignment=assignment,
            episode_id=episode_id, run_id=run_id)['monitoring_information_credit']
