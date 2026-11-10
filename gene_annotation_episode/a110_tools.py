"""A110 tools; native accounting uses the existing shared HPC owner."""
from .component_axis_native_tools import ComponentNativeHPCMixin
from .tools import ToolRegistry


class A110ToolRegistry(ComponentNativeHPCMixin, ToolRegistry):
    COMPONENT_NATIVE_AXES = ('A110',)

    def __init__(self, *args, a110_flux_balance_bindings=(), **kwargs):
        from .a110_fba_hpc import normalize
        self.a110_flux_balance_bindings = normalize(a110_flux_balance_bindings)
        super().__init__(*args, **kwargs)

    def operation_resource_limits(self):
        result = super().operation_resource_limits()
        from .component_source_identity import TOOLS
        from .a110_reference_accounting import TOOL as PANEL_TOOL
        result['component_native_metadata']['tool_names'].extend([TOOLS['A110'], PANEL_TOOL])
        return result

    def catalog(self, scope=None):
        from .a110_reference_accounting import catalog
        entries = super().catalog(scope=scope)
        extra = catalog()
        if set(entries) & set(extra):
            raise ValueError('a110_reference_accounting_operation_owner_conflict')
        return {**entries, **extra}

    def received_attributions(self, context, known):
        inherited = getattr(super(), 'received_attributions', None)
        generated, needs = inherited(context, known) if callable(inherited) else ([], [])
        if context.role not in {'annotation', 'scientific_process', 'improvement'} or (
                context.role == 'scientific_process' and context.assignment.get('selection', {}).get(
                    'evidence_axis', {}).get('option_id') != 'A110'):
            return generated, needs
        from .a110_reference_accounting import refresh
        more, pending = refresh(self.store, context, set(known) | set(generated))
        return list(dict.fromkeys([*generated, *more])), [*needs, *pending]

    async def execute_async(self, name, args, *, scope=None, operation_key=None, permitted_record_refs=None):
        from .component_axis_source_access import source_received_inputs
        permitted_record_refs = source_received_inputs(self, name, args, scope,
            operation_key, permitted_record_refs)
        from .component_source_identity import TOOLS
        from . import a110_reference_accounting as panels
        if name not in {TOOLS['A110'], panels.TOOL}:
            return await super().execute_async(name, args, scope=scope,
                operation_key=operation_key, permitted_record_refs=permitted_record_refs)
        from .a110_qualification import VERSION, catalog, source_identity_request, refresh
        from .communication import plain
        from .domain import canonical, validate_schema
        from .episode_return_records import EpisodeReturnRecords
        from .component_axis_native_hpc import require
        import json
        preparing_panel = name == panels.TOOL
        contracts = panels.catalog() if preparing_panel else catalog()
        create = panels.request if preparing_panel else source_identity_request
        update = panels.refresh if preparing_panel else refresh
        version = panels.VERSION if preparing_panel else VERSION
        prefix = 'a110_reference_accounting' if preparing_panel else 'a110_source_identity'
        try:
            validate_schema(args, contracts[name]['input_schema'])
            invocation = self._current_invocation.get()
            require(invocation is not None and invocation[2:] == (name, args, operation_key),
                prefix + '_original_action_required')
            context = invocation[0]
            EpisodeReturnRecords(self.store, context.run_id, failure_prefix='a110_').authenticate(context)
            require(self.store.validate_scope(scope) == plain(context.scope),
                prefix + '_original_scope_required')
            require(context.role != 'scientific_process' or context.assignment.get('selection', {}).get(
                'evidence_axis', {}).get('option_id') == 'A110', 'a110_original_scientific_axis_required')
            known = set(context.received_record_refs if permitted_record_refs is None else permitted_record_refs)
            require(known <= set(context.received_record_refs), 'a110_explicit_received_inputs_required')
            signature = canonical({'run_id': context.run_id, 'episode_id': context.episode_id,
                'operation': name, 'arguments': args, 'scope': plain(context.scope), 'version': version})
            saved = self.store.db.execute('SELECT * FROM component_native_actions WHERE operation_key=?',
                (operation_key,)).fetchone()
            if saved is not None:
                require(saved['request'] == signature, prefix + '_operation_conflict')
                return json.loads(saved['result'])
            with self.store.transaction():
                reference = create(self.store, args, context=context, known=known)
                generated, _ = update(self.store, context, known | {reference})
                preparations = ([body for body in panels.received(self.store,
                    known | {reference, *generated}, context.scope)
                    if body['request_ref'] == reference and body['current']] if preparing_panel else [])
                details = ({'preparation_results': preparations}
                    if preparing_panel else {'qualification_refs': generated})
                result = {'status': 'completed', 'record_refs': list(dict.fromkeys([
                    reference, *generated, *[body['source_ref'] for body in preparations]])),
                    'changed_record_refs': [], 'feedback': None, 'result': {'request_ref': reference,
                        **details, 'native_execution_requested': False, 'scientific_credit': None}}
                self.store.db.execute('INSERT INTO component_native_actions VALUES(?,?,?)',
                    (operation_key, signature, canonical(result)))
            return result
        except (ValueError, KeyError, TypeError) as error:
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'code': str(error)}}
