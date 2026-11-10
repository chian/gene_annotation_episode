"""Completed-work presentation must fit the installed SQLite interface."""
import json
import sqlite3
from types import SimpleNamespace

from gene_annotation_episode.episode_work_report import _object_sql, completed_action_reports


def database():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    return db


def test_first_decision_can_read_empty_completed_work():
    with database() as db:
        db.executescript('''
            CREATE TABLE runtime_actions(run_id,episode_id,decision_index,action,result);
            CREATE TABLE runtime_observations(run_id,episode_id,unit_index,observation);
        ''')
        workflow = SimpleNamespace(store=SimpleNamespace(db=db), run_id='synthetic',
            binding_context=lambda source: SimpleNamespace(received_record_refs=()))
        source = SimpleNamespace(episode_id='root', scope={'subject_refs': []},
            path=(('annotation', 'root'),))
        assert completed_action_reports(workflow, source, {}, before=0) == []


def test_projection_retains_every_field_beyond_native_function_arity():
    with database() as db:
        # Exercise a projection wider than this SQLite build's function arity.
        # This describes the database interface, not an episode work budget.
        width = db.getlimit(sqlite3.SQLITE_LIMIT_FUNCTION_ARG) // 2 + 1
        fields = tuple(f'field_{index}' for index in range(width))
        values = (None, {'native': [0.875, None, True], 'units': 'µmol'},
            [1, 'literal "quote"', None], 'plain text', 2.5)
        expected = {field: values[index % len(values)] for index, field in enumerate(fields)}
        payload = {**expected, 'unselected_source_body': 'not part of this projection'}
        statement = "SELECT json_set('{}','$.projected'," + _object_sql('a.result', fields)
        statement += ') FROM (SELECT ? AS result) a'
        actual = json.loads(db.execute(statement, (json.dumps(payload),)).fetchone()[0])
        assert actual == {'projected': expected}


def test_malformed_recorded_arguments_remain_null_operands():
    with database() as db:
        statement = 'SELECT ' + _object_sql('a.result', ('target_ref', 'components'))
        statement += ' FROM (SELECT ? AS result) a'
        actual = json.loads(db.execute(statement, ('not valid JSON',)).fetchone()[0])
        assert actual == {'target_ref': None, 'components': None}
