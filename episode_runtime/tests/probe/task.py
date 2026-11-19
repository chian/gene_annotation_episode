"""The task: run the plan of the commission, one step per unit.

The task always offers a unit and never ends the Episode. When nothing is left of the plan it offers ``idle``, a
unit that does nothing and earns nothing; the Episode ends when its yield controller stops it. With the
controller this episode builds when the commissioner names none (a finite target of one credit per plan step)
that is exactly at the last plan step."""
import json
from pathlib import Path

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, TableDeclaration, ToolCall

from ..sheet_library import SHEET, cells, write_cell

CHILD_SLOTS = {'left': 'fact_collection/fact_extraction', 'right': 'fact_collection/fact_extraction',
               'nested': 'probe'}
SERVICES = ('counter', 'switch')
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['ref'],
          'properties': {'ref': {'type': 'string'}}}
INSTRUCTIONS = ('Answer with the ref of the record whose name is the wanted name. If the feedback says that record '
                'is not held, answer with the ref of the other record instead.')
LEDGER = TableDeclaration(name='probe_ledger', columns=('k', 'v'), key=('k',))
SOURCE = {'provider': 'probe', 'accession': None, 'uri': None, 'request_ref': None, 'version': None,
          'retrieved_at': None}
ANSWER_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['answer'],
                 'properties': {'answer': {'type': 'string'}}}


def idle(arguments, ctx):
    """Nothing is left of the plan: this unit does nothing. What it earns is the episode's credit (nothing)."""
    return {'idle': True}


def close(arguments, ctx):
    """The closing value the plan step carries (in a real episode: what the model wrote to close its work). It is
    this unit's outcome; the summary holds it and ``final_to_parent`` returns it when asked."""
    return {'closing': arguments}


def bump(arguments, ctx):
    """Use a declared service; an undeclared one is not reachable."""
    count = ctx.services['counter'].bump()
    try:
        ctx.services['secret']
        hidden = False
    except KeyError:
        hidden = True
    return {'count': count, 'secret_hidden': hidden, 'service_names': sorted(ctx.services)}


def echo(arguments, ctx):
    """Return the arguments (what ``decide`` saw in its context) beside what the tool's own context says."""
    return {'decide': arguments, 'tool': {'settings': ctx.settings, 'run_id': ctx.run_id,
                                          'episode_id': ctx.episode_id, 'binding_path': ctx.binding_path}}


def effect(arguments, ctx):
    """Write a record and an external side effect, once per operation key; then fail when the switch says so."""
    ref = ctx.store.artifact(json.dumps({'resumed': ctx.resumed}), 'application/json')
    log = Path(arguments['log'])
    lines = log.read_text().splitlines() if log.exists() else []
    already = ctx.operation_key in lines
    if not already:
        with log.open('a') as stream:
            stream.write(ctx.operation_key + '\n')
    if ctx.services['switch'].fail:
        raise RuntimeError('interrupted after the side effect')
    return {'ref': ref, 'resumed': ctx.resumed, 'operation_key': ctx.operation_key, 'already_logged': already}


def intent(arguments, ctx):
    """Write an intent marker; a rerun sees what its abandoned attempt wrote, reads it and may take it over."""
    seen = [{'ref': item['ref'], 'producer_unit': item['producer_unit'], 'held': ctx.store.holds(item['ref']),
             'content': ctx.store.get_artifact(item['ref']).decode()} for item in ctx.abandoned]
    if arguments['reclaim'] and seen:
        for item in seen:
            ctx.store.reclaim(item['ref'])
        marker = seen[0]['ref']
    else:
        marker = ctx.store.artifact('intent ' + ctx.operation_key + ' resumed ' + str(ctx.resumed), 'text/plain')
    if ctx.services['switch'].fail:
        raise RuntimeError('cut after the intent was written')
    return {'marker': marker, 'resumed': ctx.resumed, 'abandoned': seen}


def scoped(arguments, ctx):
    """What the custody-scoped store offers and refuses."""
    out = {'held': json.loads(ctx.store.get_artifact(arguments['held']))['name']}
    try:
        ctx.store.get_artifact(arguments['unheld'])
    except CustodyError:
        out['unheld'] = 'refused'
    with ctx.store.transaction():
        out['written'] = ctx.store.artifact('written in a transaction', 'text/plain')
    with ctx.store.open_artifact(arguments['held']) as handle:
        out['opened_artifact'] = {'name': json.loads(handle.read())['name'], 'carries_a_path': isinstance(handle.name, str),
                                  'writable': handle.writable()}
    out['raw_store_offered'] = [name for name in ('db', 'path', '_require', 'close', 'artifact_path')
                                if hasattr(ctx.store, name)]
    out['admission_offered'] = [name for name in ('admit_entry', 'pass_to', 'return_to', 'pass_records')
                                if hasattr(ctx.store, name)]
    out['context_has_records'] = hasattr(ctx, 'records')
    return out


