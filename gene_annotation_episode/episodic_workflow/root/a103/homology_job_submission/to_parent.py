from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_submission.contracts import AcquisitionError, CHECKED_STATUS_SCHEMA, ContractError, EXECUTION_OBSERVATION_SCHEMA, HANDOFF_SCHEMA, Mapping, REFERENCE_FORMATS, ROLES, ReportBoundaryError, SAMPLE_SCHEMA, deepcopy, json, recorded_estimate, recorded_forecasts, reference, resource_report_source, sqlite3, subprocess, validate_recorded_estimates

class SubmissionReport:

    def fact_sources(self, role):
        if role not in ROLES:
            return {}
        handoff = {**deepcopy(HANDOFF_SCHEMA), 'type': ['object', 'null']}
        sample = {**deepcopy(SAMPLE_SCHEMA), 'type': ['object', 'null']}
        values = {'job_ref': (reference('homology_job'), 'The immutable assigned job, not an episode identity.'), 'job_cpu': ({'type': 'integer', 'minimum': 1}, 'Assigned CPU threads selected by the parent and retained in the job; not measured consumption.'), 'job_handoff': (handoff, 'A freshly functionally checked receiving-interface handoff, or null when unavailable.'), 'job_handoff_state': ({'type': 'string', 'enum': ['usable', 'unavailable']}, 'Whether this closure established a usable receiving-interface handoff; no scientific completion claim.'), 'job_handoff_failure': ({'type': ['string', 'null'], 'enum': [None, 'job_not_submitted', 'submission_unconfirmed', 'native_handle_identity_mismatch', 'receiving_interface_unavailable']}, 'The basic reason no usable handoff could be returned; null after a successful receiving-interface check.'), 'job_sample': (sample, 'The last actual sample selected by this child, unchanged on replay; null if it selected none.')}
        if 'search_modes' in self.jobs.config:
            values['job_search_mode'] = ({'type': 'string', 'enum': list(self.jobs.search_modes)}, 'The immutable parent-selected search mode. Maximum sensitivity disables heuristic filters; it is not evidence of a specific function or a stronger significance threshold.')
        sources = {key: {'type': schema['type'], 'meaning': meaning, 'report_schema': {**schema, 'x-source': key}} for key, (schema, meaning) in values.items()}
        sources['resource_tool_estimates'] = resource_report_source()
        sources['job_checked_status'] = {'type': ['object', 'null'], 'meaning': "The status and timestamp of this child's last successful selected homology.check_handoff action. This is the recorded check-time state, not a fresh closure poll or a monitoring sample. Null if no selected check succeeded. The parent decides what subsequent work this information warrants.", 'report_schema': {**deepcopy(CHECKED_STATUS_SCHEMA), 'type': ['object', 'null'], 'x-source': 'job_checked_status'}}
        if self.has_information_channel(role):
            sources['monitoring_findings'] = self.monitoring_projector.information_report_source()
            sources['monitoring_information_credit'] = {'type': 'number', 'meaning': 'Monitoring information actually obtained by this episode; separate from operational/scientific score and duration estimates. It does not select the controller input.', 'binding': self.monitoring_projector.as_record(), 'report_schema': {'type': 'number', 'x-source': 'monitoring_information_credit'}}
        return sources

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
        assignment = self.assignment(source)
        try:
            handoff = self.jobs.handoff(assignment['job_ref'])
            self.jobs.check_handoff(handoff)
            failure = None
        except (sqlite3.Error, subprocess.SubprocessError):
            handoff, failure = (None, 'receiving_interface_unavailable')
        except (ValueError, KeyError, OSError, AcquisitionError) as error:
            handoff = None
            try:
                row = self.jobs._row(assignment['job_ref'])
                handle = self.jobs.directory / assignment['job_ref'] / 'native.handle.json'
                unreadable = False
                try:
                    prepared = handle.is_file() and json.loads(handle.read_text()).get('stage') == 'prepared'
                except (OSError, ValueError, TypeError, AttributeError):
                    prepared, unreadable = (False, True)
                failure = 'receiving_interface_unavailable' if unreadable else 'submission_unconfirmed' if prepared else 'job_not_submitted' if not row['submission_requested'] else 'submission_unconfirmed' if not handle.is_file() else 'native_handle_identity_mismatch' if str(error) == 'native_handle_does_not_describe_registered_job' else 'receiving_interface_unavailable'
            except (sqlite3.Error, ValueError, KeyError):
                failure = 'receiving_interface_unavailable'
        facts = {'job_ref': assignment['job_ref'], 'job_cpu': assignment['cpu'], 'job_handoff': handoff, 'job_handoff_state': 'usable' if handoff else 'unavailable', 'job_handoff_failure': failure, 'job_sample': self.latest_sample(source), 'resource_tool_estimates': recorded_forecasts(source.workflow.store, run_id=source.workflow.run_id, episode_id=source.episode_id)}
        if 'search_modes' in self.jobs.config:
            facts['job_search_mode'] = assignment['search_mode']
        facts['job_checked_status'] = self.latest_checked_status(source)
        if self.has_information_channel(source.path[-1][0]):
            information = self.credit_view(source) if credit_view is None else credit_view
            facts.update(monitoring_information_credit=information['monitoring_information_credit'], monitoring_findings=information['monitoring_findings'])
        return facts

    def validate_report(self, value, assignment, *, role, store=None, schema=None):
        """Validate retained sources under the original three-role return contract."""
        if role not in {'job_launch': None, 'job_monitor': None, 'job_results': None}:
            raise ValueError('homology_return_role_required')
        self._validate_role_return_sources(role, schema)
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
