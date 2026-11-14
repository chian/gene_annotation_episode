"""Cold projection of two actual pre-extraction Stores, not workflow reopening."""
import ast
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import shutil
import sqlite3
import sys
import types

import pytest

from ..domain import canonical
from ..library.a101_scoring import A101ScoringUnavailable
from ..scientific_process.native_correspondence_credit import A101SequenceCredit
from ..state import Store
from ..tool_grading_artifacts import source_tool_grading_entries

FIXTURES=Path(__file__).with_name('fixtures')/'retained_native_scoring'


def files(directory):
    return {str(path.relative_to(directory)):hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob('*')) if path.is_file()}


@contextmanager
def original_projector():
    """Load the exact retained class, rebasing only its relocated scalar import."""
    path=FIXTURES/'a101_credit_before_extraction.py'
    source=path.read_text();tree=ast.parse(source)
    selected=[n for n in tree.body if isinstance(n,ast.ImportFrom) and n.level==1 and n.module=='a101_scoring']
    assert len(selected)==1
    selected[0].module='library.a101_scoring'
    # The pure scalar module moved byte-exact; the retained full class and all
    # of its method bodies remain original. No sys.modules production alias.
    name=__package__+'._retained_original_native_projector'
    assert name not in sys.modules
    module=types.ModuleType(name);module.__package__=__package__.rsplit('.tests',1)[0]
    sys.modules[name]=module
    try:
        exec(compile(tree,str(path),'exec'),module.__dict__)
        yield module.A101SequenceCredit()
    finally:
        del sys.modules[name]


def snapshot(db):
    tables=[row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name:[tuple(row) for row in db.execute('SELECT * FROM "'+name+'" ORDER BY rowid')]
        for name in tables}


def forbid_writes(operation,*arguments):
    denied={sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_ALTER_TABLE,sqlite3.SQLITE_CREATE_INDEX,sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_INDEX,sqlite3.SQLITE_CREATE_TEMP_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_TRIGGER,sqlite3.SQLITE_CREATE_TEMP_VIEW,
        sqlite3.SQLITE_CREATE_TRIGGER,sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_DROP_INDEX,sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_DROP_VIEW,sqlite3.SQLITE_ATTACH,sqlite3.SQLITE_DETACH}
    return sqlite3.SQLITE_DENY if operation in denied else sqlite3.SQLITE_OK


@pytest.mark.parametrize('case',['database_blast','native_without_grader'])
def test_real_pre_extraction_store_keeps_original_projection_and_saved_payload(tmp_path,case,monkeypatch):
    origin=FIXTURES/case/'state';before=files(origin)
    manifest=json.loads((FIXTURES/'manifest.json').read_text())
    assert before==manifest['cases'][case]['files']
    copied=tmp_path/case/'state';shutil.copytree(origin,copied)
    def forbidden(*args,**kwargs):pytest.fail('Cold saved projection cannot publish, acquire, run native work or grade new input')
    from gene_annotation_episode.episodic_workflow.root.a101.library import blast_graders
    monkeypatch.setattr(Store,'artifact',forbidden)
    monkeypatch.setattr(Store,'put',forbidden)
    monkeypatch.setattr(blast_graders,'grade_blast_result',forbidden)
    with Store(copied) as store, original_projector() as original:
        stored=snapshot(store.db)
        assert not {'runtime_episodes','runtime_observations','runtime_record_receipts'}&stored.keys()
        observations=[json.loads(row[0]) for row in store.db.execute("SELECT data FROM records WHERE record_type='observation'")]
        assert len(observations)==1
        observation=observations[0]
        scope=store.validate_scope({'subject_refs':observation['subject_refs']})
        store.db.execute('PRAGMA query_only=ON');store.db.set_authorizer(forbid_writes)
        current=A101SequenceCredit()
        assert current.as_record()==original.as_record()
        empty=current(store,scope,known_record_refs=[])
        assert empty==original(store,scope,known_record_refs=[])
        assert empty['credit']==0
        if case=='database_blast':
            entries=source_tool_grading_entries(store,observation['source_ref'])
            assert len(entries)==1
            artifact=observation['native_blast']['shared_projection']['grading_artifact_ref']
            payload=store.get_artifact(artifact)
            saved=json.loads(payload)
            assert saved['schema']=='tool_grading_artifact_v2'
            assert saved['grading']==entries[0]['grading']
            result=current.read_details(store,scope,known_record_refs=[observation['id']],details_limit=50,details_offset=0)
            expected=original.read_details(store,scope,known_record_refs=[observation['id']],details_limit=50,details_offset=0)
            assert canonical(result)==canonical(expected)
            assert result['credit']==pytest.approx((1-math.exp(-0.025*10))*0.5*0.5)
            target,=observation['subject_refs']
            assert result['a101_sheet']['targets'][target]['profile']==['blast']
            assert store.get_artifact(artifact)==payload
        else:
            assert source_tool_grading_entries(store,observation['source_ref'])==[]
            for projector in (current,original):
                with pytest.raises(A101ScoringUnavailable,match='native_grader_not_attached'):
                    projector(store,scope,known_record_refs=[observation['id']])
        assert snapshot(store.db)==stored
        store.db.set_authorizer(None)
    assert files(origin)==before
    assert files(copied/'artifacts')==files(origin/'artifacts')