def transactions(arguments, ctx):
    """A rolled-back transaction, a nested one whose inner part commits and whose outer part rolls back, and a
    committed one."""
    store, out = ctx.store, {}
    source = {'provider': 'probe', 'accession': None, 'uri': None, 'request_ref': None, 'version': None,
              'retrieved_at': None}
    try:
        with store.transaction():
            lost_artifact = store.artifact('rolled back ' + ctx.operation_key, 'text/plain')
            lost = store.put('source', {**source, 'artifact_ref': lost_artifact, 'text_ref': lost_artifact},
                             origin='caller')['id']
            out['held_inside'] = [store.holds(lost_artifact), store.holds(lost)]
            out['read_inside'] = store.get(lost)['provider']
            raise ValueError('abort the transaction')
    except ValueError:
        pass
    out['lost'] = [lost_artifact, lost]
    out['held_after_rollback'] = [store.holds(lost_artifact), store.holds(lost)]
    try:
        store.get(lost)
        out['read_after_rollback'] = 'read'
    except CustodyError:
        out['read_after_rollback'] = 'refused'
    try:
        with store.transaction():
            with store.transaction():
                inner = store.artifact('inner part ' + ctx.operation_key, 'text/plain')
            out['inner_held_before_outer_ends'] = store.holds(inner)
            raise ValueError('abort the outer transaction')
    except ValueError:
        pass
    out['inner'] = inner
    out['inner_held_after_outer_rollback'] = store.holds(inner)
    with store.transaction():
        kept_artifact = store.artifact('committed ' + ctx.operation_key, 'text/plain')
        kept = store.put('source', {**source, 'artifact_ref': kept_artifact, 'text_ref': kept_artifact},
                         origin='caller')['id']
    out['kept'] = [kept_artifact, kept]
    out['kept_record_artifact'] = store.get(kept)['artifact_ref']
    out['kept_listed'] = [row['id'] for row in store.list('source')]
    out['kept_count'] = store.count('source')
    return out


def reason(arguments, ctx):
    """Commit a reasoning payload under the scope of the held problem subjects, then read it back the three ways."""
    store = ctx.store
    scope = {'subject_refs': arguments['input_refs']}
    result = store.commit_reasoning(arguments['payload'], scope, ctx.operation_key)
    again = store.commit_reasoning(arguments['payload'], scope, ctx.operation_key)
    page = store.query_records('term', scope)
    view = store.reasoning_view(scope)
    return {'status': result['status'], 'errors': result['errors'], 'record_refs': result['record_refs'],
            'same_again': again == result,
            'queried_terms': [row['id'] for row in page['records']], 'query_total': page['total'],
            'view_terms': [row['id'] for row in view['terms']],
            'view_subjects': [row['id'] for row in view['subjects']],
            'subset': store.reference_subset([*result['record_refs'], arguments['unheld']], scope),
            'listed_terms': [row['id'] for row in store.list('term', scope)],
            'problem_subjects': store.problem()['subject_refs'],
            'targets': [row['id'] for row in store.targets()],
            'subjects': [row['id'] for row in store.subjects(scope)],
            'referenced_terms': store.references(scope)['term'], 'counted_terms': store.count('term', scope),
            'in_scope': [store.in_scope(ref, scope) for ref in result['record_refs']],
            'required_kinds': [store.require(ref)['record_type'] for ref in result['record_refs']],
            'current_accounts': [row['id'] for row in store.iter_current_accounts('interpretation_account', scope)],
            'current_account_count': store.count('interpretation_account', scope, current=True),
            'current_assessments': store.current_assessments(scope)}


def material(arguments, ctx):
    """Register material from held source bytes and from new bytes; the Episode holds what each call created."""
    store = ctx.store
    reused = store.register_material(source_ref=arguments['source_ref'], format='opaque', use='evidence')
    fresh = store.register_material(data=arguments['text'].encode(), name='note', format='opaque', use='evidence')
    source = store.get(fresh['source_ref'])
    try:
        store.register_material(source_ref=arguments['unheld'], format='opaque', use='evidence')
        unheld = 'registered'
    except CustodyError:
        unheld = 'refused'
    return {'reused': reused['id'], 'reused_source': reused['source_ref'], 'fresh': fresh['id'],
            'fresh_source': source['id'], 'fresh_artifact': source['artifact_ref'],
            'fresh_bytes': store.get_artifact(source['artifact_ref']).decode(), 'unheld_source': unheld,
            'materials': [row['id'] for row in store.list('material')]}


