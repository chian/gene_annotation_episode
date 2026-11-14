"""Controlled A107 retained-value boundaries; no producer/native execution."""
from copy import deepcopy
import hashlib

from jsonschema import Draft202012Validator, ValidationError
import pytest

from gene_annotation_episode.episodic_workflow.root.a107 import molecular_sequence_result_contracts as stored
from gene_annotation_episode.episodic_workflow.root.a107.library import calibrated_signal_selection as calibrated
from gene_annotation_episode.episodic_workflow.root.a107.library import primer_placement_result_contracts as primer
from gene_annotation_episode.episodic_workflow.root.a107.library import protease_assay_context as protease
from gene_annotation_episode.episodic_workflow.root.a107.library.molecular_publication_bytes import _publication_bytes
from gene_annotation_episode.episodic_workflow.root.a107.native_file_capture import NativeFileCaptureError


class RetainedArtifact:
    """Declared Store metadata/byte ports; the actual integrity reader executes."""
    def __init__(self, raw):
        self.raw = raw
        digest = hashlib.sha256(raw).hexdigest()
        self.reference = 'artifact_' + digest
        self.metadata = {'id': self.reference, 'record_type': 'artifact', 'sha256': digest,
            'size': len(raw), 'media_type': 'application/octet-stream'}
        self.reads = []

    def _require(self, reference, allowed):
        assert reference == self.reference and allowed == {'artifact'}
        self.reads.append('metadata')
        return deepcopy(self.metadata)

    def get_artifact(self, reference):
        assert reference == self.reference
        self.reads.append('bytes')
        return self.raw


def test_retained_bytes_preserve_exact_original_payload_and_read_order():
    store = RetainedArtifact(b'\x00retained scientific payload\xff\n')
    assert _publication_bytes(store, store.reference) == store.raw
    assert store.reads == ['metadata', 'bytes']


@pytest.mark.parametrize('change', ['length', 'digest', 'metadata_identity'])
def test_retained_bytes_reject_changed_content_with_actual_capture_error(change):
    store = RetainedArtifact(b'original')
    if change == 'length':
        store.raw += b'changed'
    elif change == 'digest':
        store.raw = b'modified'
    else:
        store.metadata['id'] = 'artifact_' + '0' * 64
    with pytest.raises(NativeFileCaptureError) as error:
        _publication_bytes(store, store.reference)
    assert type(error.value) is NativeFileCaptureError
    assert error.value.code == str(error.value) == 'retained_artifact_mismatch'
    assert store.reads == (['metadata'] if change == 'metadata_identity' else ['metadata', 'bytes'])


def test_unknown_protease_context_and_original_qualifications_stay_unresolved():
    context = protease._context(None)
    assert context['enzyme_basis'] == 'unknown'
    assert context['calibration'] is context['product_per_cleavage'] is None
    assert set(context['units'].values()) == {None}
    assert stored._valid_protease_literal(context, 'protease_assay_context') is True
    assert stored._valid_protease_literal(protease.QUALIFICATIONS, 'protease_qualifications') is True
    assert stored._valid_protease_literal([], 'protease_qualifications') is False
    assert stored._valid_protease_literal(None, 'protease_unestimated') is False


@pytest.mark.parametrize('change,code,field', [
    ('unknown_field', 'closed_assay_context_required', '/assay_context'),
    ('blank_identity', 'identity_or_null_required', '/assay_context/enzyme_identity'),
    ('boolean_stoichiometry', 'positive_product_stoichiometry_required', '/assay_context/product_per_cleavage'),
    ('zero_stoichiometry', 'positive_product_stoichiometry_required', '/assay_context/product_per_cleavage'),
])
def test_protease_context_keeps_original_error_identity_and_reader_rejection(change, code, field):
    value = protease._context(None)
    if change == 'unknown_field':
        value['invented'] = 1
    elif change == 'blank_identity':
        value['enzyme_identity'] = ' '
    else:
        value['product_per_cleavage'] = True if change == 'boolean_stoichiometry' else 0
    before = deepcopy(value)
    with pytest.raises(protease.ProteaseKineticsContractError) as observed:
        protease._context(value)
    assert type(observed.value) is protease.ProteaseKineticsContractError
    assert (observed.value.code, observed.value.field, str(observed.value)) == (code, field, code + ':' + field)
    assert value == before
    assert stored._valid_protease_literal(value, 'protease_assay_context') is False


