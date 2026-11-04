"""Resource launch specializations for the ordinary shared Episode loop.

``ResourceEpisodes(services, resource_adapters=...)`` implements C7. Adapters
are explicit caller bindings, with the public methods implemented below by
``HomologyResourceAdapter(homology_episodes, store, journal,
resource_estimator=None)``. They supply ordinary operations, never a model loop.

The persisted ``resource_launch_assignment_v1`` wraps C9 LaunchAssignmentV1
losslessly and adds ``adapter_assignment`` only after a resource is selected.
That field holds the existing immutable job assignment; it is not a selectable
replacement for the scientific parent's job, inputs, constraints or allocation.
``resource_results_assignment_v1`` carries handoff and requested_data_selector.
"""
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
from .homology_episodes import HomologyEpisodes, obj, _result_progress
from .homology_results import recorded_coverage
from .resource_estimation import recorded_forecasts


from .resource_records import (ROLES, RESOURCE_ROLES, LAUNCH_VERSION, RESULTS_VERSION,
    FAILURE_CODES, ALLOCATION_SCHEMA, SELECTION_SCHEMA, INPUT_VERSION_SCHEMA, CAPABILITY_SCHEMA,
    FAILURE_SCHEMA, RECEIVER_SCHEMA, HANDOFF_SCHEMA, LAUNCH_SCHEMA, RESULTS_SCHEMA,
    _string, _reference, _array, _nullable, _validate)
from .resource_information import ResourceInformation


def _failure(code, references=()):
    return {'code': code, 'affected_refs': list(references),
        'diagnostic_ref': None, 'partial_record_refs': []}


def _outcome(value=None, failure=None, record_refs=()):
    return {'status': 'failed' if failure else 'completed', 'record_refs': list(record_refs),
        'changed_record_refs': [], 'result': value, 'feedback': failure}


def _availability_failure(capability):
    return {'unavailable': 'resource_unavailable',
        'authentication_required': 'resource_authentication_required',
        'unknown': 'resource_availability_unknown'}.get(capability['availability'])


