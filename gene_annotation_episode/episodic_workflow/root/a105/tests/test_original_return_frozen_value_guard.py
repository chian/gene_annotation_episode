"""Nonempty original typed-return custody, without claiming a scientific assessment.

The scalar is a synthetic control. This exercises the real saved-form guard,
not source interpretation, numerical grading or investigation-finding coverage.
"""
from importlib import import_module
import pytest

PACKAGE = __package__.rsplit('.tests', 1)[0]


@pytest.mark.parametrize('mutation', [None, 'frozen_value', 'assignment'])
def test_original_assignment_and_nonempty_frozen_value_remain_jointly_required(tmp_path, mutation):
    module = lambda name: import_module(PACKAGE + '.' + name)
    canonical = module('domain').canonical
    BindingContext = module('episode_bindings').BindingContext
    EpisodeRef = module('method_loop.identities').EpisodeRef
    with module('state').Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MAAA', molecule='protein')
        scope = store.validate_scope()
        store.db.execute('CREATE TABLE runtime_episodes(run_id TEXT,episode_id TEXT,path TEXT,request TEXT)')
        store.db.execute('CREATE TABLE runtime_report_attempts(run_id TEXT,parent_episode_id TEXT,decision_index INTEGER,child_episode_id TEXT,contract TEXT,form TEXT,failure TEXT,delivery_ref TEXT)')
        store.db.execute('CREATE TABLE runtime_actions(run_id TEXT,episode_id TEXT,decision_index INTEGER,action TEXT,result TEXT)')
        store.db.execute('CREATE TABLE runtime_forms(run_id TEXT,episode_id TEXT,facts TEXT)')
        run = 'synthetic-frozen-return'
        schema = {'type': 'object', 'properties': {'counter': {'type': 'integer', 'x-source': 'synthetic_control_counter'}}, 'required': ['counter'], 'additionalProperties': False}
        contract = {'decision': 'return the original controlled scalar', 'measurements': {'schema': schema}}
        selected = {'original_control_operand': 'first'}
        actual = {'original_control_operand': 'changed'} if mutation == 'assignment' else selected
        def context(path, assignment):
            request = {'message': {'scope': scope, 'episode_assignment': assignment}, 'report_contract': contract}
            result = BindingContext(run, EpisodeRef(run, path).episode_id, path[-1][0], path, scope, assignment, request)
            store.db.execute('INSERT INTO runtime_episodes VALUES(?,?,?,?)', (run, result.episode_id, canonical(path), canonical(request)))
            return result
        parent = context((('scientific_process', 'original-parent'),), {})
        child = context((*parent.path, ('results', 'child_0')), actual)
        form = {'counter': 2}
        frozen = {'synthetic_control_counter': 3 if mutation == 'frozen_value' else 2}
        store.db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,?)', (run, parent.episode_id, 0, canonical({'kind': 'episode_child', 'role': 'results', 'assignment': selected}), None))
        store.db.execute('INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?,?,?,?)', (run, parent.episode_id, 0, child.episode_id, canonical(contract), canonical(form), None, 'original-delivery'))
        store.db.execute('INSERT INTO runtime_forms VALUES(?,?,?)', (run, child.episode_id, canonical(frozen)))
        reader = module('episode_return_records').EpisodeReturnRecords(store, run, failure_prefix='frozen_control_')
        before = store.db.total_changes
        if mutation is None:
            returned, actual_form, actual_schema = reader._attempt(parent, 0)
            assert returned == child and actual_form == form and actual_schema == schema
        else:
            failure = 'frozen_return_conflict' if mutation == 'frozen_value' else 'commission_assignment_conflict'
            with pytest.raises(ValueError, match=failure):
                reader._attempt(parent, 0)
        assert store.db.total_changes == before
