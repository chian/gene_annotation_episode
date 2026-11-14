"""Scoped job-role bindings for the existing shared method_loop.

No production score, timing exchange rate, itinerary or private decision loop.
The caller owns resource/scoring configuration; the parent owns commissioning.
"""
from __future__ import annotations

from copy import copy, deepcopy
import json
import math
import sqlite3
import subprocess
from collections.abc import Mapping

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.communication import REFERENCE_FORMATS, ReportBoundaryError
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.homology_jobs import HomologyJobs
from gene_annotation_episode.episodic_workflow.root.library.homology_job_contracts import HANDOFF_SCHEMA
from gene_annotation_episode.episodic_workflow.root.library.homology_job_status_contracts import SAMPLE_SCHEMA, STATUS_SCHEMA
from gene_annotation_episode.episodic_workflow.root.homology_results import HomologyResults
from gene_annotation_episode.episodic_workflow.root.library.native_phmmer_inputs import NativePhmmerInput
from gene_annotation_episode.episodic_workflow.root.library.homology_result_coverage import recorded_coverage
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.episodic_workflow.root.library.monitoring_credit import EXECUTION_OBSERVATION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.library.resource_estimation import (recorded_estimate, recorded_forecasts, validate_recorded_estimates,
    report_source as resource_report_source)


from types import SimpleNamespace
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_contracts import obj, reference, CHECKED_STATUS_SCHEMA, RESULT_PROGRESS_SCHEMA, _result_progress, _binding

def _validate_recorded_return(self, value, assignment, *, store=None, schema=None):
    """References and native fact fields must describe their actual record.

    Parent-defined names/interpretations remain allowed. A declared native
    sample identity cannot be reused to smuggle different recorded values.
    This does not assess scientific suitability or decide continuation.
    """
    validate_recorded_estimates(store, value, schema=schema, job_ref=assignment['job_ref'])
    reference_namespaces = {'sample_ref': 'job_sample', 'job_ref': 'homology_job',
        'registry_ref': 'execution_registry'}
    def declares(actual, expected, keyword=None):
        # Recognize declared native meanings, not literal schema text.
        # Additional validation constraints and annotations cannot disable
        # provenance checks. Enum/type ordering is not semantic ordering.
        if isinstance(expected, Mapping):
            if not isinstance(actual, Mapping):
                return False
            for key, child in expected.items():
                if keyword != 'properties' and key not in {
                        'type', 'format', 'x-reference-namespace', 'enum', 'properties', 'items'}:
                    continue
                if key == 'enum' and key not in actual and 'const' in actual:
                    if actual['const'] not in child:
                        return False
                elif key not in actual or not declares(actual[key], child, key):
                    return False
            return True
        if keyword == 'enum':
            return isinstance(actual, list) and bool(actual) and all(item in expected for item in actual)
        if keyword == 'type':
            allowed = set(expected if isinstance(expected, list) else [expected])
            if 'number' in allowed:
                allowed.add('integer')
            declared = actual if isinstance(actual, list) else [actual]
            return bool(declared) and all(item in allowed for item in declared)
        return actual == expected
    def known_identity(value, namespace):
        if namespace == 'homology_job' and value == assignment['job_ref']:
            return True
        if namespace == 'job_sample' and store is not None:
            if self.recorded_sample(store, value, assignment) is not None:
                return True
        try:
            return self.jobs.resolve(value, namespace)
        except sqlite3.Error:
            return False
    def visit(node, declared):
        if isinstance(node, Mapping):
            properties = declared.get('properties', {}) if declared is not None else {}
            # This is the declared native execution-observation shape, not
            # a reservation of arbitrary parent-chosen field names.
            if declares(properties, EXECUTION_OBSERVATION_SCHEMA['properties'], 'properties'):
                kind = node['observation_kind']
                if kind == 'handoff_check':
                    if node.get('sample_ref') is not None or node.get('sampled_at_unix_seconds') is not None:
                        raise ReportBoundaryError('A checked status is not a sample', code='checked_status_identity_mismatch')
                    if store is None:
                        raise ReportBoundaryError('Selected checked-status record is unavailable',
                                                  code='checked_status_record_unavailable')
                    rows = store.db.execute('''SELECT json_extract(result,'$.result.sample')
                        FROM runtime_actions WHERE json_extract(action,'$.tool')='homology.check_handoff'
                        AND json_extract(result,'$.status')='completed'
                        AND json_extract(result,'$.result.checked_at_unix_seconds')=?
                        AND json_extract(result,'$.result.sample.job_ref')=?
                        AND json_extract(result,'$.result.sample.registry_ref')=?''',
                        (node.get('checked_at_unix_seconds'), assignment['job_ref'], self.jobs.config['registry_ref']))
                    if not any(all(node[key] == value for key, value in json.loads(row[0]).items())
                               for row in rows):
                        raise ReportBoundaryError('Checked status differs from selected recorded work',
                                                  code='checked_status_fact_mismatch')
                elif (node.get('sample_ref') is None or node.get('sampled_at_unix_seconds') is None
                      or node.get('checked_at_unix_seconds') is not None):
                    raise ReportBoundaryError('A sample needs its original sample identity',
                                              code='sample_identity_mismatch')
            identities = {name: field.get('x-reference-namespace') for name, field in properties.items()
                if field.get('format') in REFERENCE_FORMATS and node.get(name) is not None}
            if declared is None:
                # Untyped direct consumers can establish identity from the
                # registry, without reserving arbitrary parent field names.
                identities = {name: namespace for name, namespace in reference_namespaces.items()
                    if node.get(name) is not None and known_identity(node[name], namespace)}
            for name, namespace in identities.items():
                if namespace == 'homology_job' and node[name] != assignment['job_ref']:
                    raise ReportBoundaryError('Returned job differs from its assignment', code='job_identity_mismatch')
                if namespace == 'execution_registry' and node[name] != self.jobs.config['registry_ref']:
                    raise ReportBoundaryError('Returned registry differs from its binding', code='registry_identity_mismatch')
                if namespace != 'job_sample':
                    continue
                actual = self.recorded_sample(store, node[name], assignment) if store is not None else None
                if actual is None:
                    try:
                        row = self.jobs.db.execute('SELECT job_ref,body FROM samples WHERE sample_ref=?',
                                                  (node[name],)).fetchone()
                    except sqlite3.Error:
                        row = None
                    actual = json.loads(row['body']) if row is not None and row['job_ref'] == assignment['job_ref'] else None
                if actual is None:
                    raise ReportBoundaryError('Sample does not belong to the assigned job', code='sample_identity_mismatch')
                fields = [key for key in node.keys() & actual.keys()
                    if properties.get(key, {}).get('format') not in REFERENCE_FORMATS
                    or properties[key].get('x-reference-namespace') == reference_namespaces.get(key)]
                if any(node[key] != actual[key] for key in fields):
                    raise ReportBoundaryError('Native sample fields differ from their recorded values', code='sample_fact_mismatch')
            for name, child in node.items():
                visit(child, properties.get(name) if declared is not None else None)
        elif isinstance(node, (list, tuple)):
            for child in node:
                visit(child, declared.get('items') if declared is not None else None)
    visit(value, schema)

