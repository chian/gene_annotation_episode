"""Synchronous updates of saved literature-sheet dependencies.

A scientific population owns its interpretation and calculation.  This module
only retains the calculation's existing input bindings, follows an input's
current version and reruns dependent calculations.  It never creates a decision
or a credit event and never acquires an unreturned child component.
"""
from copy import deepcopy
from dataclasses import replace
from functools import wraps
from episode_runtime import TableDeclaration
from importlib import import_module
import inspect
import json
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import canonical, identity
from gene_annotation_episode.domain import ContractError
VERSION = 'literature_sheet_dependencies_v1'
DEPENDENCIES = TableDeclaration(name='literature_sheet_dependencies', columns=('sheet_ref', 'family', 'provider', 'adapter', 'method', 'arguments', 'assignment', 'possessed', 'dependencies', 'receipt'), key=('sheet_ref',), record_refs=('sheet_ref',))
CURRENT_SHEETS = TableDeclaration(name='literature_current_scoring_sheets', columns=('family', 'sheet_ref', 'status', 'detail'), key=('family',), record_refs=('sheet_ref',))

def _policy_for(provider):
    """Resolve A105's private scientific use policy."""
    if provider.startswith('literature.a105.'):
        from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_sheet_policy
    else:
        return None
    return literature_sheet_policy

def _supported(repository):
    return repository.provider.startswith('literature.a105.')

