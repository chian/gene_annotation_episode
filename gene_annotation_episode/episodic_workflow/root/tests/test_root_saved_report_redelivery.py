"""Real saved-record and parser boundaries with controlled report values.

These tests do not execute scientific tools, the iterator, or an HPC job.
"""
from contextlib import contextmanager
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.episode_contract_information import expand_fact_form
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef


@contextmanager
def saved_report(role, assignment=None):
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    try:
        db.executescript('''
            CREATE TABLE runtime_episodes
                (run_id TEXT, episode_id TEXT, path TEXT, request TEXT);
            CREATE TABLE runtime_report_attempts
                (run_id TEXT, parent_episode_id TEXT, decision_index INTEGER,
                 child_episode_id TEXT, delivery_ref TEXT, contract TEXT,
                 form TEXT, failure TEXT, report_contract_declaration TEXT);
            CREATE TABLE runtime_actions
                (run_id TEXT, episode_id TEXT, decision_index INTEGER, action TEXT);
            CREATE TABLE runtime_model_calls
                (run_id TEXT, episode_id TEXT, call_index INTEGER, response TEXT);
            CREATE TABLE runtime_forms (run_id TEXT, episode_id TEXT, facts TEXT);
        ''')
        run_id = 'root-saved-report-boundary'
        parent = EpisodeRef(run_id, (('annotation', 'root'),))
        child = EpisodeRef(run_id, (*parent.path, (role, 'child_0')))
        submitted = json.dumps({'type': 'object', 'properties': {
            'returned': {'$ref': 'episode-fact:recorded_value'}},
            'required': ['returned'], 'additionalProperties': False})
        prepared = expand_fact_form(submitted, child_role=role,
            facts_by_role={role: {'recorded_value': {'type': 'number',
                'meaning': 'Controlled recorded value.',
                'report_schema': {'type': 'number'}}}}, permitted_child_roles=[role])
        schema, declaration = prepared['expanded_schema'], prepared['declaration']
        contract = {'decision': 'Return the recorded value', 'measurements': {'schema': schema}}
        scope = {'subject': 'controlled-subject'}
        for identity, supplied in ((parent, {}), (child, assignment or {})):
            request = {'message': {'scope': scope, 'episode_assignment': supplied}}
            if identity == child:
                request['report_contract'] = contract
            db.execute('INSERT INTO runtime_episodes VALUES (?,?,?,?)',
                (run_id, identity.episode_id, json.dumps(identity.path), json.dumps(request)))
        for index in (0, 1):
            db.execute('INSERT INTO runtime_report_attempts VALUES (?,?,?,?,?,?,?,?,?)',
                (run_id, parent.episode_id, index, child.episode_id, 'original-delivery',
                 json.dumps(contract), json.dumps({'returned': 2.5}), None,
                 json.dumps(declaration) if index else None))
        db.execute('INSERT INTO runtime_forms VALUES (?,?,?)',
            (run_id, child.episode_id, json.dumps({'recorded_value': 2.5})))
        selection = {'kind': 'redeliver_report', 'delivery_ref': 'original-delivery',
            'schema_json': submitted, 'purpose': contract['decision']}
        db.execute('INSERT INTO runtime_model_calls VALUES (?,?,?,?)',
            (run_id, parent.episode_id, 1, json.dumps({'selection': selection})))
        reader = EpisodeReturnRecords(SimpleNamespace(db=db), run_id,
            failure_prefix='saved_report_')
        yield SimpleNamespace(db=db, reader=reader, parent=reader.context(parent.episode_id),
            child=child, schema=schema, declaration=declaration)
    finally:
        db.close()


@pytest.mark.parametrize('role', ['literature', 'results', 'scientific_process'])
@pytest.mark.parametrize('assignment', [{}, {'selection': {'unrelated': 'not a parser identity'}}])
def test_original_root_declaration_redelivers_without_axis_inference(role, assignment):
    with saved_report(role, assignment) as frame:
        before = frame.db.total_changes
        child, form, schema = frame.reader._attempt(frame.parent, 1)
        assert child.episode_id == frame.child.episode_id
        assert form == {'returned': 2.5} and schema == frame.schema
        assert frame.db.total_changes == before
        assert frame.reader._attempt(frame.parent, 1) == (child, form, schema)
        assert frame.db.total_changes == before


@pytest.mark.parametrize('field,value', [
    ('child_role', 'foreign_child'), ('expanded_schema_sha256', '0' * 64)])
def test_changed_saved_declaration_is_rejected(field, value):
    with saved_report('literature') as frame:
        frame.declaration[field] = value
        frame.db.execute('UPDATE runtime_report_attempts SET report_contract_declaration=? '
            'WHERE decision_index=1', (json.dumps(frame.declaration),))
        with pytest.raises(ValueError, match='saved_report_redelivery_declaration_invalid'):
            frame.reader._attempt(frame.parent, 1)


def test_frozen_fact_conflict_is_rejected_after_valid_declaration():
    with saved_report('literature') as frame:
        frame.db.execute('UPDATE runtime_forms SET facts=?',
            (json.dumps({'recorded_value': 9.0}),))
        with pytest.raises(ValueError, match='saved_report_frozen_return_conflict'):
            frame.reader._attempt(frame.parent, 1)


def test_redelivery_requires_the_original_child_delivery():
    with saved_report('literature') as frame:
        frame.db.execute("UPDATE runtime_report_attempts SET child_episode_id='foreign' "
            'WHERE decision_index=0')
        with pytest.raises(ValueError, match='saved_report_redelivery_origin_conflict'):
            frame.reader._attempt(frame.parent, 1)
