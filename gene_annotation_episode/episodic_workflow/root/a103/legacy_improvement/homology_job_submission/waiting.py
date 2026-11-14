"""Private job_launch waiting behavior for A103."""
from __future__ import annotations
from .contracts import ContractError, Mapping, STATUS_SCHEMA, artifact_path, deepcopy, json, sqlite3

class HomologyEpisodeWaiting:

    def latest_sample(self, source, *, include_inherited=False):
        row = source.workflow.store.db.execute("SELECT json_extract(result,'$.result')\n            FROM runtime_actions WHERE run_id=? AND episode_id=?\n            AND json_extract(result,'$.operational_sample_ref') IS NOT NULL\n            ORDER BY decision_index DESC LIMIT 1", (source.workflow.run_id, source.episode_id)).fetchone()
        if row is not None:
            return json.loads(row[0])
        prior = self.assignment(source).get('prior_samples', []) if include_inherited else []
        return deepcopy(prior[-1]) if prior else None

    @staticmethod
    def recorded_sample(store, sample_ref, assignment):
        for sample in assignment.get('prior_samples', []):
            if sample['sample_ref'] == sample_ref and sample['job_ref'] == assignment['job_ref']:
                return deepcopy(sample)
        row = store.db.execute("SELECT json_extract(result,'$.result') FROM runtime_actions\n            WHERE json_extract(result,'$.operational_sample_ref')=?\n            AND json_extract(result,'$.result.job_ref')=?\n            AND json_extract(result,'$.status')='completed' LIMIT 1", (sample_ref, assignment['job_ref'])).fetchone()
        return json.loads(row[0]) if row is not None else None

    def latest_checked_status(self, source):
        assignment = self.assignment(source)
        row = source.workflow.store.db.execute("SELECT json_extract(result,'$.result.sample'),\n            json_extract(result,'$.result.checked_at_unix_seconds') FROM runtime_actions\n            WHERE run_id=? AND episode_id=?\n            AND json_extract(action,'$.tool')='homology.check_handoff'\n            AND json_extract(result,'$.status')='completed'\n            AND json_extract(result,'$.result.sample.job_ref')=?\n            AND json_extract(result,'$.result.sample.registry_ref')=?\n            ORDER BY decision_index DESC LIMIT 1", (source.workflow.run_id, source.episode_id, assignment['job_ref'], self.jobs.config['registry_ref'])).fetchone()
        return {'checked_at_unix_seconds': row[1], **json.loads(row[0])} if row is not None else None

    def received_timing_records(self, store, value, schema, scope):
        """Normalize requested, admitted timing facts to their physical receipt.

        Read only the original typed host measurement and immutable assignment
        at the selected check/sample boundary. No live poll, private reasoning,
        new statistic, child-score sum or biological interpretation participates.
        A missing provenance record is a reporting issue, never a form rejection.
        """
        from gene_annotation_episode.episodic_workflow.root.a103.execution_recording import NativeMeasurement
        from gene_annotation_episode.episodic_workflow.root.a103.native_timing_information import record_native_measurement
        references, issues = ([], [])

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
                row = store.db.execute("SELECT exports.value, episodes.request, actions.result\n                    FROM runtime_actions actions JOIN runtime_episodes episodes\n                    ON episodes.run_id=actions.run_id AND episodes.episode_id=actions.episode_id\n                    JOIN json_each(actions.result,'$.execution_statistics_export') exports\n                    WHERE json_extract(exports.value,'$.job_ref')=?\n                    AND json_type(exports.value,'$.measurement')='object'\n                    AND json_extract(actions.result,'$.status')='completed'\n                    AND ((? IS NOT NULL AND json_extract(actions.action,'$.tool')='homology.check_handoff'\n                         AND json_extract(actions.result,'$.result.checked_at_unix_seconds')=?)\n                      OR (? IS NOT NULL AND json_extract(actions.action,'$.tool')='homology.sample'\n                          AND json_extract(actions.result,'$.operational_sample_ref')=?))\n                    ORDER BY actions.rowid LIMIT 1", (job, checked, checked, sample, sample)).fetchone()
                if row is None:
                    code = 'measurement_not_recorded'
                else:
                    exported, request, outcome = (json.loads(item) for item in row)
                    message = request['message']
                    carriers = [message['job_assignment']] if 'job_assignment' in message else []
                    resource = message.get('episode_assignment', {})
                    if 'adapter_assignment' in resource:
                        carriers.append(resource['adapter_assignment'])
                    if not carriers or any((not isinstance(item, Mapping) for item in carriers)) or any((json.dumps(item, sort_keys=True, allow_nan=False) != json.dumps(carriers[0], sort_keys=True, allow_nan=False) for item in carriers[1:])):
                        raise ValueError('received_assignment_missing_or_conflicting')
                    assignment = carriers[0]
                    query_ref, cpu = (assignment['query_ref'], assignment['cpu'])
                    if assignment['job_ref'] != job or type(cpu) is not int:
                        raise ValueError('received_assignment_identity_mismatch')
                    handoff = assignment.get('handoff')
                    if handoff is not None and (handoff['job_ref'] != job or handoff['registry_ref'] != status['registry_ref']):
                        raise ValueError('received_assignment_registry_mismatch')
                    self._query(store, store.validate_scope(message['scope']), query_ref)
                    query = self._query(store, scope, query_ref)
                    registered = self.jobs._row(job)
                    if registered['query_ref'] != query_ref or registered['cpu'] != cpu or registered['search_mode'] != assignment.get('search_mode', 'native_defaults'):
                        raise ValueError('received_assignment_job_mismatch')
                    from gene_annotation_episode.episodic_workflow.root.a103.homology_jobs import normalize_query_fasta
                    symbols = artifact_path(store, query['sequence_ref']).read_text()
                    if registered['query_fasta'] != normalize_query_fasta('>query\n' + symbols + '\n'):
                        raise ValueError('received_assignment_query_mismatch')
                    actual = outcome['result']['sample'] if checked is not None else outcome['result']
                    if any((actual[key] != status[key] for key in STATUS_SCHEMA['properties'])) or (checked is not None and sample is not None) or (checked is None and (actual['sample_ref'] != sample or actual['sampled_at_unix_seconds'] != status['sampled_at_unix_seconds'])):
                        raise ValueError('received_selected_status_mismatch')
                    measured = NativeMeasurement.from_record(exported['measurement'])
                    if self.statistics is None or measured.execution_class != self.statistics.execution_class(self.jobs, registered) or exported['attempt_sha256'] != measured.statistic.attempt_sha256 or (exported['class_ref'] != measured.execution_class.ref):
                        raise ValueError('received_measurement_assignment_mismatch')
                    if 'adapter_assignment' in resource:
                        selection = resource['handoff']['resource_selection'] if 'handoff' in resource else resource['resource_selection']
                        if selection['capability_binding_ref'] != status['registry_ref'] or selection['allocation']['cpu'] != cpu or selection['resource_id'] != measured.execution_class.resource_id:
                            raise ValueError('received_resource_assignment_mismatch')
                    expected_outcome = 'succeeded' if measured.statistic.outcome == 'succeeded' else 'failed' if measured.statistic.outcome in {'failed', 'cancelled', 'resource_limit'} else 'unknown'
                    if measured.statistic.duration_kind != 'complete' or measured.statistic.elapsed_seconds != status['elapsed_seconds'] or measured.execution_class.duration_measure != status['duration_measure'] or (expected_outcome != status['outcome']):
                        code = 'measurement_status_mismatch'
                    else:
                        references.append(record_native_measurement(store, measured, operation='phmmer_search', operands=[{'role': 'query', 'subject_ref': query_ref}]))
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
                    measured_status(finding['sample'], source, path + [index, 'sample'])
            elif isinstance(node, Mapping):
                for key, child in node.items():
                    if key in declared.get('properties', {}):
                        visit(child, declared['properties'][key], path + [key])
            elif isinstance(node, (list, tuple)) and 'items' in declared:
                for index, child in enumerate(node):
                    visit(child, declared['items'], path + [index])
        visit(value, schema, [])
        return {'version': 'received_job_timing_receipts_v1', 'native_execution_refs': list(dict.fromkeys(references)), 'issues': issues}