def unheld_scope(arguments, ctx):
    """A scope over a problem subject the Episode does not hold is refused by every content read."""
    scope, out = {'subject_refs': arguments['input_refs']}, {}
    for name, call in (('reasoning_view', lambda: ctx.store.reasoning_view(scope)),
                       ('query_records', lambda: ctx.store.query_records('subject', scope)),
                       ('scope_dimension_segments',
                        lambda: ctx.store.scope_dimension_segments(scope, arguments['input_refs'][0])),
                       ('get_input', lambda: ctx.store.get_input(arguments['input_refs'][0]))):
        try:
            call()
            out[name] = 'answered'
        except CustodyError:
            out[name] = 'refused'
    out['problem_subjects'] = ctx.store.problem()['subject_refs']
    return out


def sheet(arguments, ctx):
    """Write cells of a sheet through the library function, in one transaction; fail before commit when asked."""
    try:
        with ctx.store.transaction():
            rows = [write_cell(ctx.store, arguments['sheet'], cell, value, arguments['source_ref'])
                    for cell, value in arguments['cells']]
            if arguments.get('abort'):
                raise ValueError('abort the sheet')
    except ValueError:
        return {'aborted': True, 'held_cells': [row['cell'] for row in cells(ctx.store, arguments['sheet'])],
                'held_refs': [ctx.store.holds(row['id']) for row in rows]}
    return {'rows': [{'id': row['id'], 'cell': row['cell'], 'value': row['value'], 'revision': row['revision'],
                      'unit': row['unit'], 'operation_key': row['operation_key'], 'episode_id': row['episode_id']}
                     for row in rows],
            'held_cells': [[row['cell'], row['value']] for row in cells(ctx.store, arguments['sheet'])],
            'read_by_get': ctx.store.get(rows[0]['id'])['table']}


def read_cells(arguments, ctx):
    """The cells of a sheet this Episode holds; a named row it does not hold is refused."""
    out = {'cells': [[row['cell'], row['value'], row['episode_id'] == ctx.episode_id]
                     for row in cells(ctx.store, arguments['sheet'])]}
    for ref in arguments.get('unheld', []):
        try:
            ctx.store.table(SHEET).get(ref)
            out['unheld'] = 'read'
        except CustodyError:
            out['unheld'] = 'refused'
    return out


async def ask(arguments, ctx):
    """Ask the model from inside a tool; the call is recorded and replayed under this unit."""
    response = await ctx.model.complete('FAST', arguments['instructions'], {'question': arguments['question']},
                                        ANSWER_SCHEMA)
    if ctx.services['switch'].fail:
        raise RuntimeError('cut after the model answered')
    return {'answer': response['answer'], 'resumed': ctx.resumed}


def read_ref(arguments, ctx):
    return {'name': json.loads(ctx.store.get_artifact(arguments['ref']))['name']}


def attempt(call):
    """What a call returned, or the error it raised (so one unit can show several refusals)."""
    try:
        return {'ok': call()}
    except Exception as error:      # noqa: BLE001 - the tool reports whatever is raised
        return {'raised': type(error).__name__ + ': ' + str(error)[:160]}


def name_unheld(arguments, ctx):
    """Writes that name a record the Episode does not hold: a source record, a work-table row and material."""
    store, unheld = ctx.store, arguments['unheld']
    out = {'read': attempt(lambda: store.get_artifact(unheld).decode()),
           'put': attempt(lambda: store.put('source', {**SOURCE, 'artifact_ref': unheld, 'text_ref': unheld},
                                            origin='caller')['id']),
           'register': attempt(lambda: store.register_material(source_ref=arguments['unheld_source'],
                                                               format='opaque', use='evidence')['id']),
           'holds_after': store.holds(unheld)}
    held = store.artifact('bytes this unit wrote', 'text/plain')
    out['put_naming_its_own_artifact'] = attempt(lambda: store.holds(store.put(
        'source', {**SOURCE, 'artifact_ref': held, 'text_ref': held}, origin='caller')['id']))
    return out


def reason_plain(arguments, ctx):
    """Commit a reasoning payload under the scope of the given subjects; the error when it is refused."""
    result = attempt(lambda: ctx.store.commit_reasoning(arguments['payload'], {'subject_refs': arguments['input_refs']},
                                                        ctx.operation_key))
    if 'raised' in result:
        return result
    return {'status': result['ok']['status'], 'errors': result['ok']['errors'],
            'record_refs': result['ok']['record_refs']}