def test_supplied_calibrated_selector_uses_actual_current_caller_and_closed_schema():
    selection = {'version':'calibrated_signal_selection_v1', 'sample_ids':['sample'],
        'species_ids':['species'], 'calibration_ids':[]}
    value = {'version':stored.SUPPLIED_SELECTOR_VERSION, 'operation':stored.SUPPLIED_OPERATION,
        'mode':'supplied_measurements', 'action':'calculate',
        'input':{'reference':'source_supplied', 'namespace':'source'}, 'stored':None,
        'calculation_selection':selection, 'return_files':[]}
    before = deepcopy(value)
    assert stored.validate_molecular_sequence_supplied_selector(value) == before == value
    schema = calibrated.calibrated_signal_selection_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(selection)
    schema['properties']['sample_ids']['items']['type'] = 'null'
    assert calibrated.calibrated_signal_selection_schema()['properties']['sample_ids']['items']['type'] == 'string'


@pytest.mark.parametrize('change', ['duplicate_selection', 'unknown_field'])
def test_calibrated_selection_retains_original_closed_and_unique_constraints(change):
    value = {'version':'calibrated_signal_selection_v1', 'sample_ids':[], 'species_ids':[], 'calibration_ids':[]}
    if change == 'duplicate_selection':
        value['sample_ids'] = ['sample','sample']
    else:
        value['invented_quantity'] = 1
    with pytest.raises(ValidationError):
        Draft202012Validator(calibrated.calibrated_signal_selection_schema()).validate(value)


def operand(reference, sequence):
    raw = sequence.encode('ascii')
    digest = hashlib.sha256(raw).hexdigest()
    return {'version':primer.profile()['operand_version'], 'subject':{'id':reference},
        'sequence':sequence, 'parent_mapping':None,
        'mapping_failure':{'code':'subregion_mapping_unavailable'},
        'input_file':{'artifact_ref':'artifact_'+digest,'sha256':digest,'size_bytes':len(raw),'format':'ascii_sequence'},
        'associations':{},'footprint':[]}


@pytest.mark.parametrize('list_form', [False, True])
def test_primer_operand_forms_preserve_supplied_symbols_order_and_mapping_qualification(list_form):
    target = operand('target', 'acGT')
    first = operand('primer', 'aC')
    primers = [first, deepcopy(first)] if list_form else first
    arguments = {'target_ref':'target','primer_refs':['primer','primer'] if list_form else 'primer'}
    supplied = {'version':primer.OPERANDS_VERSION,'target':target,'primers':primers}
    before = deepcopy(supplied)
    assert primer.native_arguments(arguments,supplied) == {'long_seq':'acGT','short_seqs':['aC','aC'] if list_form else 'aC'}
    context = primer.scientific_context(arguments,supplied)
    assert context['target_mapping'] is None
    assert context['primer_mappings'] == ([None,None] if list_form else [None])
    assert supplied == before
    assert len(primer.operand_records(supplied)) == (3 if list_form else 2)


def test_primer_duplicate_reference_cannot_change_original_sequence_identity():
    supplied = {'version':primer.OPERANDS_VERSION,'target':operand('target','ACTG'),
        'primers':[operand('primer','AC'),operand('primer','TG')]}
    with pytest.raises(ValueError,match='^ordinary_primer_placement_duplicate_operand_conflict$'):
        primer.native_arguments({'target_ref':'target','primer_refs':['primer','primer']},supplied)


def test_primer_missing_source_files_remain_unavailable_in_context():
    unavailable = {'sheet':{'file':None,'state':'unavailable'},'components':{'file':None,'state':'unavailable'}}
    result = primer.context(sheet=None,components=None,source_files=unavailable)
    assert result['sheet_state'] == result['components_state'] == 'unavailable'
    for key in ('input','native_outcome','component_status','population','group_populations','definitions','issues'):
        assert result[key] is None
