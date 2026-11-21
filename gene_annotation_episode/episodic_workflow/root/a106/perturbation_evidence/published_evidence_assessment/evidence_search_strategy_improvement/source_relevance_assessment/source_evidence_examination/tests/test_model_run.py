"""A real run of this examination with the real model, its three investigations linked beside it
(``episode_runtime/tests/test_model_run.py`` is the pattern; the world is the A106 grading world of
``source_coverage_improvement/tests/a106_world.py``): Jev assesses the held paper's candidates, the model picks one leaf per decision,
which runs with the model in its turn and returns its credit and controlled finding. The run ends
when this Episode's yield controller stops it; a resumed run replays the recorded answers without asking the model.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, resume

from ..source_coverage_improvement.tests.a106_world import SETTINGS, held_world, linked_run

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceEvidenceExamination
CHILDREN = [importlib.import_module(PACKAGE + '.' + name + '.episode').__dict__[cls] for name, cls in (
    ('source_coverage_improvement', 'SourceCoverageImprovement'),
    ('table_evidence_extraction', 'TableEvidenceExtraction'),
    ('passage_evidence_extraction', 'PassageEvidenceExtraction'))]
PATH = EPISODE.binding_path
RUN_ID = 'a106_source_examination_model_run'


def registry():
    return BindingRegistry([EPISODE(), *(child() for child in CHILDREN)])


@pytest.mark.model_run
def test_the_examination_and_its_investigations_run_with_the_model_and_resume_replays(tmp_path):
    store, leaf_entry, _, names = held_world(tmp_path)
    reading = leaf_entry['assignment']
    assignment = {**reading['page'], 'literature_task': reading['literature_task'],
                  'proposed_annotation_ref': reading['proposed_annotation_ref'], 'scope': reading['scope'],
                  'received_record_refs': reading['received_record_refs']}
    entry = {'assignment': assignment, 'message': {}, 'selection': []}
    settings = {path: {**SETTINGS, 'cost': 0.05} for path in (PATH, *(child.binding_path for child in CHILDREN))}
    linked, journal, collaborators = linked_run(tmp_path, [EPISODE(), *(child() for child in CHILDREN)], PATH,
                                                entry, store, RUN_ID, settings)
    first = asyncio.run(linked.run())
    record = first['result'].as_record()
    assert journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    assert set(record) == {'credit', 'finding'}
    EPISODE.return_form.select(()).admit(record, 'return')
    units = [unit[2] for unit in journal.units(RUN_ID, ((PATH.replace('/', '__'), RUN_ID),))]
    print('A106_PARENT_UNITS', [(unit.get('tool') or unit.get('slot'),
                                 (unit.get('outcome') or {}).get('status') if unit['kind'] == 'tool'
                                 else unit.get('report')) for unit in units])
    print('A106_PARENT_RESULT', json.dumps(record, sort_keys=True))
    for unit in units:
        if unit['kind'] == 'child':
            report = unit['report']
            assert set(report) <= {'slot', 'credit', 'finding', 'lead_source_refs'}
            assert set(report['finding']) == {'intervention_assessments', 'a106_subscores'}
    calls = list((tmp_path / 'model_calls').glob('call-*'))
    assert calls

    resumed = asyncio.run(resume(registry(), run_id=RUN_ID, journal=journal,
                                 collaborators=collaborators).run())['result'].as_record()
    assert resumed == record
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == len(calls)
    store.close()