def scope_reads(arguments, ctx):
    """Scope arithmetic and coverage over an input the Episode does not hold, and the reference filter."""
    store, held, unheld = ctx.store, arguments['held'], arguments['unheld_input']
    scope = {'subject_refs': [unheld]}
    return {
        'validate_scope': attempt(lambda: store.validate_scope(scope)),
        'validate_scope_segment': attempt(lambda: store.validate_scope(
            {'subject_refs': [unheld], 'segments': [{'subject_ref': unheld, 'start': 0, 'end': 100000}]})),
        'scope_contains': attempt(lambda: store.scope_contains(scope, scope)),
        'scope_covers': attempt(lambda: store.scope_covers([{'subject_ref': unheld, 'start': 0, 'end': 5}], scope)),
        'record_coverage_of_a_built_row': attempt(lambda: store.record_coverage(
            {'id': held, 'record_type': 'hypothesis', 'subject_refs': [unheld]})),
        'query_naming_an_unheld_record': attempt(lambda: store.query_records(
            'term', {'subject_refs': arguments['held_inputs']}, references=[arguments['unheld_record']])['total']),
        'query_naming_a_missing_record': attempt(lambda: store.query_records(
            'term', {'subject_refs': arguments['held_inputs']}, references=['artifact_' + '0' * 64])['total']),
    }


def parse(arguments, ctx):
    """Register sequence material, parse it, and read what the parse made."""
    store = ctx.store
    material = store.register_material(data=arguments['fasta'].encode(), name='probe', format='fasta',
                                       molecule='protein')
    parsed = store.parse_material(material['id'])
    members = store.material_members(parsed['collection_ref'])['members']
    first = store.material_member(members[0]['id'])
    header = store.material_header(members[0]['id'])
    reference = store.material_reference(members[1]['id'])
    return {'material': material['id'], 'parse_ref': parsed['id'], 'collection_ref': parsed['collection_ref'],
            'status': parsed['status'], 'valid_records': parsed['valid_records'],
            'holds': [store.holds(parsed['id']), store.holds(parsed['collection_ref'])],
            'errors': store.material_errors(parsed['id'])['total'], 'members': len(members),
            'member_sequence': first['sequence'], 'header_text': header['text'],
            'header_artifact_text': store.get_artifact(header['artifact_ref']).decode(),
            'reference': reference['id'], 'reference_sequence': store.get_artifact(reference['sequence_ref']).decode(),
            'got_parse': store.get(parsed['id'])['record_type'],
            'listed': {kind: [row['id'] for row in store.list(kind)]
                       for kind in ('parse_attempt', 'collection', 'reference')},
            'parsed_again_is_the_same': store.parse_material(material['id'])['id'] == parsed['id']}


def follow(arguments, ctx):
    """Store reads that follow the references a held record names: ``{label: [operation, argument, ...]}``, each
    answered (its JSON value) or refused."""
    return {label: attempt(lambda call=call: getattr(ctx.store, call[0])(*call[1:]))
            for label, call in arguments['calls'].items()}


def parse_passed(arguments, ctx):
    """Parse material this Episode was passed, and read a member of a collection it was passed."""
    store = ctx.store
    out = {'parse': attempt(lambda: store.parse_material(arguments['material'])['id'])}
    if arguments.get('member'):
        out['member'] = attempt(lambda: store.material_member(arguments['member'])['sequence'])
        out['reference'] = attempt(lambda: store.material_reference(arguments['member'])['id'])
    return out


def many(arguments, ctx):
    """Write ``n`` source records and list them: the inventory is not cut at a silent page."""
    store = ctx.store
    for index in range(arguments['n']):
        artifact = store.artifact('record ' + str(index), 'text/plain')
        store.put('source', {**SOURCE, 'accession': 'N' + str(index), 'artifact_ref': artifact,
                             'text_ref': artifact}, origin='caller')
    return {'listed': len(store.list('source')), 'counted': store.count('source'),
            'page': len(store.list('source', None, 10, 5))}


def leave(arguments, ctx):
    """First attempt: write a marker and fail. Rerun: name the abandoned marker for the summary to read, and take
    it over only when asked."""
    if not ctx.resumed:
        marker = ctx.store.artifact(json.dumps({'name': 'marker of ' + ctx.operation_key}), 'application/json')
        if ctx.services['switch'].fail:
            raise RuntimeError('cut after the marker was written')
        return {'marker': marker, 'summary_read': None}
    seen = [item['ref'] for item in ctx.abandoned]
    read = [json.loads(ctx.store.get_artifact(ref))['name'] for ref in seen]
    if arguments['reclaim']:
        for ref in seen:
            ctx.store.reclaim(ref)
    return {'abandoned': seen, 'read_by_the_tool': read, 'held': [ctx.store.holds(ref) for ref in seen],
            'summary_read': seen[0]}


