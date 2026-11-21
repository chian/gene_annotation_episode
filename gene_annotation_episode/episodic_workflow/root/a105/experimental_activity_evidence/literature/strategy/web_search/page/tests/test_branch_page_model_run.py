"""Branch runs of the source evidence examination (A105) with the real model. ``link(...).run()`` with the standard
``ModelProvider``, the real Store and journal; ``resume`` of the closed run replays the recorded answers.

The examination holds the ordinary tools by design (its goal: "Choose ordinary source operations or selected table,
ordered-reading or targeted-passage investigations as useful"), so no test asserts that the model delegates.

1. The examination alone on a source whose one results table sits in the first bytes before a long filler table: the
   model's own choice of units is reported.
2. The commission path, by ``run_unit(ChildCall('table', ...))`` with the real model in the child:
   the commissioner's objective (a value of the child's fixed vocabulary) is in the child's recorded model request,
   the child's grading enters the quantities the window prints, its unit classifies the fields it left unknown
   against the window it read (one typed model call, a closed answer per field), and its credit is the share those
   classified fields leave.
3. A source large enough that iteration matters (three assay tables, each followed by many passages): whether the
   model delegates is reported, not asserted.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, ChildCall, RunJournal, link, resume
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_unknown_classification import (
    graded_share)
from gene_annotation_episode.model_provider import ModelProvider, load_config

from . import grading_world as gw
from .grading_world import CHILD_PATHS, MODEL_SETTINGS, TEXT, held_world

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceEvidenceExamination
PATH = EPISODE.binding_path
CHILD_CLASSES = [getattr(importlib.import_module(PACKAGE + '.' + name + '.episode'), cls) for name, cls in zip(
    CHILD_PATHS, ('TableEvidenceExtraction', 'SourceCoverageImprovement', 'PassageEvidenceExtraction'))]
FILLER = 'Table 2. Purification summary of other preparations (no activity assay)\n' + '\n'.join(
    'row %d\tpreparation P%d\tprotein %d mg\tyield %d percent\tpurity %d percent' % (n, n, 10 + n, 20 + n % 60,
                                                                                    50 + n % 45)
    for n in range(1, 400))
# The commissioner's objective: a value of the examination's fixed vocabulary (messages/read_from_parent.OBJECTIVES).
OBJECTIVE = 'evidence_in_table'
# The three assay tables of the long source: the experiment label and its nine printed quantities.
ASSAYS = (('A', '12.5', '0.25', '0.9', '0.6', '0.8', '0.8', '1', '12', '0'),
          ('B', '8.4', '0.16', '0.85', '0.5', '0.7', '0.9', '1', '9', '0'),
          ('C', '3.1', '0.09', '0.95', '0.4', '0.6', '0.7', '1', '3', '0'))


def source_of(store, text, provider):
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                                  'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None,
                                  'parent_source_refs': []}, origin='caller')['id']
    return source, artifact


def assay_of(store, source, artifact, text, heading, label):
    """The assay reference anchored at its heading line in the source."""
    start = len(text[:text.index(heading)].encode())
    return store.put('reference', {'reference_type': 'assay', 'source_ref': source, 'accession': 'synthetic_assay_'
                                   + label.lower(), 'label': 'Experiment ' + label, 'sequence_ref': None,
                                   'molecule': None, 'length': None, 'term_refs': [], 'context_refs': [],
                                   'anchor': {'source_ref': source, 'artifact_ref': artifact, 'start': start,
                                              'end': start + len(heading.encode()), 'quote': heading}},
                     origin='caller')['id']


def commissioned(world, source, artifact, assays):
    """The entry input of the examination on ``source`` for the experiments ``assays``."""
    assignment = dict(world['input']['assignment'])
    assignment.update({'source_ref': source, 'artifact_ref': artifact,
                       'literature_task': {'version': 'literature_local_task_v1', 'kind': 'a105_experiments',
                                           'evidence_axis': 'A105', 'credit_unit': 1.0,
                                           'experiments': [{'experiment_ref': assay, 'assay_type': 'activity_rate'}
                                                           for assay in assays]},
                       'received_record_refs': [world['target'], source, artifact, *assays, world['reaction'],
                                                world['proposed']]})
    world.update({'source': source, 'artifact': artifact, 'assays': assays,
                  'input': {'assignment': assignment, 'message': {'objective': OBJECTIVE}, 'selection': []}})
    return world


def world_of(directory):
    """The held world of the examination, its source the one assay table followed by the long filler table."""
    world = held_world(directory)
    text = TEXT + '\n' + FILLER
    source, artifact = source_of(world['store'], text, 'synthetic_a105_paper')
    assay = assay_of(world['store'], source, artifact, text, gw.LINES[0], 'A')
    return commissioned(world, source, artifact, [assay])


def long_world_of(directory):
    """A source large enough that iteration matters: three assay tables (one row per quantity, each a number
    followed by its printed unit), each followed by sixty passages of methods and discussion."""
    world = held_world(directory)
    headings, sections = [], []
    for index, (label, effect, variance, recovery, attributed, total, test, reference, assertion,
                alternative) in enumerate(ASSAYS, 1):
        heading = ('Table %d. Experiment %s: purified enzyme hydrolysis rate assay with a known normal '
                   'fixed-prediction model.' % (index, label))
        headings.append((heading, label))
        rows = ['effect %s U/mg;' % effect, 'variance %s U/mg_squared;' % variance,
                'recovery %s fraction;' % recovery, 'attributed %s fraction;' % attributed,
                'total %s fraction;' % total, 'condition test %s fraction;' % test,
                'condition reference %s fraction;' % reference, 'assertion prediction %s U/mg;' % assertion,
                'alternative prediction %s U/mg.' % alternative]
        passages = ['Passage %s.%d. The preparation of experiment %s was dialysed in batch %d and stored on ice; '
                    'no rate was measured in this step, and buffer lot %d was used for the washes.'
                    % (label, n, label, n, 100 + n) for n in range(1, 61)]
        sections.append('\n'.join([heading, *rows, *passages]))
    text = '\n'.join(sections)
    source, artifact = source_of(world['store'], text, 'synthetic_a105_long_paper')
    assays = [assay_of(world['store'], source, artifact, text, heading, label) for heading, label in headings]
    return commissioned(world, source, artifact, assays)


def linked(directory, world, run_id):
    registry = BindingRegistry([EPISODE(), *(cls() for cls in CHILD_CLASSES)])
    continuation = {PATH: MODEL_SETTINGS, **{cls.binding_path: {**MODEL_SETTINGS, 'launch_instruction_directory': None}
                                             for cls in CHILD_CLASSES}}
    journal = RunJournal(directory / 'journal.sqlite3')
    world['collaborators'] = {'store': world['store'],
                              'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
                              'continuation': continuation, 'services': {}}
    return registry, journal, link(registry, PATH, world['input'], run_id=run_id, journal=journal,
                                   collaborators=world['collaborators'])


def report_facts(journal, run_id):
    units = journal.units(run_id, ((EPISODE().grain_name, run_id),))
    trace = [(unit[2]['kind'], unit[2].get('tool') or unit[2].get('slot'),
              unit[2]['outcome'].get('status') if unit[2]['kind'] == 'tool' else unit[2]['report']['credit'])
             for unit in units]
    print('BRANCH_UNITS', trace)
    print('BRANCH_DELEGATED', [name for kind, name, _ in trace if kind == 'child'])
    return units, trace


def sheet_facts(sheets):
    return [{name: features.get(name) for name in ('experiment_refs', 'effect_status', 'effect_value', 'effect_unit',
                                                   'effect_variance_status', 'effect_variance',
                                                   'source_log_evidence_ratio_status', 'source_log_evidence_ratio',
                                                   'graded_field_count', 'unknown_field_count',
                                                   'unknown_classification_status', 'justified_unknown_count',
                                                   'unjustified_unknown_count')}
            for features in sheets]


def check_close(tmp_path, world, registry, journal, run_id, closed, units):
    result = closed['result'].as_record()
    print('BRANCH_RESULT_CREDIT', result['credit'])
    print('BRANCH_RESULT_SHEETS', json.dumps(sheet_facts(result['finding']['assay_sheets'])))
    assert journal.run_state(run_id)[1]['ended_by'] == 'yield_stop'
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    for unit in units:
        if unit[2]['kind'] == 'child':
            report = unit[2]['report']
            print('BRANCH_CHILD_REPORT', json.dumps({'slot': report['slot'], 'credit': report['credit'],
                                                     'counts': report['counts'],
                                                     'objective': unit[2]['message']['objective'],
                                                     'sheets': sheet_facts(report['assay_sheets'])}))
            assert set(report) == {'slot', 'credit', 'assay_sheets', 'aggregation_sheets', 'counts',
                                   'lead_source_refs', 'screening_covered'}
            assert set(unit[2]['result']) == {'credit', 'finding'}
    calls = len(list((tmp_path / 'model_calls').glob('call-*')))
    again = asyncio.run(resume(registry, run_id=run_id, journal=journal,
                               collaborators=world['collaborators']).run())['result'].as_record()
    assert again == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == calls
    return result


def recorded_requests(tmp_path):
    return [json.loads((call / 'request.json').read_text())
            for call in sorted((tmp_path / 'model_calls').glob('call-*'))]


@pytest.mark.model_run
def test_the_examination_runs_on_its_own_decisions_and_resume_replays(tmp_path):
    world = world_of(tmp_path)
    run_id = 'a105-see-branch'
    registry, journal, run = linked(tmp_path, world, run_id)
    closed = asyncio.run(run.run())
    units, _ = report_facts(journal, run_id)
    first = recorded_requests(tmp_path)[0]
    assert first['context']['commission']['objective'] == OBJECTIVE
    assert first['instructions'].startswith('THIS EPISODE: page')
    check_close(tmp_path, world, registry, journal, run_id, closed, units)
    world['store'].close()


@pytest.mark.model_run
def test_the_table_commission_by_run_unit_with_the_real_model_in_the_child(tmp_path):
    world = world_of(tmp_path)
    run_id = 'a105-see-branch-rununit'
    registry, journal, run = linked(tmp_path, world, run_id)
    page = {'source_ref': world['source'], 'representation': 'original', 'artifact_ref': world['artifact']}
    window = {'source_ref': world['source'], 'representation': 'original', 'offset': 0,
              'limit': len(TEXT.encode())}
    unit = asyncio.run(run.run_unit(ChildCall('table', {
        'objective': 'grade_reported_experiment', 'page': page, 'selection': window})))
    # Every recorded request so far is the child's: its decisions and the classification its grading unit made.
    requests = recorded_requests(tmp_path)
    decisions = [request for request in requests if 'commission' in request['context']]
    classifications = [request for request in requests if 'unknown_fields' in request['context']]
    assert decisions and len(decisions) + len(classifications) == len(requests)
    for request in decisions:           # the commissioner's objective reached the child's model
        assert request['context']['commission']['objective'] == 'grade_reported_experiment'
        assert request['context']['commission']['selection'] == window
        assert request['instructions'].startswith('THIS EPISODE: table')
    for request in classifications:     # the typed classification: a closed answer per unknown field
        fields = request['output_schema']['properties']['fields']
        assert fields['additionalProperties'] is False and all(
            option['enum'] == ['justified', 'unjustified'] for option in fields['properties'].values())
        print('BRANCH_CLASSIFIED_FIELDS', [item['field'] for item in request['context']['unknown_fields']])
    sheets = unit['report']['assay_sheets']
    print('BRANCH_CHILD_SHEETS', json.dumps(sheet_facts(sheets)))
    # The window prints the effect: the child's grading entered it. Its unknown fields were classified against the
    # window it read, and its credit is the share its entered and justified fields earn.
    features, = sheets
    assert (features['effect_status'], features['effect_value'], features['effect_unit']) == ('populated', 12.5,
                                                                                              'U/mg')
    assert features['unknown_classification_status'] == 'classified'
    assert (features['justified_unknown_count'] + features['unjustified_unknown_count']
            == features['unknown_field_count'])
    assert unit['report']['credit'] == graded_share(features)
    closed = asyncio.run(run.run())
    units, _ = report_facts(journal, run_id)
    check_close(tmp_path, world, registry, journal, run_id, closed, units)
    world['store'].close()


@pytest.mark.model_run
def test_a_long_source_of_several_tables_and_many_passages_reports_whether_the_model_delegates(tmp_path):
    world = long_world_of(tmp_path)
    run_id = 'a105-see-branch-long'
    registry, journal, run = linked(tmp_path, world, run_id)
    closed = asyncio.run(run.run())
    units, _ = report_facts(journal, run_id)
    result = check_close(tmp_path, world, registry, journal, run_id, closed, units)
    print('BRANCH_LONG_ANSWERED', result['credit'], 'of', len(world['assays']))
    world['store'].close()