class ResourceEpisodes:
    """C7 binding; all iteration/commissioning remains in shared method_loop.

    Adapter API: resource_id, capability(), as_record(), prepare_assignment(
    context, role, launch_assignment, scope, operation_key), catalog(context),
    execute(context, tool_name, arguments, operation_key), fact_sources(role),
    facts(context, completion_snapshot), resolve(context, reference, namespace),
    validate_report(context, form, original_schema), credit_view(context,
    receiver_selection). An optional decision_context(context) supplies actual
    prospective duration information. An adapter's tool list is authoritative.
    """
    roles = ROLES
    entry_roles = ('launch', 'results')

    def __init__(self, services, *, resource_adapters=()):
        self.services = services
        self.adapters = {}
        required = ('capability', 'as_record', 'prepare_assignment', 'catalog', 'execute',
            'fact_sources', 'facts', 'resolve', 'validate_report', 'credit_view')
        for adapter in resource_adapters:
            if (not isinstance(adapter.resource_id, str) or not adapter.resource_id
                    or any(not callable(getattr(adapter, name, None)) for name in required)):
                raise TypeError('explicit_resource_adapter_required')
            if adapter.resource_id in self.adapters:
                raise ValueError('duplicate_resource_id')
            bind_selection = getattr(adapter, 'bind_record_selection', None)
            if bind_selection is not None:
                bind_selection(getattr(services, 'record_selection', None))
            self.adapters[adapter.resource_id] = adapter

    def child_roles(self, role):
        return tuple(RESOURCE_ROLES) if role == 'launch' else ()

    def as_record(self):
        return {'version': 'resource_episode_binding_v1', 'binding_id': 'resource_episodes',
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'configuration': {'resource_adapters': [adapter.as_record()
                for adapter in self.adapters.values()]}}

    def credit_kind(self, role):
        if role not in ROLES:
            raise ValueError('unknown_resource_episode_role')
        return 'operational'

    def assignment_schema(self, role):
        self.credit_kind(role)
        return deepcopy(RESULTS_SCHEMA if role == 'results' else LAUNCH_SCHEMA)

    def permitted_common_actions(self, context):
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')

    def capabilities(self, context=None):
        """Include unbound declarations accurately, but never offer their tools."""
        values = {}
        for capability in self.services.capabilities():
            value = _validate(capability, CAPABILITY_SCHEMA)
            if value['resource_id'] not in self.adapters:
                value['tool_names'] = []
            values[value['resource_id']] = value
        for adapter in self.adapters.values():
            value = _validate(adapter.capability(), CAPABILITY_SCHEMA)
            if value['resource_id'] != adapter.resource_id:
                raise ValueError('resource_capability_identity_mismatch')
            if (context is not None and context.role in RESOURCE_ROLES
                    and context.assignment.get('resource_selection', {}).get('resource_id') == adapter.resource_id):
                bound = {tool['name'] for tool in adapter.catalog(context)}
                if not set(value['tool_names']) <= bound:
                    raise ValueError('resource_capability_tool_not_bound')
            values[value['resource_id']] = value
        return tuple(values.values())

    @staticmethod
    def _permitted(assignment, capability):
        constraints = assignment.get('constraints', {})
        selection = assignment.get('resource_selection')
        return ((selection is None or capability['resource_id'] == selection['resource_id']
                and capability['kind'] == selection['kind'])
            and ('allowed_resource_ids' not in constraints
                or capability['resource_id'] in constraints['allowed_resource_ids'])
            and ('allowed_kinds' not in constraints or capability['kind'] in constraints['allowed_kinds'])
            and ('resource_id' not in constraints or capability['resource_id'] == constraints['resource_id'])
            and ('kind' not in constraints or capability['kind'] == constraints['kind']))

    def allowed_children(self, parent, caller_capabilities):
        if parent.role != 'launch':
            return ()
        # Authentication/environment investigation may itself be selected when
        # ordinary bound operations exist. No claim of successful deployment.
        capabilities = self.capabilities()
        return tuple(role for role, kind in RESOURCE_ROLES.items()
            if any(value['kind'] == kind and value['resource_id'] in self.adapters
                and value['tool_names'] and value['availability'] != 'unavailable'
                and self._permitted(parent.assignment, value) for value in capabilities))

    def _adapter(self, assignment):
        selection = (assignment['handoff']['resource_selection']
            if assignment.get('version') == RESULTS_VERSION else assignment.get('resource_selection'))
        if selection is None or selection['resource_id'] not in self.adapters:
            raise ValueError('resource_not_bound')
        return self.adapters[selection['resource_id']]

    def _context_adapters(self, context):
        assignment = plain(context.assignment)
        if context.role in RESOURCE_ROLES or context.role == 'results':
            return (self._adapter(assignment),)
        if context.role == 'launch' and assignment.get('resource_selection') is not None:
            return (self._adapter(assignment),)
        return tuple(self.adapters.values())

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = plain(selection)
        # The common commissioning selection contains other fields (goal,
        # original typed form, scope). Only declared specialist operands enter.
        schema = self.assignment_schema(role)
        selected = {key: selected[key] for key in schema['properties'] if key in selected}
        selected = _validate(selected, schema)
        if parent.role == 'launch' and role not in RESOURCE_ROLES:
            raise ValueError('resource_child_role_not_owned_by_launch')
        if role == 'results':
            return self._adapter(selected).prepare_assignment(parent, role, selected, scope, operation_key)
        if parent.role == 'launch':
            inherited = plain(parent.assignment)
            inherited.pop('adapter_assignment', None)
            for key in LAUNCH_SCHEMA['properties']:
                if key != 'resource_selection' and selected[key] != inherited[key]:
                    raise ValueError('resource_assignment_conflict')
            if inherited['resource_selection'] is not None and selected['resource_selection'] != inherited['resource_selection']:
                raise ValueError('resource_selection_conflict')
        if role == 'launch':
            return selected
        if role not in RESOURCE_ROLES or selected['resource_selection'] is None:
            raise ValueError('explicit_resource_selection_required')
        capability = next((value for value in self.capabilities()
            if value['resource_id'] == selected['resource_selection']['resource_id']), None)
        if (capability is None or capability['kind'] != RESOURCE_ROLES[role]
                or not self._permitted(selected, capability)):
            raise ValueError('resource_selection_conflict')
        return self._adapter(selected).prepare_assignment(parent, role, selected, scope, operation_key)

    def instructions(self, context):
        responsibility = {'launch': 'Choose which actual execution approach is productive within the assigned job and constraints; commission a resource child when useful.',
            'launch_api': 'Investigate execution through the selected actual API or service, including real availability and authentication.',
            'launch_local': 'Investigate preparation, execution and receiving interfaces on the selected local resource.',
            'launch_hpc': 'Investigate the selected actual environment, queue, staging and execution interfaces.',
            'results': 'Acquire the requested data through the supplied receiving interface; the scientific parent interprets it.'}[context.role]
        return (responsibility + ' Revise later choices from actual outcomes. Ordinary operations are tools; '
            'iteration belongs to this shared Episode. Preserve the parent job, input versions, CPU, search '
            'and constraints. Capabilities and duration estimates inform your decisions, without selecting '
            'an approach or imposing an order. Unknown/authentication-required resources remain explicit. '
            'Return the original parent-defined typed form. Only the configured local controller governs continuation.')

    def decision_context(self, context, current_view):
        values = {'role': context.role, 'assignment': plain(context.assignment),
            'resource_capabilities': list(self.capabilities())}
        adapters = self._context_adapters(context)
        estimates = []
        for adapter in adapters:
            callback = getattr(adapter, 'decision_context', None)
            if callback is not None:
                estimates.extend(callback(context).get('resource_tool_estimates', []))
        values['resource_tool_estimates'] = estimates
        return values

    def catalog(self, context):
        tools = [{'name': 'resource.capabilities', 'description': 'Read actual capability availability and configured resource information; this does not select or submit work.',
            'input_schema': obj({})}]
        if context.role == 'launch':
            tools.append({'name': 'resource.inspect',
                'description': 'Inspect one declared resource and its actual binding. Unavailable, unknown, unauthenticated and unbound resources return distinct structured failures; this does not submit work.',
                'input_schema': obj({'resource_id': _string()})})
            tools.append({'name': 'resource.check_handoff',
                'description': 'Exercise the configured receiving interfaces of an explicitly supplied returned handoff. No submission or resource substitution.',
                'input_schema': obj({'handoff': HANDOFF_SCHEMA})})
        else:
            tools.extend(self._adapter(context.assignment).catalog(context))
        return tools

    async def execute(self, context, tool_name, arguments, operation_key):
        catalog = {item['name']: item for item in self.catalog(context)}
        if tool_name not in catalog:
            raise ValueError('tool_not_owned_by_resource_role')
        arguments = _validate(arguments, catalog[tool_name]['input_schema'])
        if tool_name == 'resource.capabilities':
            return _outcome({'capabilities': list(self.capabilities())})
        if tool_name == 'resource.inspect':
            reference = arguments['resource_id']
            capability = next((value for value in self.capabilities()
                if value['resource_id'] == reference), None)
            if capability is None:
                return _outcome(failure=_failure('resource_not_bound', [reference]))
            code = _availability_failure(capability)
            if code is None and reference not in self.adapters:
                code = 'resource_not_bound'
            return _outcome({'capability': capability},
                _failure(code, [reference]) if code else None)
        if tool_name == 'resource.check_handoff':
            handoff = arguments['handoff']
            try:
                adapter = self._adapter({'version': RESULTS_VERSION, 'handoff': handoff})
                callback = getattr(adapter, 'check_handoff', None)
                if callback is None:
                    return _outcome(failure=_failure('receiving_interface_unavailable'))
                value = callback(context, handoff, operation_key)
                return await value if inspect.isawaitable(value) else value
            except (ValueError, KeyError, OSError, sqlite3.Error) as error:
                if str(error) == 'resource_information_identity_conflict':
                    raise
                return _outcome(failure=_failure('invalid_resource_handoff', [handoff['execution_handle']]))
        adapter = self._adapter(context.assignment)
        return await adapter.execute(context, tool_name, arguments, operation_key)

    def fact_sources(self, role):
        values = {'execution_handoff': {'type': ['object', 'null'],
            'meaning': 'The latest original usable received or own selected check when exactly one physical execution is known; null for zero or several identities. No new receiving check occurs at closure.',
            'report_schema': {**_nullable(HANDOFF_SCHEMA), 'x-source': 'execution_handoff'}},
            'execution_handoffs': {'type': 'array',
            'meaning': 'For each distinct registry and execution handle, the available usable check with latest original checked_at, in identity order. This records available facts without selecting a resource or rechecking it.',
            'report_schema': {**_array(HANDOFF_SCHEMA), 'x-source': 'execution_handoffs'}}}
        for adapter in self.adapters.values():
            for name, definition in adapter.fact_sources(role).items():
                if name in values and values[name] != definition:
                    raise ValueError('resource_fact_definition_conflict:' + name)
                values[name] = definition
        return values

    def facts(self, context, completion_snapshot):
        values = {'execution_handoff': None, 'execution_handoffs': []}
        adapters = self._context_adapters(context)
        for adapter in adapters:
            facts = adapter.facts(context, completion_snapshot)
            for key, value in facts.items():
                if key == 'execution_handoffs':
                    values[key].extend(value)
                    continue
                if key == 'execution_handoff':
                    continue
                if value is not None:
                    values[key] = value
                else:
                    values.setdefault(key, None)
        identities = {(item['resource_selection']['capability_binding_ref'], item['execution_handle']): item
            for item in values['execution_handoffs']}
        values['execution_handoffs'] = [identities[key] for key in sorted(identities)]
        values['execution_handoff'] = values['execution_handoffs'][0] if len(identities) == 1 else None
        return values

    def received_form_references(self, context, form, schema, operation_key):
        references = []
        def visit(value, declared):
            source = declared.get('x-source')
            if source in {'execution_handoff', 'execution_handoffs'}:
                values = value if source == 'execution_handoffs' else ([] if value is None else [value])
                for handoff in values:
                    adapter = self._adapter({'version': RESULTS_VERSION, 'handoff': handoff})
                    callback = getattr(adapter, 'received_form_references', None)
                    if callback is None:
                        raise ValueError('resource_information_handoff_proof_missing')
                    references.extend(callback(context, handoff, {'x-source': 'execution_handoff'}, operation_key))
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
        if context.role != 'results':
            return []
        callback = getattr(self._adapter(context.assignment), 'initial_references', None)
        return [] if callback is None else callback(context)

    def resolve(self, context, reference, namespace):
        if reference_in_context(self.services, context, reference, namespace):
            return True
        return any(adapter.resolve(context, reference, namespace)
            for adapter in self._context_adapters(context))

    def validate_report(self, context, form, original_schema):
        for adapter in self._context_adapters(context):
            adapter.validate_report(context, form, original_schema)
        facts = self.facts(context, {})
        def visit(value, schema):
            if schema.get('x-source') in {'execution_handoff', 'execution_handoffs'}:
                if plain(value) != facts[schema['x-source']]:
                    raise ReportBoundaryError('Resource handoff differs from selected recorded check',
                        code='resource_handoff_fact_mismatch')
            elif isinstance(value, Mapping):
                for key, child in value.items():
                    if key in schema.get('properties', {}):
                        visit(child, schema['properties'][key])
            elif isinstance(value, (list, tuple)) and 'items' in schema:
                for child in value:
                    visit(child, schema['items'])
        visit(form, original_schema)

    def credit_view(self, context, receiver_selection):
        # Caller owns the projection; adding a role supplies no new weights.
        return self.services.bound_role_credit(context, receiver_selection)


