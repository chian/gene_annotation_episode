"""Own previously examined inputs for the currently selected external source.

Keep exact source witnesses and returned native measurement addresses together
across ordinary reads. This projects original successful own tool outcomes;
it acquires no bytes, judges no applicability and creates no scientific record.
It never reads a descendant's history or supplies this view to an ancestor.
"""
import json

from .communication import plain


def _measurement_selectors(value, path=()):
    if isinstance(value, dict):
        selector = value.get('measurement_selector')
        if isinstance(selector, dict) and selector.get('kind') == 'database_measurement':
            yield {'selector': selector, 'returned_field_path': list(path),
                'native_field_context': {key: value[key] for key in ('name', 'role', 'unit')
                                         if key in value}}
        for key, child in value.items():
            yield from _measurement_selectors(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _measurement_selectors(child, (*path, index))


def own_source_inputs(store, context):
    """Present exact already returned inputs, never unexamined source contents."""
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_actions'").fetchone() is None:
        return {}
    actions = store.db.execute("""
        SELECT action,result FROM runtime_actions
        WHERE run_id=? AND episode_id=? AND json_extract(action,'$.kind')='tool'
          AND (json_type(action,'$.arguments.source_ref')='text'
               OR json_type(result,'$.result.source_ref')='text')
          AND json_extract(result,'$.status') IN ('completed','partial')
        ORDER BY decision_index DESC""", (context.run_id, context.episode_id))
    source_ref = None
    for row in actions:
        action, outcome = json.loads(row['action']), json.loads(row['result'])
        selected = (action.get('arguments', {}).get('source_ref')
                    or (outcome.get('result') or {}).get('source_ref'))
        if selected in context.received_record_refs:
            source_ref = selected
            break
    if source_ref is None or not store.reference_subset([source_ref], plain(context.scope)):
        return {}

    witnesses, selectors = {}, {}
    for row in store.db.execute("""
        SELECT decision_index,action,result FROM runtime_actions
        WHERE run_id=? AND episode_id=?
          AND json_extract(action,'$.kind')='tool'
          AND json_extract(action,'$.tool') IN ('source.locate','source.experimental.records')
          AND json_extract(action,'$.arguments.source_ref')=?
          AND json_extract(result,'$.status') IN ('completed','partial')
        ORDER BY decision_index""", (context.run_id, context.episode_id, source_ref)):
        action, outcome = json.loads(row['action']), json.loads(row['result'])
        content = outcome.get('result')
        if not isinstance(content, dict):
            continue
        if action['tool'] == 'source.locate':
            for match in content.get('matches', []):
                witness = match.get('witness', {})
                artifact = match.get('artifact_ref', content.get('artifact_ref'))
                if (witness.get('source_ref') != source_ref or artifact is None
                        or not all(key in witness for key in
                                   ('representation', 'start', 'end', 'quote'))):
                    continue
                # Project selectable locations from the original authenticated
                # result; the host materializes quotes from those locations.
                location = {key: witness[key] for key in
                    ('source_ref', 'representation', 'start', 'end')}
                anchor = {'source_ref': source_ref, 'artifact_ref': artifact,
                    **{key: witness[key] for key in ('start', 'end')}}
                key = json.dumps([witness, artifact], sort_keys=True)
                retained = {'decision_index': row['decision_index'],
                    'witness': location, 'anchor': anchor, 'text': witness['quote']}
                window = match.get('context')
                if (isinstance(window, dict) and window.get('artifact_ref') == artifact
                        and all(key in window for key in ('start', 'end', 'text'))):
                    retained['context_anchor'] = {'source_ref': source_ref,
                        'artifact_ref': artifact, 'start': window['start'],
                        'end': window['end']}
                    retained['context_text'] = window['text']
                witnesses[key] = retained
        else:
            for selected in _measurement_selectors(content.get('records', []), ('records',)):
                selector = selected['selector']
                if selector.get('source_ref') != source_ref:
                    continue
                key = json.dumps(selector, sort_keys=True)
                selectors[key] = {'decision_index': row['decision_index'], **selected}
    if not witnesses and not selectors:
        return {}
    return {'source_ref': source_ref, 'examined_witnesses': list(witnesses.values()),
        'returned_measurement_selectors': list(selectors.values())}
