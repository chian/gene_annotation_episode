"""The kinetic-contrast repository and its model view on the custody-scoped store: population from witnessed
quotations of a retained source, the saved sheet read back, projected, and viewed with the model repository,
through the real runner."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_kinetic_inputs import CONTEXT_FIELDS, SUBJECT_FIELDS

from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

KINETIC = 'literature_kinetic_storage:LiteratureKineticRepository'
MODEL = 'literature_kinetic_model_storage:LiteratureKineticModelRepository'
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_kinetic_model_storage import COMPONENTS as MODEL_COMPONENTS

PLACEHOLDER = 'source_' + 'a' * 24
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
UNIT = 'uM^-1min^-1'
TEXT = ('<p>π ProteinFixture constructX substrateN substrateD.</p><p>Parameter catalytic_efficiency.</p>'
        f'<p>numerator 8 {UNIT}</p><p>denominator 2 {UNIT}</p>'
        '<p>Same subject and definition; separate assays; reported protocols.</p><p></p>')


def witness(raw, text, occurrence=0):
    token, first = text.encode(), 0
    for turn in range(occurrence + 1):
        first = raw.index(token, first)
        last = first + len(token)
        if turn < occurrence:
            first = last
    return {'source_ref': PLACEHOLDER, 'representation': 'original', 'start': first, 'end': last, 'quote': text}


def selection(raw):
    """A closed kinetic selection over TEXT: the numbers and units are quoted, the interpretations witnessed."""
    shared = 'Same subject and definition; separate assays; reported protocols.'

    def interpreted(value):
        return {'value': value, 'witnesses': [] if value in ('unknown', 'unspecified', 'unreported')
                else [witness(raw, shared)]}

    def operand(row, token, index):
        unit = witness(raw, row)
        unit['start'] += len(row[:row.rindex(UNIT)].encode())
        unit['end'] = unit['start'] + len(UNIT.encode())
        unit['quote'] = UNIT
        return {'parameter_kind': {'value': 'catalytic_efficiency', 'witnesses': [witness(raw, 'catalytic_efficiency')]},
                'subject': {name: witness(raw, 'ProteinFixture') if name == 'molecule'
                            else witness(raw, 'constructX') if name == 'construct' else None for name in SUBJECT_FIELDS},
                'context': {name: witness(raw, 'substrateN' if index == 0 else 'substrateD') if name == 'substrate'
                            else None for name in CONTEXT_FIELDS},
                'measurement_identity': None,
                'measurement': {'number': {'witness': witness(raw, row), 'number_start': row.index(token),
                                           'number_end': row.index(token) + len(token)}, 'unit': unit},
                'qualification': interpreted('reported_point'),
                'uncertainty': {'statistic': interpreted('unreported'), 'magnitude': None, 'interval': None,
                                'unit': None, 'unit_relationship': interpreted('unknown'), 'confidence_level': None,
                                'count': None, 'repetition_basis': interpreted('unspecified'),
                                'estimate_basis': interpreted('unknown')}}
    return {'version': 'a105_kinetic_source_selection', 'source_ref': PLACEHOLDER, 'source_kind': 'synthetic_fixture',
            'numerator': operand(f'numerator 8 {UNIT}', '8', 0), 'denominator': operand(f'denominator 2 {UNIT}', '2', 1),
            'comparison': {name: interpreted(value) for name, value in {
                'subject_relationship': 'same_molecule_and_construct', 'parameter_definition_relationship': 'same',
                'substrate_arrangement': 'separate_assays', 'comparison_scope': 'reported_protocols',
                'nonintended_conditions_relationship': 'unknown'}.items()}}


def bound(value, reference):
    if isinstance(value, dict):
        return {key: bound(item, reference) for key, item in value.items()}
    if isinstance(value, list):
        return [bound(item, reference) for item in value]
    return reference if value == PLACEHOLDER else value


def test_a_kinetic_sheet_is_saved_read_back_projected_and_viewed_by_the_model_repository(world):  # noqa: F811
    reference, artifact = source(world, TEXT, 'application/xml')
    populate = call(KINETIC, 'populate', bound(selection(TEXT.encode()), reference), scope=world['scope'])
    populate['arguments']['role'] = 'reader'
    view = call(MODEL, 'populate', {'source_ref': SHEET, 'model_source_ref': None, 'model_witnesses': []},
                scope=world['scope'])
    view['arguments']['role'] = 'reader'
    populated, held, saved, cells, modelled, model_cells = run(world, 'kinetic', [populate,
        read(KINETIC, 'held_sheet_refs'),
        read(KINETIC, 'read', SHEET),
        read(KINETIC, 'project_cells', [SHEET], components=['numerator_parameter', 'denominator_parameter']),
        view,
        read(MODEL, 'project_cells', [{'from_step': 4, 'path': ['result', 'sheet_ref']}],
             components=MODEL_COMPONENTS[:1])], held=[reference, artifact])
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and held == [sheet]
    assert populated['result']['cells']['numerator_parameter']['value'] == 8.0
    assert populated['result']['cells']['denominator_parameter']['value'] == 2.0
    assert saved['input_source_ref'] == reference
    assert [(cell['component'], cell['value']) for cell in cells] == [('numerator_parameter', 8.0),
                                                                      ('denominator_parameter', 2.0)]
    assert modelled['status'] == 'completed'
    assert [(cell['component'], cell['kinetic_sheet_ref']) for cell in model_cells] == [(MODEL_COMPONENTS[0], sheet)]