def row_write(arguments, ctx):
    """Write (or rewrite) one ledger row; fail afterwards when asked. A rerun reports what it was told."""
    table = ctx.store.table(LEDGER)
    before = [[row['v'], row['revision'], row['unit']] for row in table.select({'k': arguments['k']})]
    told = [{'written': item['written'] and [item['written']['v'], item['written']['revision']],
             'prior': item['prior'] and [item['prior']['v'], item['prior']['revision']]} for item in ctx.abandoned]
    if arguments.get('reclaim') and ctx.abandoned:
        for item in ctx.abandoned:
            ctx.store.reclaim(item['ref'])
        row = table.select({'k': arguments['k']})[0]
    else:
        row = table.put({'k': arguments['k'], 'v': arguments['v']})
    if arguments.get('fail') and ctx.services['switch'].fail:
        raise RuntimeError('cut after the row was written')
    return {'before': before, 'told': told, 'row': row['id'], 'value': row['v'], 'revision': row['revision'],
            'row_unit': row['unit'], 'resumed': ctx.resumed}


def read_rows(arguments, ctx):
    return {'rows': [[row['k'], row['v'], row['revision'], row['unit']] for row in ctx.store.table(LEDGER).select()]}


def write_tx(arguments, ctx):
    """Write an artifact and a source in one transaction; a rerun reports what it was told."""
    told = [item['ref'] for item in ctx.abandoned]
    with ctx.store.transaction():
        artifact = ctx.store.artifact('committed ' + ctx.operation_key, 'text/plain')
        source = ctx.store.put('source', {**SOURCE, 'accession': 'CUT', 'artifact_ref': artifact,
                                          'text_ref': artifact}, origin='caller')['id']
    return {'artifact': artifact, 'source': source, 'resumed': ctx.resumed, 'told': told}


TOOLS = {'idle': idle, 'close': close, 'follow': follow, 'bump': bump, 'echo': echo, 'effect': effect,
         'intent': intent, 'scoped': scoped,
         'transactions': transactions, 'reason': reason, 'material': material, 'unheld_scope': unheld_scope, 'sheet': sheet,
         'read_cells': read_cells, 'ask': ask, 'read_ref': read_ref, 'name_unheld': name_unheld,
         'reason_plain': reason_plain, 'scope_reads': scope_reads, 'parse': parse, 'parse_passed': parse_passed,
         'many': many, 'leave': leave, 'row_write': row_write, 'read_rows': read_rows, 'write_tx': write_tx}


def decide(summary, feedback, ctx):
    step = len(summary['outcomes'])
    if step >= len(summary['plan']):
        return ToolCall('idle', {})
    item = summary['plan'][step]
    if 'tool' in item:
        return ToolCall(item['tool'], item['arguments'])
    if 'child' in item:
        return ChildCall(item['child'], item['arguments'])
    if 'tool_with_count' in item:
        return ToolCall(item['tool_with_count'], {**item['arguments'],
                                                  'count': ctx.services['counter'].read('count')})
    if 'show_context' in item:
        return ToolCall('echo', {'settings': ctx.settings, 'services': sorted(ctx.services),
                                 'clock': {'now': ctx.clock.now, 'began_at': ctx.clock.began_at,
                                           'elapsed_seconds': ctx.clock.elapsed_seconds,
                                           'status': ctx.clock.status,
                                           'progress_time_position': None if ctx.clock.progress_time is None
                                           else ctx.clock.progress_time['position']},
                                 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
                                 'binding_path': ctx.binding_path, 'key': ctx.key})
    context = {**item['model'], 'step': step, 'feedback': feedback}
    if item.get('count_in_context'):
        context['count'] = ctx.services['counter'].read('count')
    return ModelRequest('FAST', INSTRUCTIONS, context, SCHEMA)


def action(response, summary, records, ctx):
    if response['ref'] in ctx.settings.get('refused_refs', []):
        raise Rejected({'refused_by_settings': response['ref']})
    # PROVISIONAL (owner decision 6): an answer that names a record this Episode does not hold is an invalid answer
    # like any other. The record is an argument of this episode's own tool; it is not a commission.
    if not records.holds(response['ref']):
        raise Rejected({'not_held': response['ref']})
    item = summary['plan'][len(summary['outcomes'])]
    if 'then' in item:
        return ToolCall(item['then'], {**item['arguments'], 'ref': response['ref']})
    return ToolCall('read_ref', {'ref': response['ref']})