def _refs(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == 'sheet_ref' and isinstance(child, str):
                yield child
            else:
                yield from _refs(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _refs(child)

def _replace_refs(value, replacements):
    if isinstance(value, dict):
        return {key: _replace_refs(child, replacements) for key, child in value.items()}
    if isinstance(value, list):
        return [_replace_refs(child, replacements) for child in value]
    return replacements.get(value, value) if isinstance(value, str) else value

def _measurement_keys(value):
    found = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {'measurement_keys', 'physical_estimate_keys'} and isinstance(child, list):
                found.update((item for item in child if isinstance(item, str)))
            elif key in {'measurement_key', 'physical_measurement_key', 'physical_estimate_key', 'estimate_key'} and isinstance(child, str):
                found.add(child)
            else:
                found.update(_measurement_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_measurement_keys(child))
    return sorted(found)

def _family(repository, arguments, saved, dependency_families):
    provider = repository.provider
    policy = _policy_for(provider)
    use = policy.family_use(provider, arguments, saved, dependency_families, _measurement_keys, _replace_refs) if policy is not None else None
    if use is None:
        use = _replace_refs(arguments, dependency_families)
    return identity('literature_scientific_sheet_use', {'provider': provider, 'use': use})

def _rows(store, context):
    own = {'run_id': context.run_id, 'episode_id': context.episode_id}
    current = {row['family']: row for row in store.table(CURRENT_SHEETS).select(own)}
    rows = []
    for row in store.table(DEPENDENCIES).select(own):
        if row['provider'].startswith('literature.a105.'):
            saved = current.get(row['family'])
            rows.append({**row, 'current_ref': saved['sheet_ref'] if saved else None, 'current_status': saved['status'] if saved else None, 'current_detail': saved['detail'] if saved else None})
    return rows

def _mark_unavailable(store, context, family, detail):
    row = store.table(CURRENT_SHEETS).select({'run_id': context.run_id, 'episode_id': context.episode_id, 'family': family})[0]
    store.table(CURRENT_SHEETS).put({'family': family, 'sheet_ref': row['sheet_ref'], 'status': 'unavailable', 'detail': canonical(detail)})

def _dependency(store, run_id, episode_id, ref):
    rows = store.table(DEPENDENCIES).select({'run_id': run_id, 'episode_id': episode_id, 'sheet_ref': ref})
    return rows[0] if rows else None

def _heads(rows):
    result = {}
    for row in rows:
        if row['sheet_ref'] == row['current_ref']:
            result[row['family']] = row
    return result

def _register(repository, context, arguments, outcome, method):
    ref = (outcome.get('result') or {}).get('sheet_ref')
    if not ref:
        return None
    store = repository.store
    saved = repository.read(ref)
    prior = _rows(store, context)
    families = {row['sheet_ref']: row['family'] for row in prior}
    args = plain(arguments)
    family = _family(repository, args, saved, families)
    owner = repository._sheet_owner(ref)
    policy = _policy_for(repository.provider)
    if policy is not None and repository.provider == policy.SCORING_PROVIDER:
        family = identity('literature_scientific_sheet_owner_use', {'family': family, 'owner': owner})
    dependencies = list(dict.fromkeys([*_refs(args), *context.assignment.get('_automatic_literature_input_versions', ())]))
    receipt = {'version': VERSION, 'input_versions': dependencies, 'publication_operation_ref': outcome.get('operation_ref'), 'scientific_calculator': type(repository).__module__ + ':' + type(repository).__name__, 'credit': 'belongs_to_original_scientific_action', 'custody': 'owned' if owner == context.episode_id else 'admitted'}
    if _dependency(store, context.run_id, context.episode_id, ref) is None:
        store.table(DEPENDENCIES).put({'sheet_ref': ref, 'family': family, 'provider': repository.provider, 'adapter': type(repository).__module__ + ':' + type(repository).__name__, 'method': method, 'arguments': canonical(args), 'assignment': canonical(plain(context.assignment)), 'possessed': canonical(list(dict.fromkeys([*context.received_record_refs, *outcome['record_refs']]))), 'dependencies': canonical(dependencies), 'receipt': canonical(receipt)})
        store.table(CURRENT_SHEETS).put({'family': family, 'sheet_ref': ref, 'status': 'current', 'detail': None})
    return family

def _adapter(store, run_id, name):
    module, cls = name.split(':')
    factory = getattr(import_module(module), cls)

    def read_cells(context, *selection):
        ref, components = selection[-2:]
        source = store.get(ref)
        candidates = list(reversed(store.table(DEPENDENCIES).select({'run_id': run_id, 'sheet_ref': ref})))
        if not candidates:
            raise ContractError('literature_dependency_adapter_not_registered')
        for candidate in candidates:
            native = _adapter(store, run_id, candidate['adapter'])
            if native.provider == source.get('provider'):
                return native.fact_cells(context, [ref], components=components)
        raise ContractError('literature_dependency_adapter_not_registered')
    parameters = inspect.signature(factory).parameters
    return factory(store, run_id, **{'read_cells': read_cells} if 'read_cells' in parameters else {})

def _context(context, row, refs):
    return replace(context, assignment=json.loads(row['assignment']), received_record_refs=tuple(dict.fromkeys([*context.received_record_refs, *json.loads(row['possessed']), *refs])))

def _refresh_dependents(repository, context):
    store = repository.store
    produced = []
    visited = set()
    unavailable = set()
    while True:
        rows = _rows(store, context)
        heads = _heads(rows)
        replacements = {row['sheet_ref']: heads[row['family']]['sheet_ref'] for row in rows}
        pending = []
        for row in heads.values():
            if json.loads(row['receipt'])['custody'] != 'owned':
                continue
            args = json.loads(row['arguments'])
            policy = _policy_for(row['provider'])
            if policy is not None and hasattr(policy, 'dependent_revision'):
                decision, detail = policy.dependent_revision(row['provider'], args, replacements)
                if decision == 'unavailable':
                    _mark_unavailable(store, context, row['family'], detail)
                if decision in {'unavailable', 'skip'}:
                    continue
            if policy is not None and row['provider'] == policy.SCORING_PROVIDER and hasattr(policy, 'revised_arguments'):
                updated = policy.revised_arguments(args, replacements, _replace_refs)
            else:
                updated = _replace_refs(args, replacements)
            if canonical(args) != canonical(updated):
                if (row['family'], canonical(updated)) not in unavailable:
                    pending.append((row, updated))
        if not pending:
            return produced
        for row, arguments in pending:
            fingerprint = (row['family'], canonical(arguments))
            if fingerprint in visited:
                raise ContractError('literature_sheet_dependency_cycle')
            visited.add(fingerprint)
            adapter = _adapter(store, context.run_id, row['adapter'])
            refreshed = _context(context, row, replacements.values())
            key = identity('automatic_literature_sheet_refresh', {'version': VERSION, 'family': row['family'], 'arguments': arguments})
            try:
                outcome = getattr(adapter, row['method'])(refreshed, arguments, key)
            except ContractError as error:
                if not str(error).endswith(('component_not_received', 'cell_not_received', 'sheet_not_received')):
                    raise
                detail = {'version': VERSION, 'reason': str(error), 'input_versions': list(dict.fromkeys(_refs(arguments))), 'requirement': 'dependent_component_not_in_admitted_subset'}
                _mark_unavailable(store, context, row['family'], detail)
                unavailable.add(fingerprint)
                continue
            produced.append(outcome)

def _refresh_main(repository, context):
    """Create/update A105's original activity aggregation."""
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_sheet_policy as a105_policy
    store = repository.store
    rows = _rows(store, context)
    heads = list(_heads(rows).values())
    outputs = []
    for policy in (a105_policy,):
        provider, module, cls, requested = policy.main_binding()
        groups = {}
        for row in heads:
            if row['provider'] != provider:
                continue
            args = json.loads(row['arguments'])
            group = (args['assertion_ref'], args.get('target_context_ref'))
            groups.setdefault(group, []).append(row)
        for (assertion, target), contributions in groups.items():
            references = list(dict.fromkeys([*context.received_record_refs, *(row['sheet_ref'] for row in rows), *(ref for row in contributions for ref in json.loads(row['possessed']))]))
            main = _adapter(store, context.run_id, module + ':' + cls)
            main_context = replace(context, received_record_refs=tuple(references), assignment={**plain(context.assignment), requested: list(main.components), '_automatic_literature_input_versions': [row['sheet_ref'] for row in contributions]})

            def read_grade(row, view):
                grade = _adapter(store, context.run_id, row['adapter'])
                return bool(grade.fact_cells(view, [row['sheet_ref']], components=['evidence_amount']))
            plans = policy.main_plans(heads, contributions, main, assertion, target, main_context, read_grade)
            for arguments in plans:
                key = identity('automatic_literature_main_sheet', {'version': VERSION, 'provider': main.provider, 'arguments': arguments, 'input_versions': [row['sheet_ref'] for row in contributions]})
                outputs.append(main.populate(main_context, arguments, key))
    return outputs

def _merge(outcome, updates):
    if not updates:
        return outcome
    result = deepcopy(outcome)
    for field in ('record_refs', 'changed_record_refs'):
        result[field] = list(dict.fromkeys([*result.get(field, []), *(ref for update in updates for ref in update.get(field, []))]))
    return result

def _publication_receipt(repository, context, outcome):
    ref = (outcome.get('result') or {}).get('sheet_ref')
    if not ref:
        return None
    row = _dependency(repository.store, context.run_id, context.episode_id, ref)
    return json.loads(row['receipt']) if row else None

def _replay_publication(repository, context, outcome):
    receipt = _publication_receipt(repository, context, outcome)
    if receipt is None:
        return outcome
    if 'returned_record_refs' not in receipt or receipt['publication_operation_ref'] != outcome.get('operation_ref'):
        raise ContractError('literature_publication_return_not_retained')
    return {**outcome, **{field: receipt['returned_record_refs'][field] for field in ('record_refs', 'changed_record_refs') if field in receipt['returned_record_refs']}}

def _retain_publication(repository, context, outcome):
    receipt = _publication_receipt(repository, context, outcome)
    if receipt is not None:
        receipt['returned_record_refs'] = {field: outcome[field] for field in ('record_refs', 'changed_record_refs') if field in outcome}
        row = _dependency(repository.store, context.run_id, context.episode_id, outcome['result']['sheet_ref'])
        repository.store.table(DEPENDENCIES).put({**{name: row[name] for name in DEPENDENCIES.columns}, 'receipt': canonical(receipt)})
    return outcome

def publication(method):
    """Wrap the storage interface, including direct and atomic population."""
    if getattr(method, '_automatic_literature_updates', False):
        return method

    @wraps(method)
    def populate(repository, context, arguments, operation_key):
        store = repository.store
        if not _supported(repository):
            return method(repository, context, arguments, operation_key)
        if repository._operation(context.episode_id, operation_key) is not None:
            outcome = method(repository, context, arguments, operation_key)
            return _replay_publication(repository, context, outcome)
        with store.section('literature_sheet_updating') as outer:
            with store.transaction():
                outcome = method(repository, context, arguments, operation_key)
                if outcome.get('status') not in {'completed', 'partial'}:
                    return outcome
                _register(repository, context, arguments, outcome, method.__name__)
                if not outer:
                    return _retain_publication(repository, context, outcome)
                updates = _refresh_dependents(repository, context)
                updates.extend(_refresh_main(repository, context))
                updates.extend(_refresh_dependents(repository, context))
                return _retain_publication(repository, context, _merge(outcome, updates))
    populate._automatic_literature_updates = True
    return populate

def admitted(repository, context, cells, operation_key):
    """Refresh from the exact admitted subset; a handle grants no private cells."""
    if not cells or not _supported(repository):
        return
    store = repository.store
    for ref in dict.fromkeys((row['sheet_ref'] for row in cells)):
        source = store.get(ref)
        request = json.loads(store.get_artifact(source['request_ref']))
        owner = request['episode_id']
        row = _dependency(store, context.run_id, owner, ref)
        if row is None:
            adapter, method = (repository, 'populate')
        else:
            adapter, method = (_adapter(store, context.run_id, row['adapter']), row['method'])
        cell_refs = repository.cell_record_refs(cells) if hasattr(repository, 'cell_record_refs') else [cell['sheet_ref'] for cell in cells]
        refs = list(dict.fromkeys([*context.received_record_refs, *cell_refs]))
        receiving = replace(context, received_record_refs=tuple(refs))
        _register(adapter, receiving, request['arguments'], {'result': {'sheet_ref': ref}, 'record_refs': [ref], 'operation_ref': operation_key}, method)
    with store.section('literature_sheet_updating') as outer:
        if outer:
            _refresh_dependents(repository, receiving)
            _refresh_main(repository, receiving)
            _refresh_dependents(repository, receiving)

def current_sheet_refs(store, context, provider=None):
    """Saved current versions, restricted to this scientific owner/receiver."""
    heads = _heads(_rows(store, context))
    return [row['sheet_ref'] for row in heads.values() if row['current_status'] == 'current' and (provider is None or row['provider'] == provider)]

def current_scoring_sheets(store, context):
    """Project saved current evidence sheets, without another grading action.

    Only this episode's own calculations and exact admitted cells participate.
    Old scientific artifacts and archived report forms remain historical.
    """
    rows = _rows(store, context)
    if not rows:
        return []
    heads = list(_heads(rows).values())
    known = list(dict.fromkeys([*context.received_record_refs, *(row['sheet_ref'] for row in heads)]))
    view = replace(context, received_record_refs=tuple(known))
    result = []
    for row in heads:
        policy = _policy_for(row['provider'])
        if policy is None or row['provider'] != policy.SCORING_PROVIDER:
            continue
        native = _adapter(store, context.run_id, row['adapter'])
        cells = native.fact_cells(view, [row['sheet_ref']], components=list(native.components)) if row['current_status'] == 'current' else []
        args = json.loads(row['arguments'])
        axis = policy.AXIS
        inputs = []
        for grade in heads:
            if grade['provider'] != policy.GRADING_PROVIDER:
                continue
            arguments = json.loads(grade['arguments'])
            if arguments['assertion_ref'] != args['assertion_ref']:
                continue
            if not policy.includes_grade(args, grade['sheet_ref']):
                continue
            adapter = _adapter(store, context.run_id, grade['adapter'])
            actual = adapter.fact_cells(view, [grade['sheet_ref']], components=list(adapter.components))
            inputs.append({'sheet_ref': grade['sheet_ref'], 'available_components': [cell['component'] for cell in actual], 'cells': actual, 'input_versions': json.loads(grade['dependencies'])})
        receipt = json.loads(row['receipt'])
        receipt.pop('returned_record_refs', None)
        result.append({'version': VERSION, 'axis': axis, 'sheet_ref': row['sheet_ref'], 'assertion_ref': args['assertion_ref'], 'cells': cells, 'status': row['current_status'], 'missing_inputs': json.loads(row['current_detail']) if row['current_detail'] else None, 'subscoring_sheets': inputs, 'dependency_receipt': receipt, 'update_rule': 'automatic_before_original_action_credit', 'scientific_combination': 'existing_axis_calculator_and_declared_bindings', 'controller_progress': 'separate_from_evidence_scoring_sheet'})
    return result
