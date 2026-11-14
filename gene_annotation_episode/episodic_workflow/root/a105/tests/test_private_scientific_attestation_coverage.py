"""Every additional prospective source gate authenticates current bytes and tampering."""
from importlib import import_module
import hashlib
import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a105'
PILOT = AXIS + '.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination'
CASES = (
    ('literature_kinetic_storage', None, '_dependencies', 'literature_kinetic_calculations.py'),
    ('literature_endpoint_signal_storage', 'LiteratureEndpointSignalRepository', '_original_implementation', 'literature_endpoint_signal_inputs.py'),
    ('literature_ion_discrimination_storage', 'LiteratureIonDiscriminationRepository', '_implementation_receipt', 'literature_ion_discrimination_inputs.py'),
    ('literature_product_coupling_storage', 'LiteratureProductCouplingRepository', '_implementation_receipt', 'literature_product_coupling_inputs.py'),
    ('literature_measurement_validation_storage', 'LiteratureMeasurementValidationRepository', '_implementation_receipt', 'literature_measurement_validation_inputs.py'),
    ('literature_measurement_comparison_storage', 'LiteratureMeasurementComparisonRepository', '_original_implementation', 'literature_measurement_comparison_inputs.py'),
    ('literature_concentration_window_storage', 'LiteratureConcentrationWindowRepository', '_original_implementation', 'literature_concentration_window_inputs.py'),
)

@pytest.mark.parametrize('pilot', (False, True))
@pytest.mark.parametrize('name, class_name, method, chosen', CASES)
def test_additional_prospective_guards_authenticate_exact_bytes(pilot, name, class_name, method, chosen, tmp_path, monkeypatch):
    module = import_module((PILOT + '.scoring.' if pilot else AXIS + '.library.') + name)
    if class_name is None:
        read = getattr(module, method)
    else:
        cls = getattr(module, class_name)
        repository = cls.__new__(cls)
        if hasattr(cls, '_bound_descriptor'):
            monkeypatch.setattr(repository, '_bound_descriptor', lambda: None)
        read = getattr(repository, method)
    receipt = read()
    hashes = receipt['sha256'] if 'sha256' in receipt else receipt['files']
    assert hashes
    assert all(value == hashlib.sha256(module.source_file(key).read_bytes()).hexdigest() for key, value in hashes.items())
    actual = module.source_file
    changed = tmp_path / chosen
    changed.write_bytes(actual(chosen).read_bytes() + b'\n# Unapproved byte change\n')
    monkeypatch.setattr(module, 'source_file', lambda key: changed if key == chosen else actual(key))
    with pytest.raises(module.ContractError, match='dependency_mismatch'):
        read()

@pytest.mark.parametrize('pilot', (False, True))
@pytest.mark.parametrize('name, constant', (
    ('literature_kinetic_inputs', 'LEGACY_DEPENDENCIES'),
    ('literature_optical_inputs', 'LEXICAL_DEPENDENCY'),
    ('literature_optical_validation', '_LEXICAL_DEPENDENCY'),
    ('literature_amount_inputs', 'LEXICAL_DEPENDENCY'),
    ('literature_amount_inputs', '_RELEASED027_LEXICAL_DEPENDENCY'),
))
def test_historical_release_module_labels_retain_original_identity(pilot, name, constant):
    module = import_module((PILOT + '.tools.' if pilot else AXIS + '.library.') + name)
    declaration = getattr(module, constant)
    labels = {key: value for key, value in declaration.items() if key == 'module' or key.endswith('_module')}
    assert labels
    assert all(value.startswith('gene_annotation_episode.literature_') for value in labels.values())
    assert all('.episodic_workflow.' not in value for value in labels.values())
