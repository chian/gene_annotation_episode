"""Original Homology shared resource admission and exact receipt/read closure."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.message_contracts import HomologyJobs, LocalJobPolicy, copy, json
from gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.message_contracts import ContractError, artifact_path
from gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.message_contracts import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_credit import project_homology_credit
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_fact_readers import project_credit_view_for_role
from gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.message_contracts import ContractError, EXECUTION_OBSERVATION_SCHEMA, Mapping, REFERENCE_FORMATS, ReportBoundaryError, json, recorded_estimate, sqlite3, validate_recorded_estimates
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_fact_readers import read_facts_for_role
from gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.message_contracts import ContractError, Mapping, STATUS_SCHEMA, artifact_path, deepcopy, json, sqlite3
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_role_readers import goal_instructions
from gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.message_contracts import sqlite3
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_role_readers import tool_catalog
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_operations import operation_for_role

async def execute_assigned(owner, source, name, args, *, operation_key):
    result = await owner._execute(source, name, args, operation_key=operation_key)
    if owner.native_event_provider is not None and name in {'homology.submit', 'homology.resume_start'}:
        from gene_annotation_episode.episodic_workflow.root.a104.method_loop.durable import DurableExecutionError
        job_ref = owner.assignment(source)['job_ref']
        try:
            owner.bind_job_native_events(source, job_ref)
            result['native_event_targets'] = owner.jobs.native_event_targets(job_ref)
        except (DurableExecutionError, sqlite3.Error, OSError, ValueError, KeyError, TypeError) as error:
            result['native_event_targets'] = []
            storage = isinstance(error, (sqlite3.Error, OSError)) or (isinstance(error, DurableExecutionError) and error.failure['code'] == 'storage_failure')
            result['native_event_target_failure'] = {'code': 'native_event_storage_unavailable' if storage else 'native_event_identity_conflict', 'affected_refs': [job_ref]}
    if owner.statistics is not None:
        try:
            exported = list(owner.jobs.recover_statistics(owner.assignment(source)['job_ref']))
        except (sqlite3.Error, OSError) as error:
            exported = [{'job_ref': owner.assignment(source)['job_ref'], 'state': 'unavailable', 'code': 'statistics_registry_unavailable', 'exception_type': type(error).__name__}]
        result['execution_statistics_export'] = exported
    return result

class HomologyFamilyResources:

    def __init__(self, jobs: HomologyJobs, *, parser_policy: LocalJobPolicy, credit_projector, credit_binding, monitoring_projector, monitoring_binding, statistics=None, _family_resources=None):
        if _family_resources is not None:
            from ..homology_binding_family import HomologyBindingFamily
            if type(_family_resources) is not HomologyBindingFamily:
                raise TypeError('explicit_original_homology_family_resources_required')
            owner = _family_resources
            if jobs is not owner.jobs or parser_policy is not owner.parser_policy or credit_projector is not owner._job_credit_calculator or (credit_binding is not owner._role_credit_bindings['job_launch']) or (monitoring_projector is not owner.monitoring_projector) or (monitoring_binding is not owner._role_credit_bindings['job_monitor']) or (statistics is not owner.statistics):
                raise ValueError('original_homology_family_resource_identity_conflict')
            self.__dict__ = owner.__dict__
            return
        if type(jobs) is not HomologyJobs or type(parser_policy) is not LocalJobPolicy:
            raise TypeError('explicit_homology_resources_required')
        if not callable(credit_projector) or not isinstance(credit_binding, dict) or (not credit_binding):
            raise ValueError('explicit_operational_credit_binding_required')
        self.jobs, self.parser_policy, self._job_credit_calculator = (jobs, parser_policy, credit_projector)
        if not callable(monitoring_projector) or not isinstance(monitoring_binding, dict) or (not monitoring_binding):
            raise ValueError('explicit_monitoring_credit_binding_required')
        self.monitoring_projector = monitoring_projector
        self._role_credit_bindings = {'job_launch': json.loads(json.dumps(credit_binding, allow_nan=False)), 'job_monitor': json.loads(json.dumps(monitoring_binding, allow_nan=False)), 'job_results': json.loads(json.dumps(credit_binding, allow_nan=False))}
        if statistics is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.execution_recording import HomologyStatistics
            if type(statistics) is not HomologyStatistics:
                raise TypeError('typed_homology_statistics_binding_required')
        self.statistics = statistics
        self.native_event_provider = None

    def with_native_events(self, provider):
        """A host-local view; the caller's binding/descriptor stays unchanged."""
        from gene_annotation_episode.episodic_workflow.root.a104.native_events import NativeEventProvider
        if type(provider) is not NativeEventProvider:
            raise TypeError('typed_native_event_provider_required')
        if self.statistics is not None and self.statistics.resource_id != provider.resource_id:
            raise ValueError('native_event_resource_identity_conflict')
        view = copy(self)
        view.native_event_provider = provider
        return view

    def recover_native_events(self):
        summary = {}
        if self.native_event_provider is not None:
            for value in self.jobs.recover_native_events(native_event_provider=self.native_event_provider):
                summary[value['state']] = summary.get(value['state'], 0) + 1
        return summary

    def bind_job_native_events(self, source, job_ref):
        provider = self.native_event_provider
        if provider is None:
            return None
        if source.workflow.run_id != provider.run_id:
            raise ValueError('native_event_run_identity_conflict')
        original = self.jobs.native_event_binding(job_ref)
        if original is None and (self.jobs._handle(job_ref).path.exists() or self.jobs._row(job_ref)['submission_requested']):
            return None
        return provider.for_job(owner_episode_id=source.episode_id, job_ref=job_ref, registry_ref=self.jobs.config['registry_ref'], original_binding=original)

    def recover_statistics(self):
        summary = {}
        if self.statistics is not None:
            for value in self.jobs.recover_statistics():
                summary[value['state']] = summary.get(value['state'], 0) + 1
        return summary

    def prospective_execution_classes(self, store, scope):
        """Caller-resource configurations for actual eligible protein records.

        Reading this inventory does not translate a sequence, choose work,
        create an order, or launch anything. It is recomputed for later
        decisions so newly acquired protein records can become visible.
        """
        return list({value['execution_class'].ref: value['execution_class'] for value in self.prospective_execution_options(store, scope)}.values())

    def prospective_execution_options(self, store, scope):
        """Local selectable operands and their statistical class, never a choice.

        Query identity stays in the episode's local configuration inventory;
        it is not added to shared run statistics or credited as a finding.
        """
        if self.statistics is None:
            return []
        options = []
        offset = 0
        while True:
            page = store.query_records('subject', scope=scope, offset=offset, limit=100)
            for candidate in page['records']:
                try:
                    query = self._query(store, scope, candidate['id'])
                    symbols = artifact_path(store, query['sequence_ref']).read_text()
                except (ValueError, KeyError, OSError, ContractError):
                    continue
                for cpu in range(1, self.jobs.config['max_cpu'] + 1):
                    for mode in self.jobs.search_modes:
                        execution_class = self.statistics.execution_class_for_query(self.jobs, query_fasta='>query\n' + symbols + '\n', cpu=cpu, search_mode=mode)
                        options.append({'query_ref': query['id'], 'cpu': cpu, 'search_mode': mode, 'execution_class': execution_class})
            if page['next_offset'] is None:
                return options
            offset = page['next_offset']

    def working_state(self, source):
        return {'role': source.path[-1][0], 'assignment': self.assignment(source)}

    def binding_for(self, role):
        if role not in self._role_credit_bindings:
            raise ValueError('unknown_job_episode_role')
        return deepcopy(self._role_credit_bindings[role])

    def has_information_channel(self, role):
        return getattr(self.monitoring_projector, 'include_handoff_checks', False) and role in getattr(self.monitoring_projector, 'information_roles', ()) and callable(getattr(self.monitoring_projector, 'information_view', None))

    def initial_credit(self, store, role, assignment, episode_id, run_id):
        return project_homology_credit(self._job_credit_calculator, self.monitoring_projector, store, role, assignment, episode_id, run_id)

    def credit_view(self, source):
        return project_credit_view_for_role(self, source)

    @staticmethod
    def _query(store, scope, query_ref):
        from gene_annotation_episode.episodic_workflow.root.a104.homology_query import protein_query
        return protein_query(store, scope, query_ref, error_code='job_query_must_be_protein_of_assigned_target')

    @staticmethod
    def assignment(source):
        return source.request.message.as_record()['job_assignment']

    def resolve(self, store, scope, value, namespace, *, assignment=None):
        if assignment is not None and namespace == 'subject' and (value == assignment.get('query_ref')):
            try:
                self._query(store, scope, value)
            except (ValueError, KeyError, ContractError):
                return False
            return True
        if assignment is not None and (namespace in {None, 'homology_job'} and value == assignment['job_ref'] or (namespace in {None, 'job_sample'} and self.recorded_sample(store, value, assignment) is not None)):
            try:
                self._query(store, scope, assignment['query_ref'])
            except (ValueError, KeyError, ContractError):
                return False
            return True
        if namespace in {'job_execution_estimate', 'execution_class', 'execution_expectation', 'execution_proposal'}:
            estimate = recorded_estimate(store, value, assignment['job_ref'] if assignment else None, namespace=namespace)
            if estimate is None:
                return False
            if estimate['job_ref'] is None or (assignment is None and namespace != 'job_execution_estimate'):
                try:
                    return estimate['execution_class_ref'] in {execution_class.ref for execution_class in self.prospective_execution_classes(store, scope)}
                except (ValueError, KeyError, OSError, ContractError):
                    return False
            try:
                query_ref = assignment['query_ref'] if assignment is not None and estimate['job_ref'] == assignment['job_ref'] else self.jobs._row(estimate['job_ref'])['query_ref']
                self._query(store, scope, query_ref)
            except (ValueError, KeyError, ContractError, sqlite3.Error):
                return False
            return True
        try:
            if not self.jobs.resolve(value, namespace):
                return False
            if value == self.jobs.config['registry_ref']:
                return True
            if self.jobs.resolve(value, 'homology_job'):
                job_ref = value
            elif self.jobs.resolve(value, 'job_sample'):
                job_ref = self.jobs.db.execute('SELECT job_ref FROM samples WHERE sample_ref=?', (value,)).fetchone()[0]
            else:
                row = self.jobs.db.execute('SELECT job_ref FROM handoffs WHERE receipt_ref=?', (value,)).fetchone()
                if row is None:
                    return False
                job_ref = row[0]
            if assignment is not None and job_ref != assignment['job_ref']:
                return False
            self._query(store, scope, self.jobs._row(job_ref)['query_ref'])
        except (ValueError, KeyError, ContractError, sqlite3.Error):
            return False
        return True

    def facts(self, source, *, credit_view=None):
        return read_facts_for_role(self, source, credit_view=credit_view)

    def validate_report(self, value, assignment, *, role, store=None, schema=None):
        """Select the owning job episode's return binding explicitly."""
        roles = {'job_launch': 'job_launch', 'job_monitor': 'job_monitor', 'job_results': 'job_results'}
        if role not in roles:
            raise ValueError('homology_return_role_required')
        selected_role = roles[role]
        self._validate_role_return_sources(selected_role, schema)
        self._validate_recorded_return(value, assignment, store=store, schema=schema)

    def _validate_role_return_sources(self, role, schema):
        if schema is None:
            return
        allowed = self.fact_sources(role)
        for node in schema.get('properties', {}).values():
            source = node.get('x-source')
            if isinstance(source, str) and source.startswith(('job_', 'monitoring_')) and (source not in allowed):
                raise ReportBoundaryError('Fact does not belong to this job episode', code='homology_return_source_role_conflict')

    def _validate_recorded_return(self, value, assignment, *, store=None, schema=None):
        """References and native fact fields must describe their actual record.

        Parent-defined names/interpretations remain allowed. A declared native
        sample identity cannot be reused to smuggle different recorded values.
        This does not assess scientific suitability or decide continuation.
        """
        validate_recorded_estimates(store, value, schema=schema, job_ref=assignment['job_ref'])
        reference_namespaces = {'sample_ref': 'job_sample', 'job_ref': 'homology_job', 'registry_ref': 'execution_registry'}

        def declares(actual, expected, keyword=None):
            if isinstance(expected, Mapping):
                if not isinstance(actual, Mapping):
                    return False
                for key, child in expected.items():
                    if keyword != 'properties' and key not in {'type', 'format', 'x-reference-namespace', 'enum', 'properties', 'items'}:
                        continue
                    if key == 'enum' and key not in actual and ('const' in actual):
                        if actual['const'] not in child:
                            return False
                    elif key not in actual or not declares(actual[key], child, key):
                        return False
                return True
            if keyword == 'enum':
                return isinstance(actual, list) and bool(actual) and all((item in expected for item in actual))
            if keyword == 'type':
                allowed = set(expected if isinstance(expected, list) else [expected])
                if 'number' in allowed:
                    allowed.add('integer')
                declared = actual if isinstance(actual, list) else [actual]
                return bool(declared) and all((item in allowed for item in declared))
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
                if declares(properties, EXECUTION_OBSERVATION_SCHEMA['properties'], 'properties'):
                    kind = node['observation_kind']
                    if kind == 'handoff_check':
                        if node.get('sample_ref') is not None or node.get('sampled_at_unix_seconds') is not None:
                            raise ReportBoundaryError('A checked status is not a sample', code='checked_status_identity_mismatch')
                        if store is None:
                            raise ReportBoundaryError('Selected checked-status record is unavailable', code='checked_status_record_unavailable')
                        rows = store.db.execute("SELECT json_extract(result,'$.result.sample')\n                            FROM runtime_actions WHERE json_extract(action,'$.tool')='homology.check_handoff'\n                            AND json_extract(result,'$.status')='completed'\n                            AND json_extract(result,'$.result.checked_at_unix_seconds')=?\n                            AND json_extract(result,'$.result.sample.job_ref')=?\n                            AND json_extract(result,'$.result.sample.registry_ref')=?", (node.get('checked_at_unix_seconds'), assignment['job_ref'], self.jobs.config['registry_ref']))
                        if not any((all((node[key] == value for key, value in json.loads(row[0]).items())) for row in rows)):
                            raise ReportBoundaryError('Checked status differs from selected recorded work', code='checked_status_fact_mismatch')
                    elif node.get('sample_ref') is None or node.get('sampled_at_unix_seconds') is None or node.get('checked_at_unix_seconds') is not None:
                        raise ReportBoundaryError('A sample needs its original sample identity', code='sample_identity_mismatch')
                identities = {name: field.get('x-reference-namespace') for name, field in properties.items() if field.get('format') in REFERENCE_FORMATS and node.get(name) is not None}
                if declared is None:
                    identities = {name: namespace for name, namespace in reference_namespaces.items() if node.get(name) is not None and known_identity(node[name], namespace)}
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
                            row = self.jobs.db.execute('SELECT job_ref,body FROM samples WHERE sample_ref=?', (node[name],)).fetchone()
                        except sqlite3.Error:
                            row = None
                        actual = json.loads(row['body']) if row is not None and row['job_ref'] == assignment['job_ref'] else None
                    if actual is None:
                        raise ReportBoundaryError('Sample does not belong to the assigned job', code='sample_identity_mismatch')
                    fields = [key for key in node.keys() & actual.keys() if properties.get(key, {}).get('format') not in REFERENCE_FORMATS or properties[key].get('x-reference-namespace') == reference_namespaces.get(key)]
                    if any((node[key] != actual[key] for key in fields)):
                        raise ReportBoundaryError('Native sample fields differ from their recorded values', code='sample_fact_mismatch')
                for name, child in node.items():
                    visit(child, properties.get(name) if declared is not None else None)
            elif isinstance(node, (list, tuple)):
                for child in node:
                    visit(child, declared.get('items') if declared is not None else None)
        visit(value, schema)

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
        from gene_annotation_episode.episodic_workflow.root.a104.execution_recording import NativeMeasurement
        from gene_annotation_episode.episodic_workflow.root.a104.native_timing_information import record_native_measurement
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
                    from gene_annotation_episode.episodic_workflow.root.a104.homology_jobs import normalize_query_fasta
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

    def instructions(self, role):
        return goal_instructions(role, self.has_information_channel)

    def catalog(self, source):
        role = source.path[-1][0]
        return tool_catalog(role)

    async def execute(self, source, name, args, *, operation_key):
        return await execute_assigned(self, source, name, args, operation_key=operation_key)

    async def _execute(self, source, name, args, *, operation_key):
        return await operation_for_role(self, source, name, args, operation_key=operation_key)