def received_timing_records(self, store, value, schema, scope):
    """Normalize requested, admitted timing facts to their physical receipt.

    Read only the original typed host measurement and immutable assignment
    at the selected check/sample boundary. No live poll, private reasoning,
    new statistic, child-score sum or biological interpretation participates.
    A missing provenance record is a reporting issue, never a form rejection.
    """
    from gene_annotation_episode.episodic_workflow.root.native_measurement import NativeMeasurement
    from gene_annotation_episode.episodic_workflow.root.native_timing_information import record_native_measurement
    references, issues = [], []

    def measured_status(status, source, path):
        if not isinstance(status, Mapping) or status.get('outcome') not in {'succeeded', 'failed'}:
            return
        if status.get('elapsed_seconds') is None:
            return
        code = None
        job = status['job_ref']
        try:
            if status['registry_ref'] != self.jobs.config['registry_ref']:
                raise ValueError('received_status_registry_mismatch')
            checked = status.get('checked_at_unix_seconds')
            sample = status.get('sample_ref')
            row = store.db.execute('''SELECT exports.value, episodes.request, actions.result
                FROM runtime_actions actions JOIN runtime_episodes episodes
                ON episodes.run_id=actions.run_id AND episodes.episode_id=actions.episode_id
                JOIN json_each(actions.result,'$.execution_statistics_export') exports
                WHERE json_extract(exports.value,'$.job_ref')=?
                AND json_type(exports.value,'$.measurement')='object'
                AND json_extract(actions.result,'$.status')='completed'
                AND ((? IS NOT NULL AND json_extract(actions.action,'$.tool')='homology.check_handoff'
                     AND json_extract(actions.result,'$.result.checked_at_unix_seconds')=?)
                  OR (? IS NOT NULL AND json_extract(actions.action,'$.tool')='homology.sample'
                      AND json_extract(actions.result,'$.operational_sample_ref')=?))
                ORDER BY actions.rowid LIMIT 1''', (job, checked, checked, sample, sample)).fetchone()
            if row is None:
                code = 'measurement_not_recorded'
            else:
                exported, request, outcome = (json.loads(item) for item in row)
                message = request['message']
                carriers = ([message['job_assignment']] if 'job_assignment' in message else [])
                resource = message.get('episode_assignment', {})
                if 'adapter_assignment' in resource:
                    carriers.append(resource['adapter_assignment'])
                if (not carriers or any(not isinstance(item, Mapping) for item in carriers)
                        or any(json.dumps(item, sort_keys=True, allow_nan=False)
                            != json.dumps(carriers[0], sort_keys=True, allow_nan=False)
                            for item in carriers[1:])):
                    raise ValueError('received_assignment_missing_or_conflicting')
                assignment = carriers[0]
                query_ref, cpu = assignment['query_ref'], assignment['cpu']
                if assignment['job_ref'] != job or type(cpu) is not int:
                    raise ValueError('received_assignment_identity_mismatch')
                handoff = assignment.get('handoff')
                if handoff is not None and (handoff['job_ref'] != job
                        or handoff['registry_ref'] != status['registry_ref']):
                    raise ValueError('received_assignment_registry_mismatch')
                # Both scopes and the immutable registry operands must
                # agree with this action's saved assignment. The registry
                # is a witness, never a fallback source of query identity.
                self._query(store, store.validate_scope(message['scope']), query_ref)
                query = self._query(store, scope, query_ref)
                registered = self.jobs._row(job)
                if (registered['query_ref'] != query_ref or registered['cpu'] != cpu
                        or registered['search_mode'] != assignment.get('search_mode', 'native_defaults')):
                    raise ValueError('received_assignment_job_mismatch')
                from gene_annotation_episode.episodic_workflow.root.library.homology_job_inputs import normalize_query_fasta
                symbols = artifact_path(store, query['sequence_ref']).read_text()
                if registered['query_fasta'] != normalize_query_fasta('>query\n'+symbols+'\n'):
                    raise ValueError('received_assignment_query_mismatch')
                actual = outcome['result']['sample'] if checked is not None else outcome['result']
                if (any(actual[key] != status[key] for key in STATUS_SCHEMA['properties'])
                        or checked is not None and sample is not None
                        or checked is None and (actual['sample_ref'] != sample
                            or actual['sampled_at_unix_seconds'] != status['sampled_at_unix_seconds'])):
                    raise ValueError('received_selected_status_mismatch')
                measured = NativeMeasurement.from_record(exported['measurement'])
                if (self.statistics is None
                        or measured.execution_class != self.statistics.execution_class(self.jobs, registered)
                        or exported['attempt_sha256'] != measured.statistic.attempt_sha256
                        or exported['class_ref'] != measured.execution_class.ref):
                    raise ValueError('received_measurement_assignment_mismatch')
                if 'adapter_assignment' in resource:
                    selection = (resource['handoff']['resource_selection']
                        if 'handoff' in resource else resource['resource_selection'])
                    if (selection['capability_binding_ref'] != status['registry_ref']
                            or selection['allocation']['cpu'] != cpu
                            or selection['resource_id'] != measured.execution_class.resource_id):
                        raise ValueError('received_resource_assignment_mismatch')
                expected_outcome = ('succeeded' if measured.statistic.outcome == 'succeeded'
                    else 'failed' if measured.statistic.outcome in {'failed', 'cancelled', 'resource_limit'}
                    else 'unknown')
                if (measured.statistic.duration_kind != 'complete'
                        or measured.statistic.elapsed_seconds != status['elapsed_seconds']
                        or measured.execution_class.duration_measure != status['duration_measure']
                        or expected_outcome != status['outcome']):
                    code = 'measurement_status_mismatch'
                else:
                    references.append(record_native_measurement(store, measured, operation='phmmer_search',
                        operands=[{'role': 'query', 'subject_ref': query_ref}]))
        except (ValueError, KeyError, TypeError, ContractError):
            code = 'measurement_record_invalid'
        except (OSError, sqlite3.Error):
            code = 'receipt_storage_unavailable'
        if code is not None:
            issues.append({'source': source, 'field': path, 'job_ref': job, 'code': code})

    def visit(node, declared, path):
        source = declared.get('x-source')
        if source in {'job_checked_status', 'job_sample'}:
            measured_status(node, source, path)
        elif source == 'monitoring_findings' and isinstance(node, (list, tuple)):
            for index, finding in enumerate(node):
                measured_status(finding['sample'], source, path+[index, 'sample'])
        elif isinstance(node, Mapping):
            for key, child in node.items():
                if key in declared.get('properties', {}):
                    visit(child, declared['properties'][key], path+[key])
        elif isinstance(node, (list, tuple)) and 'items' in declared:
            for index, child in enumerate(node):
                visit(child, declared['items'], path+[index])
    visit(value, schema, [])
    return {'version': 'received_job_timing_receipts_v1',
            'native_execution_refs': list(dict.fromkeys(references)), 'issues': issues}
