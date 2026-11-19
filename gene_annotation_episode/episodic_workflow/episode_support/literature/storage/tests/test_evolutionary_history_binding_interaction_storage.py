"""The binding interaction repository and its model view on the custody-scoped store: population from a methods
source and a retained image of four measured roles, read back, projected and extended by a model sheet."""
from io import BytesIO

from PIL import Image, ImageDraw

from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_binding_interaction_inputs import ID_FIELDS, ROLES, VERSION

from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

INTERACTION = 'literature_binding_interaction_storage:LiteratureBindingInteractionRepository'
MODEL = 'literature_binding_interaction_model_storage:LiteratureBindingInteractionModelRepository'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
TEXT = ('Synthetic binding case. IC50 parameter; Hill Kd parameter. formA constructA protocolA; formB constructB '
        'protocolB; apo; ligand0 ligand1; tracerX; fluorescence; relative signal; bufferX. IC50definition; '
        'Hilldefinition; separately assayed; shared conditions. fitA0 fitA1 fitB0 fitB1. Unit nM')


def picture(expressions):
    image = Image.new('RGB', (500, 200), 'white')
    draw = ImageDraw.Draw(image)
    for index, expression in enumerate(expressions):
        draw.text((205, 14 + index * 40), expression, fill='black')
    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


def selection(methods, image, expressions=('5', '40', '2', '4'), unit='nM'):
    """The four-role selection of the retained image, its witnesses quoting ``TEXT`` (held as ``methods``)."""
    def witness(quote):
        start = TEXT.index(quote)
        return {'kind': 'text', 'source_ref': methods, 'representation': 'original',
                'start': len(TEXT[:start].encode()), 'end': len(TEXT[:start + len(quote)].encode()), 'quote': quote}

    def enum(value, quote=None):
        return {'value': value, 'witnesses': [] if quote is None else [witness(quote)]}

    def definition(label):
        if label is None:
            return {'status': 'unknown', 'label': None, 'witnesses': [], 'canonical_witness': None}
        return {'status': 'known', 'label': label, 'witnesses': [witness(label)], 'canonical_witness': witness(label)}

    roles = {}
    for index, role in enumerate(ROLES):
        subject = 'A' if index < 2 else 'B'
        region = [200, 10 + index * 40, 400, 38 + index * 40]
        labels = {name: None for name in ID_FIELDS}
        labels.update(subject='form' + subject, construct='construct' + subject, state='apo',
                      experiment='protocol' + subject, ligand='ligand' + str(index % 2), tracer='tracerX',
                      readout='fluorescence', normalization='relative signal', conditions='bufferX',
                      parameter_definition='IC50definition')
        fit = ('fitA0', 'fitA1', 'fitB0', 'fitB1')[index]
        roles[role] = {
            'parameter_kind': enum('ic50', 'IC50 parameter'),
            'definitions': {name: definition(labels[name]) for name in ID_FIELDS},
            'physical_fit': {'canonical_witness': witness(fit), 'witnesses': [witness(fit)]},
            'measurement': {'image_id': 'table', 'cell_region': region,
                'expression': {'status': 'exact', 'candidates': [{'kind': 'image', 'image_id': 'table',
                    'region': region, 'quote': expressions[index]}], 'fragments': []},
                'unit': {'status': 'exact', 'candidates': [witness(unit)], 'fragments': []}},
            'uncertainty': {'statistic': enum('unreported', 'Synthetic binding case'), 'basis': enum('unknown'),
                'repetition_basis': enum('unspecified'), 'interval': None, 'confidence_level': None,
                'exact_count': None, 'minimum_count': None}}
    relationships = {name: {'status': 'matched' if name == 'common_conditions' else 'supported',
                            'witnesses': [witness('shared conditions' if name == 'common_conditions' else 'separately assayed')]}
                     for name in ('within_reference_subject', 'within_test_subject', 'ligand_correspondence',
                                  'parameter_definition', 'separate_assays', 'common_conditions')}
    return {'version': VERSION, 'source_ref': methods, 'source_kind': 'synthetic_fixture',
            'images': [{'image_id': 'table', 'source_ref': image, 'original_source_ref': image, 'mapping': None}],
            'parameter_kind': enum('ic50', 'IC50 parameter'), 'comparison_scope': 'reported_protocols',
            'roles': roles, 'relationships': relationships}


def inputs(world):
    methods, methods_artifact = source(world, TEXT, 'text/plain')
    image, image_artifact = source(world, picture(('5', '40', '2', '4')), 'image/png')
    return methods, image, [methods, methods_artifact, image, image_artifact]


def test_an_interaction_sheet_is_saved_read_back_and_projected(world):
    methods, image, held = inputs(world)
    populated, listed, saved, cells = run(world, 'interaction', [
        call(INTERACTION, 'populate', selection(methods, image), scope=world['scope']),
        read(INTERACTION, 'held_sheet_refs'),
        read(INTERACTION, 'read', SHEET),
        read(INTERACTION, 'project_cells', [SHEET])], held=held)
    sheet = populated['result']['sheet_ref']
    assert populated['status'] == 'completed' and listed == [sheet]
    assert saved['input_source_ref'] == methods
    assert {row['sheet_ref'] for row in cells} == {sheet}
    assert len(cells) == 8 and cells[0]['component'] == 'parameter_rr'
    assert populated['result']['cells']['parameter_rr']['value'] == cells[0]['value'] == 5.0


def test_a_model_sheet_over_the_interaction_sheet_is_saved_and_read_back(world):
    methods, image, held = inputs(world)
    interaction, model, listed, saved = run(world, 'interaction_model', [
        call(INTERACTION, 'populate', selection(methods, image), scope=world['scope']),
        call(MODEL, 'populate', {'source_ref': SHEET, 'model_source_ref': None, 'model_witnesses': []},
             scope=world['scope']),
        read(MODEL, 'held_sheet_refs'),
        read(MODEL, 'read', {'from_step': 1, 'path': ['result', 'sheet_ref']})], held=held)
    assert model['status'] == 'completed'
    assert listed == [model['result']['sheet_ref']]
    assert saved['input_source_ref'] == interaction['result']['sheet_ref']
