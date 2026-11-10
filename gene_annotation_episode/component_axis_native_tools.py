"""Registry composition for shared-HPC A107/A110 component requests."""
from copy import deepcopy
import json

from .communication import plain
from .domain import ContractError, canonical, validate_schema
from .episode_return_records import EpisodeReturnRecords
from .component_axis_native_contracts import VERSION, OPERATIONS, tool_catalog
from .component_axis_native_hpc import (MAX_INPUT_BYTES, RESULT_PROVIDER,
    STATUS_PROVIDER, require, freeze, commission, read, receive, publish, sha)


class ComponentNativeHPCMixin:
    COMPONENT_NATIVE_AXES = ()

    def __init__(self, *args, **kwargs):
        self.component_native_resources = None
        super().__init__(*args, **kwargs)
        self.store.db.execute('CREATE TABLE IF NOT EXISTS component_native_actions '
            '(operation_key TEXT PRIMARY KEY,request TEXT NOT NULL,result TEXT NOT NULL)')

    def configure_component_native_hpc(self, resources):
        resources = plain(resources)
        require(any(row.get('kind') == 'pbs_ssh' for row in resources.values()), 'configured_hpc_resource_required')
        require(self.component_native_resources is None or self.component_native_resources == resources,
            'hpc_resource_configuration_changed')
        for binding in getattr(self, 'a110_flux_balance_bindings', ()):
            require(binding['resource_id'] in resources and resources[binding['resource_id']].get('kind') == 'pbs_ssh',
                'remote_fba_resource_not_configured')
        for binding in getattr(self, 'a107_detection_bindings', ()):
            require(binding['resource_id'] in resources and resources[binding['resource_id']].get('kind') == 'pbs_ssh',
                'a107_detector_resource_not_configured')
        self.component_native_resources = deepcopy(resources)

    def component_native_catalog(self):
        if self.component_native_resources is None:
            return {}
        entries = {}
        resource_ids = sorted(name for name, resource in self.component_native_resources.items()
            if resource.get('kind') == 'pbs_ssh')
        for axis in self.COMPONENT_NATIVE_AXES:
            contracts = tool_catalog(axis)
            for contract in contracts.values():
                resource = contract['input_schema']['properties']['resource_id']
                resource.update(enum=resource_ids, description=
                    'Choose a configured remote PBS resource ID from this enum. '
                    'A local host observation ID does not identify an HPC resource. '
                    'The tool resource label local describes request preparation; '
                    'the scientific calculation executes on the selected remote resource.')
            entries.update(contracts)
        if 'A110' in self.COMPONENT_NATIVE_AXES:
            from .a110_fba_hpc import catalog
            entries.update(catalog(getattr(self, 'a110_flux_balance_bindings', ())))
        if 'A107' in self.COMPONENT_NATIVE_AXES:
            from .a107_genomic_detection_hpc import catalog
            entries.update(catalog(getattr(self, 'a107_detection_bindings', ())))
        return entries

    def catalog(self, scope=None):
        entries = super().catalog(scope=scope)
        extra = self.component_native_catalog()
        if 'A110' in self.COMPONENT_NATIVE_AXES:
            from .a110_qualification import catalog
            extra.update(catalog())
        # This new registry offers no local heavy FBA fallback. Preserve the
        # original backend and its configuration for historical workflows.
        if 'perform_flux_balance_analysis' in entries:
            stored = [row for row in entries['perform_flux_balance_analysis']['input_schema'].get('oneOf', [])
                if row.get('properties', {}).get('mode', {}).get('const') == 'read_stored']
            if stored:
                entries['perform_flux_balance_analysis'] = {**entries['perform_flux_balance_analysis'],
                    'description': 'Read only actually received retained FBA output; this registry runs no local native FBA.',
                    'instructions': 'Read the selected original FBA publication through its existing '
                        'receipt-controlled stored-result view. Keep its model, software, conditions, '
                        'native quantities and limitations. Select only the actually received output '
                        'subset. New native FBA work uses the available chemistry.request_flux_balance_hpc '
                        'operation with a configured remote deployment. This contract performs only '
                        'read_stored and never launches or recalculates FBA.',
                    'input_schema': {'oneOf': stored}}
            else:
                entries.pop('perform_flux_balance_analysis')
        require(not set(entries).intersection(extra), 'operation_owner_conflict')
        return {**entries, **extra}

    def restrict_resource_tool_catalogs(self, catalogs):
        """Keep execution metadata from restoring a disabled scientific tool.

        The shared execution service remains unchanged. This axis's frozen
        scientific map must describe its actual registry, including a direct
        stored-result FBA view when that original backend is configured.
        """
        actual = self.catalog()
        result = {}
        for kind, entries in plain(catalogs or {}).items():
            if isinstance(entries, dict):
                rows = [{'name': name, **entry} for name, entry in entries.items()]
            else:
                rows = list(entries)
            kept = []
            for row in rows:
                if row['name'] != 'perform_flux_balance_analysis':
                    kept.append(deepcopy(row))
                    continue
                stored = actual.get(row['name'])
                if kind == 'local' and stored is not None:
                    kept.append({'name': row['name'], **deepcopy(stored)})
            result[kind] = kept
        return result

    def as_record(self):
        return {**super().as_record(), 'component_native_tools': {'version': VERSION,
            'axes': list(self.COMPONENT_NATIVE_AXES), 'hpc_resources': deepcopy(self.component_native_resources),
            'remote_fba_bindings': deepcopy(getattr(self, 'a110_flux_balance_bindings', ())),
            'execution': 'frozen_inputs_to_shared_hpc; no_local_native_fallback'}}

    def operation_resource_limits(self):
        parent = getattr(super(), 'operation_resource_limits', lambda: {})()
        names = list(self.component_native_catalog())
        if 'A110' in self.COMPONENT_NATIVE_AXES:
            names.extend(('chemistry.reaction_evidence', 'chemistry.experimental_reaction_evidence'))
        return {**parent, 'component_native_metadata': {'tool_names': names, 'cpu_threads': 1, 'native_jobs': 0,
            'max_input_transfer_bytes': MAX_INPUT_BYTES,
            'oversize_behavior': 'explicit_missing_large_file_staging_capability; no_silent_truncation'}}

    def received_hpc_attributions(self, context, known, *, hpc_result_reader):
        parent = getattr(super(), 'received_hpc_attributions', None)
        generated, needs = parent(context, known, hpc_result_reader=hpc_result_reader) if callable(parent) else ([], [])
        if context.role == 'scientific_process' and context.assignment.get('selection', {}).get(
                'evidence_axis', {}).get('option_id') not in self.COMPONENT_NATIVE_AXES:
            return generated, needs
        more, pending = receive(self, context, set(known) | set(generated), reader=hpc_result_reader)
        return [*generated, *more], [*needs, *pending]

    async def execute_async(self, name, args, *, scope=None, operation_key=None, permitted_record_refs=None):
        if name == 'perform_flux_balance_analysis' and args.get('mode') != 'read_stored':
            return {'status': 'unavailable', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'code': 'component_axis_local_native_fba_disabled',
                    'request_tool': 'chemistry.request_flux_balance_hpc',
                    'configured': bool(getattr(self, 'a110_flux_balance_bindings', ()))}}
        if name == 'chemistry.reaction_evidence' and 'A110' in self.COMPONENT_NATIVE_AXES:
            return self._chemical_qualification(args, scope=scope, operation_key=operation_key,
                permitted_record_refs=permitted_record_refs)
        if name == 'chemistry.experimental_reaction_evidence' and 'A110' in self.COMPONENT_NATIVE_AXES:
            return self._experimental_chemical_qualification(args, scope=scope, operation_key=operation_key,
                permitted_record_refs=permitted_record_refs)
        axes = {OPERATIONS[axis]: axis for axis in self.COMPONENT_NATIVE_AXES}
        if 'A110' in self.COMPONENT_NATIVE_AXES:
            axes['chemistry.request_flux_balance_hpc'] = 'A110'
        if 'A107' in self.COMPONENT_NATIVE_AXES:
            axes['partner.request_detection_hpc'] = 'A107'
        if name not in axes:
            return await super().execute_async(name, args, scope=scope, operation_key=operation_key,
                permitted_record_refs=permitted_record_refs)
        try:
            axis = axes[name]
            contracts = self.component_native_catalog()
            require(name in contracts, 'native_operation_not_configured')
            validate_schema(args, contracts[name]['input_schema'])
            invocation = self._current_invocation.get()
            require(invocation is not None and invocation[2:] == (name, args, operation_key),
                'original_action_binding_required')
            context = invocation[0]
            EpisodeReturnRecords(self.store, context.run_id, failure_prefix='component_native_').authenticate(context)
            require(self.store.validate_scope(scope) == plain(context.scope), 'original_action_scope_required')
            require(context.role != 'scientific_process' or context.assignment.get('selection', {}).get(
                'evidence_axis', {}).get('option_id') == axis, 'original_scientific_axis_required')
            known = set(context.received_record_refs if permitted_record_refs is None else permitted_record_refs)
            require(known <= set(context.received_record_refs), 'explicit_received_inputs_required')
            resources = self.component_native_resources
            require(resources is not None and args['resource_id'] in resources
                and resources[args['resource_id']].get('kind') == 'pbs_ssh', 'configured_hpc_resource_required')
            signature = canonical({'run_id': context.run_id, 'episode_id': context.episode_id,
                'operation': name, 'arguments': args, 'scope': plain(context.scope), 'version': VERSION})
            saved = self.store.db.execute('SELECT * FROM component_native_actions WHERE operation_key=?',
                (operation_key,)).fetchone()
            if saved is not None:
                require(saved['request'] == signature, 'operation_identity_conflict')
                return json.loads(saved['result'])
            with self.store.transaction():
                request_ref, body = freeze(self, axis, args, context=context, known=known, invocation=invocation)
                retained = [(ref, row) for ref in sorted(known)
                    if (row := read(self.store, ref, RESULT_PROVIDER)) is not None
                    and row['axis'] == axis and row['logical_work_sha256'] == body['logical_work_sha256']
                    and self.store.scope_contains(plain(context.scope), row['scope'])]
                if retained:
                    records = [request_ref, *[ref for ref, _ in retained]]
                    result = {'request_ref': request_ref, 'execution_status': 'qualified_components_already_received',
                        'new_execution_requested': False, 'scientific_credit': None}
                else:
                    from .hpc_commission_sources import publish as publish_commission
                    work = commission(body, resources)
                    commission_ref = publish_commission(self.store, work, scope=plain(context.scope), resources=resources)
                    records = [request_ref, commission_ref]
                    result = {'request_ref': request_ref, 'commission_source_ref': commission_ref,
                        'hpc_assignment': {'commission_source_ref': commission_ref},
                        'execution_owner': 'shared_hpc_parent_with_prediction_and_execution_sisters',
                        'new_execution_requested': True, 'scientific_credit': None}
                outcome = {'status': 'completed', 'record_refs': records, 'changed_record_refs': [],
                    'feedback': None, 'result': result}
                self.store.db.execute('INSERT INTO component_native_actions VALUES(?,?,?)',
                    (operation_key, signature, canonical(outcome)))
            return outcome
        except (ValueError, KeyError, OSError, TypeError) as error:
            if isinstance(error, ContractError) and error.detail.get('input_admission'):
                with self.store.transaction():
                    reference = publish(self.store, STATUS_PROVIDER, {'version': VERSION,
                        'axis': axis, 'scope': plain(context.scope), 'run_id': context.run_id, 'operation': name,
                        'target_ref': next(iter({row['target_ref'] for row in self.store.coverage(args['target_ref'])})),
                        'request_ref': None, 'hpc_result_ref': None, 'status': 'input_admission_unavailable',
                        'arguments_sha256': sha(canonical(args).encode()),
                        'witness_ref': error.detail['witness_ref'], 'required_artifact_ref': error.detail['required_artifact_ref'],
                        'failure': error.detail['failure'], 'scientific_credit': None})
                return {'status': 'unavailable', 'record_refs': [reference], 'changed_record_refs': [],
                    'result': None, 'feedback': {'code': str(error), 'detail': error.detail}}
            feedback = {'code': str(error)}
            if (isinstance(error, ContractError)
                    and str(error) == 'component_native_input_contract_mismatch'):
                feedback['detail'] = error.detail
            if str(error) == 'component_native_configured_hpc_resource_required':
                feedback.update(configured_hpc_resource_ids=sorted(name for name, resource in
                    (self.component_native_resources or {}).items() if resource.get('kind') == 'pbs_ssh'),
                    recovery='Select a configured remote PBS resource ID. Host observation IDs '
                        'and the preparation tool resource label local are different identifiers. '
                        'This rejection created no scientific result or job.')
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': feedback}

    def received_attributions(self, context, known):
        # Receipt-time native grading is handled above. Keeping this callback
        # present permits the existing runtime to reach the shared HPC hook.
        parent = getattr(super(), 'received_attributions', None)
        generated, needs = parent(context, known) if callable(parent) else ([], [])
        if 'A110' not in self.COMPONENT_NATIVE_AXES or context.role not in {
                'annotation', 'scientific_process', 'improvement'} or context.role == 'scientific_process' and (
                context.assignment.get('selection', {}).get('evidence_axis', {}).get('option_id') != 'A110'):
            return generated, needs
        from .a110_qualification import refresh
        more, pending = refresh(self.store, context, set(known) | set(generated))
        return [*generated, *more], [*needs, *pending]

    def _chemical_qualification(self, args, *, scope, operation_key, permitted_record_refs):
        from .a110_qualification import TOOL, VERSION as PROFILE, request, refresh, catalog
        try:
            validate_schema(args, catalog()[TOOL]['input_schema'])
            invocation = self._current_invocation.get()
            require(invocation is not None and invocation[2:] == (TOOL, args, operation_key),
                'a110_original_qualification_action_required')
            context = invocation[0]
            EpisodeReturnRecords(self.store, context.run_id, failure_prefix='a110_').authenticate(context)
            require(self.store.validate_scope(scope) == plain(context.scope), 'a110_original_qualification_scope_required')
            require(context.role != 'scientific_process' or context.assignment.get('selection', {}).get(
                'evidence_axis', {}).get('option_id') == 'A110', 'a110_original_scientific_axis_required')
            known = set(context.received_record_refs if permitted_record_refs is None else permitted_record_refs)
            require(known <= set(context.received_record_refs), 'a110_explicit_received_inputs_required')
            signature = canonical({'run_id': context.run_id, 'episode_id': context.episode_id,
                'operation': TOOL, 'arguments': args, 'scope': plain(context.scope), 'version': PROFILE})
            saved = self.store.db.execute('SELECT * FROM component_native_actions WHERE operation_key=?',
                (operation_key,)).fetchone()
            if saved is not None:
                require(saved['request'] == signature, 'a110_qualification_operation_identity_conflict')
                return json.loads(saved['result'])
            with self.store.transaction():
                reference = request(self.store, args, context=context, known=known)
                generated, _ = refresh(self.store, context, known | {reference})
                result = {'status': 'completed', 'record_refs': [reference, *generated],
                    'changed_record_refs': [], 'feedback': None, 'result': {'request_ref': reference,
                        'qualification_refs': generated, 'native_execution_requested': False, 'scientific_credit': None}}
                self.store.db.execute('INSERT INTO component_native_actions VALUES(?,?,?)',
                    (operation_key, signature, canonical(result)))
            return result
        except (ValueError, KeyError, TypeError) as error:
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'code': str(error)}}

    def _experimental_chemical_qualification(self, args, *, scope, operation_key, permitted_record_refs):
        from .a110_experimental_qualification import TOOL, VERSION as PROFILE, request, catalog
        from .a110_qualification import refresh
        try:
            validate_schema(args, catalog()[TOOL]['input_schema'])
            invocation = self._current_invocation.get()
            require(invocation is not None and invocation[2:] == (TOOL, args, operation_key),
                'a110_original_experimental_qualification_action_required')
            context = invocation[0]
            EpisodeReturnRecords(self.store, context.run_id, failure_prefix='a110_').authenticate(context)
            require(self.store.validate_scope(scope) == plain(context.scope),
                'a110_original_experimental_qualification_scope_required')
            require(context.role != 'scientific_process' or context.assignment.get('selection', {}).get(
                'evidence_axis', {}).get('option_id') == 'A110', 'a110_original_scientific_axis_required')
            known = set(context.received_record_refs if permitted_record_refs is None else permitted_record_refs)
            require(known <= set(context.received_record_refs), 'a110_explicit_received_inputs_required')
            signature = canonical({'run_id': context.run_id, 'episode_id': context.episode_id,
                'operation': TOOL, 'arguments': args, 'scope': plain(context.scope), 'version': PROFILE})
            saved = self.store.db.execute('SELECT * FROM component_native_actions WHERE operation_key=?',
                (operation_key,)).fetchone()
            if saved is not None:
                require(saved['request'] == signature, 'a110_experimental_qualification_operation_identity_conflict')
                return json.loads(saved['result'])
            with self.store.transaction():
                reference = request(self.store, args, context=context, known=known)
                generated, _ = refresh(self.store, context, known | {reference})
                result = {'status': 'completed', 'record_refs': [reference, *generated],
                    'changed_record_refs': [], 'feedback': None, 'result': {'request_ref': reference,
                        'qualification_refs': generated, 'native_execution_requested': False, 'scientific_credit': None}}
                self.store.db.execute('INSERT INTO component_native_actions VALUES(?,?,?)',
                    (operation_key, signature, canonical(result)))
            return result
        except (ValueError, KeyError, TypeError) as error:
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'code': str(error)}}
