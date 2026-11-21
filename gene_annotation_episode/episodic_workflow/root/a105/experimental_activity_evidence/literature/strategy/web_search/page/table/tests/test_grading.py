"""The A105 grading of this episode through the real runner on a real Store, without a model.

The run is linked with the public API (``link``) and stepped with ``EpisodeRun.next_decision`` (the Episode is
entered as ``run()`` enters it; ``decide`` is called; the model is not asked) and ``EpisodeRun.run_unit`` (one
journaled tool unit with its controller step). The ``reason`` unit commits the interpretation and saves the assay
grading sheet together on held records; the finding is read by code from the saved sheet and admitted by the
episode's ``RETURN_FORM``. Nothing is faked."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_assay_grading_prompt import (
    ASSAY_GRADING_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_assay_selection_prompt import (
    A105_ASSAY_SELECTION_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_assay_grading_features import (
    FEATURES, OPTIONAL)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import (
    CELLS, PROVIDER, LiteratureAssayGradingRepository)

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_unknown_classification import (
    QUANTITIES, classification_record, classification_request, classification_result, graded_fields, unknown_fields)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    canonical)

from .grading_world import CRITERIA, MODEL_SETTINGS, SETTINGS, TEXT, held_world, reasoning_selection

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').TableEvidenceExtraction
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
PATH = EPISODE.binding_path


def linked_run(directory, world, run_id='a105-table-grading', settings=SETTINGS):
    collaborators = {'store': world['store'],
                     'model_provider': world.setdefault('provider', ModelProvider(load_config(), directory / 'model_calls',
                                                                                    directory)),
                     'continuation': {PATH: settings}, 'services': {}}
    return link(BindingRegistry([EPISODE()]), PATH, world['input'], run_id=run_id,
                journal=RunJournal(directory / 'journal.sqlite3'), collaborators=collaborators)


def test_the_next_decision_offers_reason_with_the_owners_grading_instructions(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world)
    request = asyncio.run(run.next_decision())
    view = run.view
    summary = EPISODE()._summary(view)
    assert summary['assay_sheets'] == [] and summary['aggregation_sheets'] == []
    assert EPISODE.credit(summary, view.records) == 0
    assert view.controller_state is not None
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    tools = {entry['name']: entry for entry in request.context['tools']}
    assert 'reason' in tools and 'report' not in tools
    assert A105_ASSAY_SELECTION_TASK in request.instructions and ASSAY_GRADING_TASK in request.instructions
    assert 'Select the grader by the experiment\'s protocol and question' in request.instructions
    assert 'evidence_processing' in json.dumps(tools['reason']['input_schema'])
    assert request.context['assay_sheets'] == []
    world['store'].close()


def test_the_reason_unit_saves_the_sheet_and_the_return_is_its_controlled_features(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world)
    arguments = {'arguments': reasoning_selection(world), 'scope': world['scope'],
                 'page_source_ref': world['source'], 'proposed_annotation_ref': world['proposed'],
                 'examined_windows': []}
    unit = asyncio.run(run.run_unit(ToolCall('reason', arguments)))
    outcome = unit['outcome']
    assert outcome['status'] in ('completed', 'partial'), json.dumps(outcome)[:3000]
    grading, = outcome['evidence_processing']['gradings']
    sheet_ref = grading['result']['sheet_ref']
    reader = run.view.records
    assert reader.receipt(sheet_ref)['how'] == 'produced' and reader.get(sheet_ref)['provider'] == PROVIDER
    saved = LiteratureAssayGradingRepository(reader).read(sheet_ref)
    cells = saved['sheet']['cells']
    assert cells['measured_effect']['value'] == 12.5
    assert cells['source_log_evidence_ratio']['status'] == 'conditional'
    rows = {row['component'] for row in reader.table(CELLS).select({'sheet_ref': sheet_ref})}
    assert rows == set(LiteratureAssayGradingRepository.components)

    summary = EPISODE()._summary(run.view)
    features, = summary['assay_sheets']
    assert set(features) == set(FEATURES)
    assert features['sheet_refs'] == [sheet_ref] and features['experiment_refs'] == [world['assay']]
    assert features['evidence_type'] == 'activity_rate' and features['quantity_kind'] == 'rate'
    assert features['effect_value'] == 12.5 and features['effect_unit'] == 'U/mg'
    assert features['source_log_evidence_ratio'] == cells['source_log_evidence_ratio']['value']
    assert features['rate_regime_status'] == 'supported' and features['binding_regime_status'] == 'not_selected'
    assert features['prediction_model_kind'] == 'fixed_predictions_known_normal'
    # The experiment is graded and matched to the committed assessment: one answer, credit one.
    assert EPISODE.credit(summary, reader) == 1.0
    assert run.view.controller_state is not None

    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}
    result = EPISODE.final_to_parent(summary, completion, ())
    form = EPISODE.return_form.select(())
    admitted = form.admit(result, 'return')
    assert admitted == result and set(result) == {'credit', 'finding'}
    assert result['finding']['assay_count'] == 1 and result['finding']['assay_count_with_evidence_ratio'] == 1
    assert set(form.record_refs(admitted)) == {sheet_ref, world['assay'], world['proposed']}
    text_fields = [name for name, spec in FINAL.RETURN_FORM.fields['finding'].form.fields['assay_sheets'].items.fields.items()
                   if spec.type == 'text']
    assert text_fields and all(hasattr(FINAL.RETURN_FORM.fields['finding'].form.fields['assay_sheets'].items.fields[name],
                                       'options') for name in text_fields)
    selected = EPISODE.final_to_parent(summary, completion, (FINAL.SCREENING, FINAL.LEADS))
    assert EPISODE.return_form.select((FINAL.SCREENING, FINAL.LEADS)).admit(selected, 'return') == selected
    assert set(OPTIONAL) <= set(features)
    json.dumps(result, allow_nan=False)
    world['store'].close()


def test_an_interpretation_without_its_grading_is_refused_and_enters_the_iterator(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world)
    selection = reasoning_selection(world)
    del selection['evidence_processing']
    unit = asyncio.run(run.run_unit(ToolCall('reason', {
        'arguments': selection, 'scope': world['scope'], 'page_source_ref': world['source'],
        'proposed_annotation_ref': world['proposed'], 'examined_windows': []})))
    assert unit['outcome']['status'] == 'invalid'
    assert unit['outcome']['feedback']['code'] == 'applicable_evidence_requires_grading'
    assert EPISODE()._summary(run.view)['assay_sheets'] == []
    world['store'].close()


@pytest.mark.model_run
def test_the_model_grades_the_table_and_resume_replays_its_answers(tmp_path):
    """The real model reads the table and grades the assay through ``reason``; the run ends through the yield
    estimator, and a resume replays the recorded answers without a new model call."""
    from episode_runtime import resume
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, run_id='a105-table-model', settings=MODEL_SETTINGS)
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    assert journal.run_state('a105-table-model')[1]['ended_by'] == 'yield_stop'
    episode_path = ((EPISODE().grain_name, 'a105-table-model'),)
    recorded = journal.model_calls('a105-table-model', episode_path)
    assert recorded and recorded[-1]['response']
    assert any(unit[2]['tool'] == 'reason' for unit in journal.units('a105-table-model', episode_path))
    units = journal.units('a105-table-model', episode_path)
    print('UNITS', [(unit[2]['tool'], unit[2]['outcome'].get('status') if isinstance(unit[2]['outcome'], dict)
                     else None) for unit in units])
    print('RESULT', json.dumps(result)[:4000])
    assert set(result) == {'credit', 'finding'}
    assert isinstance(result['credit'], float) and EPISODE.return_form.select(()).admit(result, 'return') == result
    calls = len(list((tmp_path / 'model_calls').glob('call-*')))
    collaborators = {'store': world['store'],
                     'model_provider': world['provider'],
                     'continuation': {PATH: MODEL_SETTINGS}, 'services': {}}
    resumed = asyncio.run(resume(BindingRegistry([EPISODE()]), run_id='a105-table-model', journal=journal,
                                 collaborators=collaborators).run())['result'].as_record()
    assert resumed == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == calls
    world['store'].close()


def test_an_access_tool_reads_the_assigned_source_and_refuses_a_read_outside_it(tmp_path):
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world)
    envelope = {'scope': world['scope'], 'page_source_ref': world['source'],
                'proposed_annotation_ref': world['proposed']}
    read = asyncio.run(run.run_unit(ToolCall('source_read', {
        **envelope, 'arguments': {'source_ref': world['source'], 'representation': 'original', 'offset': 0,
                                  'limit': 40}})))['outcome']
    assert read['status'] == 'completed', read
    outside = asyncio.run(run.run_unit(ToolCall('source_read', {
        **envelope, 'arguments': {'source_ref': world['assay'], 'offset': 0, 'limit': 40}})))['outcome']
    assert outside['status'] == 'invalid'
    world['store'].close()


def graded_with_unknowns(world, unknown):
    """The scripted reasoning selection with the fields ``unknown`` left unknown in its grading (a null quantity,
    a null prediction model, a criterion ``unknown`` without support)."""
    selection = reasoning_selection(world)
    arguments = json.loads(selection['evidence_processing']['gradings'][0]['arguments'])
    for name in unknown:
        if name in arguments['quantities']:
            arguments['quantities'][name] = None
        elif name == 'prediction_model':
            arguments['prediction_model'] = None
        else:
            arguments['interpretations'][name] = {'status': 'unknown', 'support_refs': []}
    selection['evidence_processing']['gradings'][0]['arguments'] = json.dumps(arguments)
    return selection


def graded_run(directory, unknown, statuses=None):
    """One ``reason`` unit of the scripted grading that leaves ``unknown`` unknown, with no window read (so the
    unit itself classifies nothing). With ``statuses`` the classification of the sheet ``statuses['sheet_ref']`` is
    held by the Episode as a record passed in custody."""
    directory.mkdir()
    world = held_world(directory)
    store = world['store']
    if statuses is not None:
        result = classification_result(statuses['sheet_ref'], statuses['selection'], {'fields': statuses['fields']})
        artifact = store.artifact(canonical(result), 'application/json')
        held = store.put('source', classification_record(artifact), origin='caller')['id']
        world['input']['assignment']['received_record_refs'] += [artifact, held]
    run = linked_run(directory, world)
    outcome = asyncio.run(run.run_unit(ToolCall('reason', {
        'arguments': graded_with_unknowns(world, unknown), 'scope': world['scope'],
        'page_source_ref': world['source'], 'proposed_annotation_ref': world['proposed'],
        'examined_windows': []})))['outcome']
    assert outcome['status'] in ('completed', 'partial'), json.dumps(outcome)[:3000]
    assert outcome['unknown_classifications'] == []
    sheet_ref = outcome['evidence_processing']['gradings'][0]['result']['sheet_ref']
    summary = EPISODE()._summary(run.view)
    features, = summary['assay_sheets']
    facts = {'sheet_ref': sheet_ref, 'features': features, 'credit': EPISODE.credit(summary, run.view.records),
             'selection': LiteratureAssayGradingRepository(run.view.records).read(sheet_ref)['selection'],
             'result': EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1,
                                                         'credit': 0.0}, ())}
    assert EPISODE.return_form.select(()).admit(facts['result'], 'return') == facts['result']
    store.close()
    return facts


def test_credit_rests_on_the_held_classification_of_the_fields_a_sheet_leaves_unknown(tmp_path):
    """The classification is a record held through custody like any other: the Episode that holds it for its sheet
    earns the share of its entered fields and of its unknown fields held justified; unknown fields held unjustified,
    or not classified, earn nothing."""
    unknown = ['recovery', 'attributed_signal', 'rate_regime']
    plain = graded_run(tmp_path / 'unclassified', unknown)
    fields = len(unknown_fields(plain['selection'])), len(graded_fields(plain['selection']))
    assert fields == (3, 21) and unknown_fields(plain['selection']) == unknown
    assert plain['features']['unknown_classification_status'] == 'not_classified'
    assert (plain['features']['graded_field_count'], plain['features']['unknown_field_count']) == (21, 3)
    assert 'justified_unknown_count' not in plain['features']
    assert plain['credit'] == 18 / 21
    held = graded_run(tmp_path / 'classified', unknown, {
        'sheet_ref': plain['sheet_ref'], 'selection': plain['selection'],
        'fields': {'recovery': 'justified', 'attributed_signal': 'unjustified', 'rate_regime': 'justified'}})
    assert held['sheet_ref'] == plain['sheet_ref']
    assert held['features']['unknown_classification_status'] == 'classified'
    assert (held['features']['justified_unknown_count'], held['features']['unjustified_unknown_count']) == (2, 1)
    assert held['credit'] == 20 / 21
    sheet, = held['result']['finding']['assay_sheets']
    assert (sheet['graded_field_count'], sheet['unknown_field_count'], sheet['justified_unknown_count'],
            sheet['unjustified_unknown_count']) == (21, 3, 2, 1)


def test_a_sheet_of_nothing_but_unjustified_unknowns_earns_nothing_and_justified_unknowns_earn_the_unit(tmp_path):
    every = [*QUANTITIES, 'prediction_model', *CRITERIA]
    plain = graded_run(tmp_path / 'unclassified', every)
    assert plain['features']['unknown_field_count'] == plain['features']['graded_field_count'] == 21
    assert plain['features']['effect_status'] == 'unavailable' and plain['credit'] == 0
    missed = graded_run(tmp_path / 'unjustified', every, {
        'sheet_ref': plain['sheet_ref'], 'selection': plain['selection'],
        'fields': {name: 'unjustified' for name in every}})
    assert missed['features']['unjustified_unknown_count'] == 21 and missed['credit'] == 0
    absent = graded_run(tmp_path / 'justified', every, {
        'sheet_ref': plain['sheet_ref'], 'selection': plain['selection'],
        'fields': {name: 'justified' for name in every}})
    assert absent['features']['justified_unknown_count'] == 21 and absent['credit'] == 1.0


def test_the_classification_request_is_closed_over_the_unknown_fields_and_refuses_any_other_answer(tmp_path):
    plain = graded_run(tmp_path / 'unclassified', ['effect_variance', 'sampling_basis'])
    windows = [{'source_ref': 'source_1', 'representation': 'original', 'start': 0, 'end': 4, 'text': 'text'}]
    request = classification_request(plain['sheet_ref'], plain['selection'], windows)
    schema = request['output_schema']
    assert schema['properties']['fields']['required'] == ['effect_variance', 'sampling_basis']
    assert schema['properties']['fields']['additionalProperties'] is False
    assert all(schema['properties']['fields']['properties'][name] == {'enum': ['justified', 'unjustified']}
               for name in ('effect_variance', 'sampling_basis'))
    assert [item['field'] for item in request['context']['unknown_fields']] == ['effect_variance', 'sampling_basis']
    assert request['context']['source_windows'] == windows and 'effect' in request['context']['entered_fields']
    for answer in ({'fields': {'effect_variance': 'justified'}},
                   {'fields': {'effect_variance': 'justified', 'sampling_basis': 'the source says so'}},
                   {'fields': {'effect_variance': 'justified', 'sampling_basis': 'unjustified', 'effect': 'justified'}},
                   {'fields': {'effect_variance': 'justified', 'sampling_basis': 'unjustified'}, 'note': 'text'}):
        with pytest.raises(Exception):
            classification_result(plain['sheet_ref'], plain['selection'], answer)
    assert classification_result(plain['sheet_ref'], plain['selection'], {'fields': {
        'effect_variance': 'justified', 'sampling_basis': 'unjustified'}})['fields'] == {
            'effect_variance': 'justified', 'sampling_basis': 'unjustified'}


@pytest.mark.model_run
def test_the_grading_unit_classifies_an_all_unknown_sheet_against_the_window_it_read(tmp_path):
    """The defect of the first branch run, with the real model as the classifier: the Episode reads the window that
    prints all nine quantities and then saves a grading that leaves every field unknown. The tail of that same
    unit classifies each unknown field against the window read (one typed model call, recorded with the unit); the
    result is a record the Episode holds, and the credit is the share of the fields held justified."""
    world = held_world(tmp_path)
    run = linked_run(tmp_path, world, run_id='a105-table-classify', settings=MODEL_SETTINGS)
    envelope = {'scope': world['scope'], 'page_source_ref': world['source'],
                'proposed_annotation_ref': world['proposed']}
    window = {'source_ref': world['source'], 'representation': 'original', 'start': 0, 'end': len(TEXT.encode())}
    read = asyncio.run(run.run_unit(ToolCall('source_read', {**envelope, 'arguments': {
        'source_ref': world['source'], 'representation': 'original', 'offset': 0,
        'limit': len(TEXT.encode())}})))['outcome']
    assert read['status'] == 'completed', read
    summary = EPISODE()._summary(run.view)
    assert summary['examined_windows'] == [window]
    every = [*QUANTITIES, 'prediction_model', *CRITERIA]
    outcome = asyncio.run(run.run_unit(ToolCall('reason', {
        **envelope, 'arguments': graded_with_unknowns(world, every),
        'examined_windows': summary['examined_windows']})))['outcome']
    assert outcome['status'] in ('completed', 'partial'), json.dumps(outcome)[:3000]
    classified, = outcome['unknown_classifications']
    print('CLASSIFIED', json.dumps(classified))
    assert set(classified['fields']) == set(every) and set(classified['fields'].values()) <= {'justified',
                                                                                             'unjustified'}
    assert all(classified['fields'][name] == 'unjustified' for name in QUANTITIES)   # the window prints all nine
    reader = run.view.records
    assert reader.receipt(classified['classification_ref'])['how'] == 'produced'
    request = json.loads(next((tmp_path / 'model_calls').glob('call-*/request.json')).read_text())
    assert [item['text'] for item in request['context']['source_windows']] == [TEXT]
    assert request['output_schema']['properties']['fields']['additionalProperties'] is False
    summary = EPISODE()._summary(run.view)
    features, = summary['assay_sheets']
    assert features['unknown_classification_status'] == 'classified' and features['unknown_field_count'] == 21
    assert features['unjustified_unknown_count'] >= len(QUANTITIES)
    credit = EPISODE.credit(summary, reader)
    print('CREDIT', credit, features['justified_unknown_count'], features['unjustified_unknown_count'])
    assert credit == features['justified_unknown_count'] / 21 and credit <= 12 / 21
    world['store'].close()
