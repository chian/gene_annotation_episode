"""A103 homology resource adapter for its launch/results episode."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from types import SimpleNamespace

from .communication import ReportBoundaryError, plain
from .episode_bindings import reference_in_context
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.resource_work_submission.episode import ResourceEpisode
from .homology_results import recorded_coverage
from .resource_estimation import recorded_forecasts


from .resource_records import (ROLES, RESOURCE_ROLES, LAUNCH_VERSION, RESULTS_VERSION,
    FAILURE_CODES, ALLOCATION_SCHEMA, SELECTION_SCHEMA, INPUT_VERSION_SCHEMA, CAPABILITY_SCHEMA,
    FAILURE_SCHEMA, RECEIVER_SCHEMA, HANDOFF_SCHEMA, LAUNCH_SCHEMA, RESULTS_SCHEMA,
    _string, _reference, _array, _nullable, _validate)
from .resource_information import ResourceInformation
from .launch_instructions import validate_selection
from .local_resources import LocalResources


def _failure(code, references=()):
    return {'code': code, 'affected_refs': list(references),
        'diagnostic_ref': None, 'partial_record_refs': []}


def _outcome(value=None, failure=None, record_refs=()):
    return {'status': 'failed' if failure else 'completed', 'record_refs': list(record_refs),
        'changed_record_refs': [], 'result': value, 'feedback': failure}


class _Message:
    def __init__(self, value):
        self.value = value

    def as_record(self):
        return deepcopy(self.value)


class HomologyResourceAdapter:
    """C9 wrapper around existing HomologyEpisode ordinary operations.

    Physical resource_id comes from the caller's statistics binding when one
    exists. Without it the registry supplies a logical identity only, without
    claiming a particular machine. capability_binding_ref is always the actual
    immutable execution registry identity.
    """
    def __init__(self, homology_episode, store, journal, resource_estimator=None):
        from .homology_service_setup import homology_binding_types, bound_homology_family
        types = homology_binding_types()
        if any(type(homology_episode) is cls for children in types.values() for cls in children.values()):
            supplied = homology_episode
            homology_episode = bound_homology_family(supplied)[supplied.commissioning_parent]
        if (not isinstance(homology_episode, dict)
                or not {'job_launch', 'job_results'} <= set(homology_episode) <= {'job_launch', 'job_monitor', 'job_results'}):
            raise TypeError('explicit_private_homology_role_bindings_required')
        parents = {getattr(binding, 'commissioning_parent', None) for binding in homology_episode.values()}
        if len(parents) != 1:
            raise ValueError('homology_roles_require_one_actual_parent')
        parent, = parents
        expected = types.get(parent)
        if expected is None or any(type(binding) is not expected[role] for role, binding in homology_episode.items()):
            raise TypeError('explicit_private_homology_role_bindings_required')
        self.homology = dict(homology_episode)
        from importlib import import_module
        result_owner = type(self.homology['job_results']).__module__.rsplit('.', 1)[0]
        self._result_progress = import_module(result_owner + '.contracts')._result_progress
        self.jobs = self.homology['job_launch'].jobs
        self.statistics = self.homology['job_launch'].statistics
        if any(binding.jobs.config != self.jobs.config
               or binding.jobs.directory != self.jobs.directory
               for binding in self.homology.values()):
            raise ValueError('homology_roles_require_original_shared_job_registry')
        self.store, self.journal = store, journal
        self.information = ResourceInformation(store, run_id=journal.run_id, jobs=self.jobs)
        self.resource_estimator = resource_estimator
        statistics = self.statistics
        self.resource_id = (statistics.resource_id if statistics is not None
            else 'registry-local:' + self.jobs.config['registry_ref'])
        provider = getattr(self.homology['job_launch'], 'native_event_provider', None)
        if provider is not None and provider.resource_id != self.resource_id:
            raise ValueError('native_event_resource_binding_mismatch')
        self.record_selection = None

    def bind_record_selection(self, callback):
        self.record_selection = callback

    def as_record(self):
        return {'version': 'homology_resource_adapter_v2', 'resource_id': self.resource_id,
            'resource_identity_kind': 'physical_binding' if self.statistics else 'logical_registry',
            'homology': {role: binding.as_record() for role, binding in self.homology.items()},
            'resource_estimator': None if self.resource_estimator is None else self.resource_estimator.as_record()}

    def capability(self):
        jobs = self.jobs
        files = (jobs.config['executable']['path'], jobs.config['reference_database']['path'])
        availability = 'unavailable'
        if all(Path(path).is_file() for path in files) and os.access(files[0], os.X_OK):
            try:
                probe = subprocess.run(['systemctl', '--user', 'show-environment'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False)
                availability = 'available' if probe.returncode == 0 else 'unavailable'
            except (OSError, subprocess.SubprocessError):
                availability = 'unknown'
        resources = LocalResources.configured().snapshot()
        policy = jobs.config['job_limits']
        return {'resource_id': self.resource_id, 'kind': 'local', 'availability': availability,
            'local_resources': resources,
            'allocation_limits': deepcopy(policy),
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'provenance_refs': [jobs.config['registry_ref']], 'knowledge_entry_ids': [],
            'tool_names': [tool['name'] for tool in self.homology['job_launch'].catalog(
                SimpleNamespace(path=(('job_launch', self.resource_id),)))]}

    def _selection(self, cpu):
        policy = self.jobs.config['job_limits']
        return {'resource_id': self.resource_id, 'kind': 'local',
            'allocation': {'cpu': cpu, **deepcopy(policy)},
            'capability_binding_ref': self.jobs.config['registry_ref']}

    def _verify_selection(self, selected, cpu):
        if selected != self._selection(cpu):
            raise ValueError('resource_selection_conflict')

    def prepare_assignment(self, context, role, launch_assignment, scope, operation_key):
        value = plain(launch_assignment)
        if role == 'results':
            self._selector(value['requested_data_selector'])
            handoff = value['handoff']
            legacy = self._native_handoff(handoff)
            job = self.jobs._row(legacy['job_ref'])
            self.homology['job_launch']._query(self.store, plain(scope), job['query_ref'])
            assigned = {'job_ref': job['job_ref'], 'query_ref': job['query_ref'],
                'cpu': job['cpu'], 'handoff': legacy}
            if 'search_modes' in self.jobs.config:
                assigned['search_mode'] = job['search_mode']
            # The selector narrows requested extraction; no tool runs here.
            value['adapter_assignment'] = assigned
            return value
        if role != 'launch_local':
            raise ValueError('homology_resource_requires_local_role')
        job = value['job_request']
        if set(job) - {'query_ref', 'cpu', 'search_mode', 'existing_job_ref'}:
            raise ValueError('unsupported_homology_job_operand')
        if 'existing_job_ref' in job:
            row = self.jobs._row(job['existing_job_ref'])
            for key in ('query_ref', 'cpu', 'search_mode'):
                if key in job and job[key] != row[key]:
                    raise ValueError('resource_assignment_conflict')
            cpu, query = row['cpu'], row['query_ref']
        else:
            cpu, query = job['cpu'], job['query_ref']
        self._verify_selection(value['resource_selection'], cpu)
        constraints = value['constraints']
        for key, actual in value['resource_selection']['allocation'].items():
            if key in constraints and constraints[key] != actual:
                raise ValueError('resource_selection_conflict')
        # Verify declared versions against actual semantic input bytes before
        # ordering. The existing job service snapshots immutable FASTA bytes.
        self.homology['job_launch']._query(self.store, plain(scope), query)
        if not self.store.roots(query):
            if self.record_selection is None:
                raise ValueError('reference_query_requires_explicit_received_operand')
            received=self.record_selection(context)
            if (received.get('run_id')!=context.run_id or received.get('episode_id')!=context.episode_id
                    or query not in received['known_record_refs']):
                raise ValueError('reference_query_requires_explicit_received_operand')
        for supplied in value['immutable_input_versions']:
            record = self.store.get(supplied['reference'])
            if not self.store.reference_subset([supplied['reference']], plain(scope)):
                raise ValueError('resource_input_outside_assigned_scope')
            if supplied['version'] is not None and str(record.get('revision')) != supplied['version']:
                raise ValueError('resource_input_version_conflict')
            expected = supplied['content_sha256']
            if expected is not None:
                from .materials import artifact_path
                artifact = record['id'] if record['record_type'] == 'artifact' else record.get('sequence_ref')
                if artifact is None or hashlib.sha256(artifact_path(self.store, artifact).read_bytes()).hexdigest() != expected:
                    raise ValueError('resource_input_version_conflict')
        value['adapter_assignment'] = self.homology['job_launch'].assign(self.store, 'job_launch', job,
            plain(scope), operation_key=operation_key)
        return value

    def _legacy(self, context):
        assignment = plain(context.assignment).get('adapter_assignment')
        if assignment is None:
            return None
        role = 'job_results' if context.role == 'results' else 'job_launch'
        # Only the tool's internal role lookup is aliased. The actual episode
        # ID, original goal/request, owner and durable path remain in context.
        return SimpleNamespace(episode_id=context.episode_id, scope=plain(context.scope),
            path=(*context.path[:-1], (role, context.path[-1][1])),
            request=SimpleNamespace(message=_Message({'job_assignment': assignment})),
            workflow=SimpleNamespace(store=self.store, run_id=context.run_id))

    def catalog(self, context):
        source = self._legacy(context)
        return [] if source is None else self.homology[source.path[-1][0]].catalog(source)

    async def execute(self, context, tool_name, arguments, operation_key):
        replay = self.information.selected_handoff(context, tool_name, arguments, operation_key)
        if replay is not None:
            return replay
        source = self._legacy(context)
        if source is None:
            return _outcome(failure=_failure('resource_assignment_conflict'))
        assignment = self.homology[source.path[-1][0]].assignment(source)
        try:
            self._verify_selection(plain(context.assignment)['resource_selection']
                if context.role != 'results' else plain(context.assignment)['handoff']['resource_selection'],
                assignment['cpu'])
            row = self.jobs._row(assignment['job_ref'])
            if (row['query_ref'] != assignment['query_ref'] or row['cpu'] != assignment['cpu']
                    or row['search_mode'] != assignment.get('search_mode', 'native_defaults')):
                raise ValueError('resource_assignment_conflict')
            if context.role == 'results' and tool_name == 'homology.extract':
                start, count = self._selector(plain(context.assignment)['requested_data_selector'])
                offset, limit = arguments.get('offset', 0), arguments['limit']
                # A zero-row capture permits inspecting the retained snapshot
                # before choosing pages. All acquired rows stay in the request.
                if limit and (offset < start or count is not None and offset + limit > start + count):
                    raise ValueError('requested_data_selector_conflict')
        except ValueError as error:
            return _outcome(failure=_failure(str(error), [assignment['job_ref']]))
        outcome = await self.homology[source.path[-1][0]].execute(source, tool_name, plain(arguments), operation_key=operation_key)
        if tool_name == 'homology.check_handoff' and outcome['status'] == 'completed':
            outcome['execution_handoff'] = self._wrap(context, outcome['result'])
        return self.information.publish_handoff(context, tool_name, arguments, outcome, operation_key)

    @staticmethod
    def _selector(value):
        """Homology selectors are a zero-based native-row interval.

        An empty selector requests all rows; nullable limit leaves the upper
        bound open. Page acquisition and parser repair remain selected tools.
        """
        schema = {'type': 'object', 'properties': {
            'offset': {'type': 'integer', 'minimum': 0},
            'limit': {'type': ['integer', 'null'], 'minimum': 0}},
            'additionalProperties': False}
        try:
            value = _validate(value, schema)
        except ValueError as error:
            raise ValueError('invalid_resource_selector') from error
        return value.get('offset', 0), value.get('limit')

    def _wrap(self, context, checked):
        assignment = plain(context.assignment)
        job = self.jobs._row(checked['handoff']['job_ref'])
        versions = (assignment['handoff']['submitted_input_versions'] if context.role == 'results'
            else assignment['immutable_input_versions'])
        return {'version': 'execution_handoff_v1', 'execution_handle': job['job_ref'],
            'resource_selection': self._selection(job['cpu']), 'submitted_input_versions': versions,
            'monitoring': {'provider_id': self.resource_id, 'target_handle': job['job_ref'],
                'contract_ref': checked['handoff']['status_interface']},
            'results': {'provider_id': self.resource_id, 'target_handle': job['job_ref'],
                'contract_ref': checked['handoff']['results_interface']},
            'checked_at': datetime.fromtimestamp(checked['checked_at_unix_seconds'], timezone.utc).isoformat(),
            'check_record_refs': [checked['receipt_ref']], 'state': 'usable', 'failure': None}

    def _native_handoff(self, handoff):
        _validate(handoff, HANDOFF_SCHEMA)
        jobs = self.jobs
        row = jobs._row(handoff['execution_handle'])
        self._verify_selection(handoff['resource_selection'], row['cpu'])
        # Immutable registry/interfaces, without touching today's native handle
        # or asking the receiving interface for a new observation.
        from .homology_jobs import VERSION
        native = {'job_ref': row['job_ref'], 'registry_ref': jobs.config['registry_ref'],
            'backend': VERSION, 'status_interface': 'homology.status.v1',
            'progress_interface': 'homology.progress.v1', 'results_interface': 'homology.results.v1'}
        expected = {'monitoring': native['status_interface'], 'results': native['results_interface']}
        if handoff['state'] != 'usable' or handoff['failure'] is not None or not handoff['check_record_refs']:
            raise ValueError('invalid_resource_handoff')
        for key, contract in expected.items():
            receiver = handoff[key]
            if receiver != {'provider_id': self.resource_id, 'target_handle': row['job_ref'], 'contract_ref': contract}:
                raise ValueError('invalid_resource_handoff')
        for reference in handoff['check_record_refs']:
            receipt = jobs.db.execute('SELECT job_ref FROM handoffs WHERE receipt_ref=?', (reference,)).fetchone()
            if receipt is None or receipt[0] != row['job_ref']:
                raise ValueError('invalid_resource_handoff')
        # A valid receipt identity cannot bless altered input versions, check
        # times or receiver operands. C9 is an exact wrapper of selected work.
        witnesses = self.store.db.execute('''SELECT json_extract(result,'$.execution_handoff')
            FROM runtime_actions WHERE run_id=? AND json_extract(result,'$.status')='completed'
            AND json_extract(result,'$.execution_handoff.execution_handle')=?''',
            (self.information.run_id, row['job_ref']))
        if not any(json.loads(witness[0]) == handoff for witness in witnesses):
            # A published proof is already actual saved work even if runtime
            # was interrupted before filling its selected action result.
            matches = [source for source in self.information._sources()
                if self.information._body(source).get('execution_handoff') == handoff]
            if not matches:
                raise ValueError('invalid_resource_handoff')
            for source in matches:
                body = self.information._body(source)
                self.information.read_handoff_source(source['id'], scope=body['scope'])
        return native

    def check_handoff(self, context, handoff, operation_key):
        replay = self.information.selected_handoff(context, 'resource.check_handoff',
            {'handoff': handoff}, operation_key)
        if replay is not None:
            return replay
        native = self._native_handoff(handoff)
        assignment = plain(context.assignment)
        if (assignment.get('version') == LAUNCH_VERSION
                and assignment['immutable_input_versions'] != handoff['submitted_input_versions']):
            raise ValueError('resource_assignment_conflict')
        if assignment.get('version') == LAUNCH_VERSION:
            job = self.jobs._row(handoff['execution_handle'])
            selection = handoff['resource_selection']
            if (assignment['resource_selection'] is not None
                    and selection != assignment['resource_selection']
                    or not ResourceEpisode._permitted(assignment, selection)):
                raise ValueError('resource_selection_conflict')
            for key, actual in selection['allocation'].items():
                if key in assignment['constraints'] and assignment['constraints'][key] != actual:
                    raise ValueError('resource_selection_conflict')
            requested = assignment['job_request']
            for key in ('query_ref', 'cpu', 'search_mode'):
                if key in requested and requested[key] != job[key]:
                    raise ValueError('resource_assignment_conflict')
            if 'existing_job_ref' in requested and requested['existing_job_ref'] != job['job_ref']:
                raise ValueError('resource_assignment_conflict')
        checked = self.jobs.check_handoff(native)
        value = self._wrap(context, checked)
        outcome = {**_outcome(checked), 'execution_handoff': value}
        return self.information.publish_handoff(context, 'resource.check_handoff',
            {'handoff': handoff}, outcome, operation_key)

    def execution_handoff(self, context):
        values = self.execution_handoffs(context)
        return values[0] if len(values) == 1 else None

    def execution_handoffs(self, context):
        candidates = []
        callback = self.record_selection
        if callback is not None:
            selected = callback(context)
            if selected.get('run_id') != context.run_id or selected.get('episode_id') != context.episode_id:
                raise ValueError('resource_information_identity_conflict')
            for reference in selected['known_record_refs']:
                source = self.store.get(reference)
                if source.get('provider') != 'episode.resource_handoff':
                    continue
                body = self.information._body(source)
                if body.get('registry_ref') != self.jobs.config['registry_ref']:
                    continue
                body = self.information.read_handoff_source(reference, scope=plain(context.scope))
                try:
                    self.information._validate_assignment(context, body['execution_handoff'], body['job'])
                except ValueError as error:
                    # A receiving parent can know valid handoffs for other
                    # query jobs. Authenticate their custody first, then keep
                    # only those matching this particular commission.
                    if str(error)!='resource_information_assignment_conflict':raise
                    continue
                candidates.append((reference, body['execution_handoff']))
        rows = self.store.db.execute('''SELECT decision_index,json_extract(result,'$.execution_handoff')
            FROM runtime_actions WHERE run_id=? AND episode_id=?
            AND json_extract(result,'$.status')='completed'
            AND json_type(result,'$.execution_handoff')='object'
            ORDER BY decision_index''', (context.run_id, context.episode_id))
        for row in rows:
            handoff = json.loads(row[1])
            if handoff['resource_selection']['resource_id'] != self.resource_id:
                continue
            self._native_handoff(handoff)
            candidates.append(('legacy:' + str(row[0]), handoff))
        latest = {}
        for source_ref, handoff in candidates:
            from .resource_information import _utc
            identity = (handoff['resource_selection']['capability_binding_ref'], handoff['execution_handle'])
            ordering = (_utc(handoff['checked_at']), source_ref)
            if identity not in latest or ordering > latest[identity][0]:
                latest[identity] = (ordering, handoff)
        return [deepcopy(latest[key][1]) for key in sorted(latest)]

    def received_form_references(self, context, form, schema, operation_key):
        references = []
        def visit(value, declared):
            source = declared.get('x-source')
            if source in {'execution_handoff', 'execution_handoffs'}:
                values = value if source == 'execution_handoffs' else ([] if value is None else [value])
                for handoff in values:
                    if handoff['resource_selection']['resource_id'] == self.resource_id:
                        references.extend(self.information.references_for_form(context, handoff,
                            {'x-source': 'execution_handoff'}))
            elif isinstance(value, Mapping):
                for key, child in value.items():
                    if key in declared.get('properties', {}):
                        visit(child, declared['properties'][key])
            elif isinstance(value, (list, tuple)) and 'items' in declared:
                for child in value:
                    visit(child, declared['items'])
        visit(form, schema)
        return sorted(set(references))

    def initial_references(self, context):
        return self.information.references_for_initial(context)

    def fact_sources(self, role):
        values = self.homology['job_results' if role == 'results' else 'job_launch'].fact_sources('job_results' if role == 'results' else 'job_launch') if role != 'launch' else {}
        if values:
            values['job_handoff']['meaning'] = 'The original recorded usable receiving handoff available to this episode; no new receiving check occurs at closure.'
            values['job_handoff_state']['meaning'] = 'Whether an original usable checked handoff is available in the assigned or received records; no scientific completion claim.'
        return values

    def facts(self, context, completion_snapshot):
        source = self._legacy(context)
        handoffs = self.execution_handoffs(context)
        handoff = handoffs[0] if len(handoffs) == 1 else None
        facts = {}
        if source is not None:
            assignment = self.homology[source.path[-1][0]].assignment(source)
            native = self._native_handoff(handoff) if handoff is not None else assignment.get('handoff')
            facts = {'job_ref': assignment['job_ref'], 'job_cpu': assignment['cpu'],
                'job_handoff': native, 'job_handoff_state': 'usable' if native is not None else 'unavailable',
                'job_handoff_failure': None if native is not None else 'receiving_interface_unavailable',
                'job_sample': self.homology[source.path[-1][0]].latest_sample(source),
                'resource_tool_estimates': recorded_forecasts(self.store,
                    run_id=context.run_id, episode_id=context.episode_id)}
            if 'search_modes' in self.jobs.config:
                facts['job_search_mode'] = assignment['search_mode']
            legacy_role = source.path[-1][0]
            if legacy_role == 'job_launch':
                facts['job_checked_status'] = self.homology[source.path[-1][0]].latest_checked_status(source)
            if self.homology[legacy_role].has_information_channel(legacy_role):
                information = self.homology[source.path[-1][0]].credit_view(source)
                facts.update(monitoring_information_credit=information['monitoring_information_credit'],
                    monitoring_findings=information['monitoring_findings'])
            if legacy_role == 'job_results':
                facts.update(job_result_progress=None, job_result_progress_failure=None)
                selected = self.store.db.execute('''SELECT json_extract(result,'$.result.snapshot_ref')
                    FROM runtime_actions WHERE run_id=? AND episode_id=?
                    AND json_extract(action,'$.tool') IN ('homology.extract','homology.coverage')
                    AND json_type(result,'$.result.snapshot_ref')='text'
                    ORDER BY decision_index DESC LIMIT 1''', (context.run_id, context.episode_id)).fetchone()
                if selected is not None:
                    from .domain import ContractError
                    try:
                        coverage = recorded_coverage(self.store, selected[0], query_ref=assignment['query_ref'],
                            scope=plain(context.scope), execution_context={'job_ref': assignment['job_ref'],
                                'registry_ref': self.jobs.config['registry_ref']})
                        facts['job_result_progress'] = self._result_progress(coverage)
                    except ContractError:
                        facts['job_result_progress_failure'] = 'invalid_snapshot_or_scope'
                    except (OSError, sqlite3.Error):
                        facts['job_result_progress_failure'] = 'storage_failure'
                    except (ValueError, KeyError, TypeError):
                        facts['job_result_progress_failure'] = 'coverage_read_failed'
        facts['execution_handoff'] = handoff
        facts['execution_handoffs'] = handoffs
        return facts

    def resolve(self, context, reference, namespace):
        source = self._legacy(context)
        assignment = self.homology[source.path[-1][0]].assignment(source) if source else None
        if namespace == 'resource_binding':
            return reference == self.resource_id
        if namespace == 'resource_interface':
            return reference in {'homology.status.v1', 'homology.results.v1'}
        if namespace == 'resource_execution':
            namespace = 'homology_job'
        if namespace in {'resource_input_version', 'resource_input_digest', 'resource_check_timestamp'}:
            handoffs = self.execution_handoffs(context)
            if not handoffs and context.role == 'results':
                handoffs = [plain(context.assignment)['handoff']]
            if namespace == 'resource_check_timestamp':
                return any(reference == handoff['checked_at'] for handoff in handoffs)
            field = 'version' if namespace == 'resource_input_version' else 'content_sha256'
            return any(reference == item[field] for handoff in handoffs for item in handoff['submitted_input_versions'])
        return self.homology[source.path[-1][0] if source else 'job_launch'].resolve(self.store, plain(context.scope), reference, namespace, assignment=assignment)

    def validate_report(self, context, form, original_schema):
        source = self._legacy(context)
        if source is not None:
            self.homology[source.path[-1][0]].validate_report(form, self.homology[source.path[-1][0]].assignment(source),
                store=self.store, schema=plain(original_schema), role=source.path[-1][0])

    def credit_view(self, context, receiver_selection):
        source = self._legacy(context)
        if source is None:
            raise ValueError('explicit_role_credit_binding_required:' + context.role)
        return self.homology[source.path[-1][0]].credit_view(source)

    def decision_context(self, context):
        statistics = self.statistics
        if statistics is None or self.resource_estimator is None:
            return {'resource_tool_estimates': []}
        from .execution_expectations import capture_execution_scopes
        source = self._legacy(context)
        if source is not None:
            assignment = self.homology[source.path[-1][0]].assignment(source)
            execution_class = statistics.execution_class(self.jobs,
                self.jobs._row(assignment['job_ref']))
            captured = capture_execution_scopes(statistics.history_path, [execution_class],
                assigned_execution_class_ref=execution_class.ref)
            estimates = self.resource_estimator.estimate(captured,
                job_ref=assignment['job_ref'], sample=self.homology[source.path[-1][0]].latest_sample(source))
        else:
            # The launch episode knows its parent's exact work before choosing
            # a resource. No order/staging/dispatch is needed for this forecast.
            job = plain(context.assignment).get('job_request', {})
            if 'existing_job_ref' in job:
                row = self.jobs._row(job['existing_job_ref'])
                self.homology['job_launch']._query(self.store, plain(context.scope), row['query_ref'])
                execution_class = statistics.execution_class(self.jobs, row)
                captured = capture_execution_scopes(statistics.history_path, [execution_class],
                    assigned_execution_class_ref=execution_class.ref)
                return {'resource_tool_estimates': self.resource_estimator.estimate(captured,
                    job_ref=row['job_ref'])}
            if 'query_ref' not in job or 'cpu' not in job:
                return {'resource_tool_estimates': []}
            from .materials import artifact_path
            query = self.homology['job_launch']._query(self.store, plain(context.scope), job['query_ref'])
            sequence = artifact_path(self.store, query['sequence_ref']).read_text()
            execution_class = statistics.execution_class_for_query(self.jobs,
                query_fasta='>query\n' + sequence + '\n', cpu=job['cpu'],
                search_mode=job.get('search_mode', 'native_defaults'))
            captured = capture_execution_scopes(statistics.history_path, [execution_class])
            estimates = self.resource_estimator.estimate_context(captured)
        return {'resource_tool_estimates': estimates}