class _Message:
    def __init__(self, value):
        self.value = value

    def as_record(self):
        return deepcopy(self.value)


class HomologyResourceAdapter:
    """C9 wrapper around existing HomologyEpisodes ordinary operations.

    Physical resource_id comes from the caller's statistics binding when one
    exists. Without it the registry supplies a logical identity only, without
    claiming a particular machine. capability_binding_ref is always the actual
    immutable execution registry identity.
    """
    def __init__(self, homology_episodes, store, journal, resource_estimator=None):
        if type(homology_episodes) is not HomologyEpisodes:
            raise TypeError('explicit_homology_episode_binding_required')
        self.homology = homology_episodes
        self.store, self.journal = store, journal
        self.information = ResourceInformation(store, run_id=journal.run_id, jobs=homology_episodes.jobs)
        self.resource_estimator = resource_estimator
        statistics = homology_episodes.statistics
        self.resource_id = (statistics.resource_id if statistics is not None
            else 'registry-local:' + homology_episodes.jobs.config['registry_ref'])
        provider = getattr(homology_episodes, 'native_event_provider', None)
        if provider is not None and provider.resource_id != self.resource_id:
            raise ValueError('native_event_resource_binding_mismatch')
        self.record_selection = None

    def bind_record_selection(self, callback):
        self.record_selection = callback

    def as_record(self):
        return {'version': 'homology_resource_adapter_v1', 'resource_id': self.resource_id,
            'resource_identity_kind': 'physical_binding' if self.homology.statistics else 'logical_registry',
            'homology': self.homology.as_record(),
            'resource_estimator': None if self.resource_estimator is None else self.resource_estimator.as_record()}

    def capability(self):
        jobs = self.homology.jobs
        files = (jobs.config['executable']['path'], jobs.config['reference_database']['path'])
        availability = 'unavailable'
        if all(Path(path).is_file() for path in files) and os.access(files[0], os.X_OK):
            try:
                probe = subprocess.run(['systemctl', '--user', 'show-environment'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False)
                availability = 'available' if probe.returncode == 0 else 'unavailable'
            except (OSError, subprocess.SubprocessError):
                availability = 'unknown'
        return {'resource_id': self.resource_id, 'kind': 'local', 'availability': availability,
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'provenance_refs': [jobs.config['registry_ref']], 'knowledge_entry_ids': [],
            'tool_names': [tool['name'] for tool in self.homology.catalog(
                SimpleNamespace(path=(('job_launch', self.resource_id),)))]}

    def _selection(self, cpu):
        policy = self.homology.jobs.config['job_limits']
        return {'resource_id': self.resource_id, 'kind': 'local',
            'allocation': {'cpu': cpu, **deepcopy(policy)},
            'capability_binding_ref': self.homology.jobs.config['registry_ref']}

    def _verify_selection(self, selected, cpu):
        if selected != self._selection(cpu):
            raise ValueError('resource_selection_conflict')

    def prepare_assignment(self, context, role, launch_assignment, scope, operation_key):
        value = plain(launch_assignment)
        if role == 'results':
            self._selector(value['requested_data_selector'])
            handoff = value['handoff']
            legacy = self._native_handoff(handoff)
            job = self.homology.jobs._row(legacy['job_ref'])
            self.homology._query(self.store, plain(scope), job['query_ref'])
            assigned = {'job_ref': job['job_ref'], 'query_ref': job['query_ref'],
                'cpu': job['cpu'], 'handoff': legacy}
            if 'search_modes' in self.homology.jobs.config:
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
            row = self.homology.jobs._row(job['existing_job_ref'])
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
        self.homology._query(self.store, plain(scope), query)
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
        value['adapter_assignment'] = self.homology.assign(self.store, 'job_launch', job,
            plain(scope), operation_key=operation_key)
        return value

    def _legacy(self, context):
        if not self._owns_context(context):
            return None
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

    def _owns_context(self, context):
        assignment = plain(context.assignment)
        selection = (assignment.get('handoff', {}).get('resource_selection')
            if context.role == 'results' else assignment.get('resource_selection'))
        if selection is not None:
            return (selection.get('resource_id') == self.resource_id
                and selection.get('kind') == 'local'
                and selection.get('capability_binding_ref') == self.homology.jobs.config['registry_ref'])
        job = assignment.get('job_request', {})
        return (isinstance(job, dict) and 'provider' not in job
            and (set(job) <= {'query_ref', 'cpu', 'search_mode', 'existing_job_ref'})
            and ('existing_job_ref' in job or 'query_ref' in job and 'cpu' in job))

    def catalog(self, context):
        source = self._legacy(context)
        return [] if source is None else self.homology.catalog(source)

    async def execute(self, context, tool_name, arguments, operation_key):
        replay = self.information.selected_handoff(context, tool_name, arguments, operation_key)
        if replay is not None:
            return replay
        source = self._legacy(context)
        if source is None:
            return _outcome(failure=_failure('resource_assignment_conflict'))
        assignment = self.homology.assignment(source)
        try:
            self._verify_selection(plain(context.assignment)['resource_selection']
                if context.role != 'results' else plain(context.assignment)['handoff']['resource_selection'],
                assignment['cpu'])
            row = self.homology.jobs._row(assignment['job_ref'])
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
        outcome = await self.homology.execute(source, tool_name, plain(arguments), operation_key=operation_key)
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
        job = self.homology.jobs._row(checked['handoff']['job_ref'])
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
        jobs = self.homology.jobs
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
            job = self.homology.jobs._row(handoff['execution_handle'])
            selection = handoff['resource_selection']
            if (assignment['resource_selection'] is not None
                    and selection != assignment['resource_selection']
                    or not ResourceEpisodes._permitted(assignment, selection)):
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
        checked = self.homology.jobs.check_handoff(native)
        value = self._wrap(context, checked)
        outcome = {**_outcome(checked), 'execution_handoff': value}
        return self.information.publish_handoff(context, 'resource.check_handoff',
            {'handoff': handoff}, outcome, operation_key)

    def execution_handoff(self, context):
        values = self.execution_handoffs(context)
        return values[0] if len(values) == 1 else None

    def execution_handoffs(self, context):
        if not self._owns_context(context):
            return []
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
                if body.get('registry_ref') != self.homology.jobs.config['registry_ref']:
                    continue
                body = self.information.read_handoff_source(reference, scope=plain(context.scope))
                self.information._validate_assignment(context, body['execution_handoff'], body['job'])
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
        values = self.homology.fact_sources('job_results' if role == 'results' else 'job_launch') if role != 'launch' else {}
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
            assignment = self.homology.assignment(source)
            native = self._native_handoff(handoff) if handoff is not None else assignment.get('handoff')
            facts = {'job_ref': assignment['job_ref'], 'job_cpu': assignment['cpu'],
                'job_handoff': native, 'job_handoff_state': 'usable' if native is not None else 'unavailable',
                'job_handoff_failure': None if native is not None else 'receiving_interface_unavailable',
                'job_sample': self.homology.latest_sample(source),
                'resource_tool_estimates': recorded_forecasts(self.store,
                    run_id=context.run_id, episode_id=context.episode_id)}
            if 'search_modes' in self.homology.jobs.config:
                facts['job_search_mode'] = assignment['search_mode']
            legacy_role = source.path[-1][0]
            if legacy_role == 'job_launch':
                facts['job_checked_status'] = self.homology.latest_checked_status(source)
            if self.homology.has_information_channel(legacy_role):
                information = self.homology.credit_view(source)
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
                                'registry_ref': self.homology.jobs.config['registry_ref']})
                        facts['job_result_progress'] = _result_progress(coverage)
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
        if not self._owns_context(context):
            return False
        source = self._legacy(context)
        assignment = self.homology.assignment(source) if source else None
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
        return self.homology.resolve(self.store, plain(context.scope), reference, namespace, assignment=assignment)

    def validate_report(self, context, form, original_schema):
        if not self._owns_context(context):
            return
        source = self._legacy(context)
        if source is not None:
            self.homology.validate_report(form, self.homology.assignment(source),
                store=self.store, schema=plain(original_schema))

    def credit_view(self, context, receiver_selection):
        source = self._legacy(context)
        if source is None:
            raise ValueError('explicit_role_credit_binding_required:' + context.role)
        return self.homology.credit_view(source)

    def decision_context(self, context):
        if not self._owns_context(context):
            return {'resource_tool_estimates': []}
        statistics = self.homology.statistics
        if statistics is None or self.resource_estimator is None:
            return {'resource_tool_estimates': []}
        from .execution_expectations import capture_execution_scopes
        source = self._legacy(context)
        if source is not None:
            assignment = self.homology.assignment(source)
            execution_class = statistics.execution_class(self.homology.jobs,
                self.homology.jobs._row(assignment['job_ref']))
            captured = capture_execution_scopes(statistics.history_path, [execution_class],
                assigned_execution_class_ref=execution_class.ref)
            estimates = self.resource_estimator.estimate(captured,
                job_ref=assignment['job_ref'], sample=self.homology.latest_sample(source))
        else:
            # The launch episode knows its parent's exact work before choosing
            # a resource. No order/staging/dispatch is needed for this forecast.
            job = plain(context.assignment).get('job_request', {})
            if 'existing_job_ref' in job:
                row = self.homology.jobs._row(job['existing_job_ref'])
                self.homology._query(self.store, plain(context.scope), row['query_ref'])
                execution_class = statistics.execution_class(self.homology.jobs, row)
                captured = capture_execution_scopes(statistics.history_path, [execution_class],
                    assigned_execution_class_ref=execution_class.ref)
                return {'resource_tool_estimates': self.resource_estimator.estimate(captured,
                    job_ref=row['job_ref'])}
            if 'query_ref' not in job or 'cpu' not in job:
                return {'resource_tool_estimates': []}
            from .materials import artifact_path
            query = self.homology._query(self.store, plain(context.scope), job['query_ref'])
            sequence = artifact_path(self.store, query['sequence_ref']).read_text()
            execution_class = statistics.execution_class_for_query(self.homology.jobs,
                query_fasta='>query\n' + sequence + '\n', cpu=job['cpu'],
                search_mode=job.get('search_mode', 'native_defaults'))
            captured = capture_execution_scopes(statistics.history_path, [execution_class])
            estimates = self.resource_estimator.estimate_context(captured)
        return {'resource_tool_estimates': estimates}


__all__ = ['ResourceEpisodes', 'HomologyResourceAdapter', 'LAUNCH_VERSION', 'RESULTS_VERSION',
    'LAUNCH_SCHEMA', 'RESULTS_SCHEMA', 'HANDOFF_SCHEMA', 'SELECTION_SCHEMA', 'CAPABILITY_SCHEMA']
