"""Synthetic direct-source four-role inputs; no scientific-source truth claims."""
import hashlib
from io import BytesIO
import jsonschema
from PIL import Image, ImageDraw
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_binding_interaction_inputs import ID_FIELDS, ROLES, VERSION, binding_interaction_arguments_schema, read_binding_interaction_inputs
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_contracts import ExperimentalContractError

def png(image):
    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()

def fixture(expressions=('5', '40', '2', '4'), unit='nM', extra=''):
    text = 'Synthetic binding case. IC50 parameter; Hill Kd parameter. formA constructA protocolA; formB constructB protocolB; apo; ligand0 ligand1; tracerX; fluorescence; relative signal; bufferX. IC50definition; Hilldefinition; separately assayed; shared conditions. fitA0 fitA1 fitB0 fitB1. Unit ' + unit + '. ' + extra
    raw = text.encode()

    def witness(quote, after=0):
        start = text.index(quote, after)
        return {'kind': 'text', 'source_ref': 'methods', 'representation': 'original', 'start': len(text[:start].encode()), 'end': len(text[:start + len(quote)].encode()), 'quote': quote}

    def enum(value, quote=None):
        return {'value': value, 'witnesses': [] if quote is None else [witness(quote)]}

    def definition(label):
        return {'status': 'unknown', 'label': None, 'witnesses': [], 'canonical_witness': None} if label is None else {'status': 'known', 'label': label, 'witnesses': [witness(label)], 'canonical_witness': witness(label)}

    def text_literal(quote):
        return {'status': 'exact', 'candidates': [witness(quote)], 'fragments': []}
    image = Image.new('RGB', (500, 200), 'white')
    draw = ImageDraw.Draw(image)
    roles = {}
    for index, role in enumerate(ROLES):
        subject = 'A' if index < 2 else 'B'
        region = [200, 10 + index * 40, 400, 38 + index * 40]
        draw.text((205, 14 + index * 40), expressions[index], fill='black')
        iw = {'kind': 'image', 'image_id': 'table', 'region': region, 'quote': expressions[index]}
        labels = {name: None for name in ID_FIELDS}
        labels.update(subject='form' + subject, construct='construct' + subject, state='apo', experiment='protocol' + subject, ligand='ligand' + str(index % 2), tracer='tracerX', readout='fluorescence', normalization='relative signal', conditions='bufferX', parameter_definition='IC50definition')
        roles[role] = {'parameter_kind': enum('ic50', 'IC50 parameter'), 'definitions': {name: definition(labels[name]) for name in ID_FIELDS}, 'physical_fit': {'canonical_witness': witness(('fitA0', 'fitA1', 'fitB0', 'fitB1')[index]), 'witnesses': [witness(('fitA0', 'fitA1', 'fitB0', 'fitB1')[index])]}, 'measurement': {'image_id': 'table', 'cell_region': region, 'expression': {'status': 'exact', 'candidates': [iw], 'fragments': []}, 'unit': text_literal(unit)}, 'uncertainty': {'statistic': enum('unreported', 'Synthetic binding case'), 'basis': enum('unknown'), 'repetition_basis': enum('unspecified'), 'interval': None, 'confidence_level': None, 'exact_count': None, 'minimum_count': None}}
    arguments = {'version': VERSION, 'source_ref': 'methods', 'source_kind': 'synthetic_fixture', 'images': [{'image_id': 'table', 'source_ref': 'image', 'original_source_ref': 'image', 'mapping': None}], 'parameter_kind': enum('ic50', 'IC50 parameter'), 'comparison_scope': 'reported_protocols', 'roles': roles, 'relationships': {name: {'status': 'matched' if name == 'common_conditions' else 'supported', 'witnesses': [witness('shared conditions' if name == 'common_conditions' else 'separately assayed')]} for name in ('within_reference_subject', 'within_test_subject', 'ligand_correspondence', 'parameter_definition', 'separate_assays', 'common_conditions')}}
    sources = {'methods': raw, 'image': png(image)}
    return (arguments, sources, witness, enum, text_literal, image)

def reader(sources, calls=None):

    def read(reference, representation):
        assert representation in ('original', 'text')
        if calls is not None:
            calls.append((reference, representation))
        raw = sources[reference]
        if isinstance(raw, Exception):
            raise raw
        return {'artifact_ref': 'artifact_' + hashlib.sha256(raw).hexdigest(), 'content': raw}
    return read

def run(args, sources):
    return read_binding_interaction_inputs(args, read_source=reader(sources))



def test_closed_schema_and_malformed_fields_reject_before_source_access():
    args, sources, *_ = fixture()
    schema = binding_interaction_arguments_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(args, schema)
    args['covariance'] = [[1]]
    calls = []
    with pytest.raises(ExperimentalContractError, match='closed_fields_required'):
        read_binding_interaction_inputs(args, read_source=reader(sources, calls))
    assert calls == []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(args, schema)
    schema['properties'].clear()
    assert binding_interaction_arguments_schema()['properties']
































