"""Original retained-child and controlled-form helpers for Root LUMPY tests."""
from copy import deepcopy
import json
from jsonschema import Draft202012Validator
from method_loop.episode import ClosedChildUnit
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.local_file_capture_results import SOURCE_REFS_SCHEMA, OUTCOMES_SCHEMA


def _tables(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted((tuple(row) for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')),
        key=repr) for name in names}


def _forbidden(*args, **kwargs):
    raise AssertionError("supplied VCF result path attempted forbidden native, parser or input work")


def _closed_child(workflow, root, parent, science):
    commission = workflow.journal.row("runtime_actions", parent.episode_id, 0)
    closed = workflow.selected(root.source, json.loads(commission["action"]), 0)
    assert isinstance(closed, ClosedChildUnit)
    assert closed.record.episode_id == science.episode_id and closed.record.path == science.path
    assert plain(closed.request.as_record()) == plain(science.request)
    assert closed.record.archived_record is not None
    return plain(closed.result.as_record())


HANDOFF_FORM = dict(type='object', additionalProperties=False, properties={
    'completed': dict(type='boolean', **{'x-source': 'execution_completed'}),
    'references': dict(type='array', uniqueItems=True,
        items=dict(type='string', format='reference', **{'x-reference-namespace': 'execution_handoff'}),
        **{'x-source': 'execution_handoff_refs'})}, required=['completed', 'references'])
CAPTURE_FORM = dict(type='object', additionalProperties=False, properties={
    'sources': deepcopy(SOURCE_REFS_SCHEMA), 'outcomes': deepcopy(OUTCOMES_SCHEMA),
    'completed': dict(type='boolean', **{'x-source': 'execution_completed'})},
    required=['sources', 'outcomes', 'completed'])


def _action(tool, arguments=None):
    return dict(selection=dict(kind='tool', tool=tool, arguments={} if arguments is None else arguments), report_update={})


def _commission(role, assignment, scope, form, objective):
    return dict(selection=dict(kind='episode_child', role=role, goal=objective, scope=scope,
        purpose='Return the explicitly requested native measurements with their original meanings and custody.',
        assignment=assignment, schema_json=json.dumps(form), initial_report_json='{}'), report_update={})


def _provider_value(value, schema):
    if 'anyOf' in schema:
        for branch in schema['anyOf']:
            candidate = _provider_value(value, branch)
            if Draft202012Validator(branch).is_valid(candidate):
                return candidate
        return value
    if schema.get('type') == 'string' and isinstance(value, dict) and schema.get('description', '').startswith('JSON encoding'):
        return json.dumps(value)
    if schema.get('type') == 'object' and isinstance(value, dict):
        result = dict(value)
        for name, field in schema.get('properties', {}).items():
            if name in result:
                result[name] = _provider_value(result[name], field)
            elif name in schema.get('required', []) and Draft202012Validator(field).is_valid(None):
                result[name] = None
        return result
    if isinstance(value, list) and 'items' in schema:
        return [_provider_value(item, schema['items']) for item in value]
    return value


