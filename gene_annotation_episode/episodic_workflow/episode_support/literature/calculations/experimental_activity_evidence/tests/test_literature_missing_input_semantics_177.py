"""Synthetic prospective input semantics and authentic pre-change v1 custody.

The retained v1 stores were produced by real selected writers before the change;
tests never relabel a prospective result as historical output.
"""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence import literature_transport_calculations as transport
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_binding_models as binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_transport_storage import LiteratureTransportRepository, transport_response_cells_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_binding_model_storage import LiteratureBindingModelRepository, binding_model_cells_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence.tests.test_literature_transport_calculations import example
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests.test_literature_binding_models import sheet, model
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.tests.test_literature_transport_storage import fixture as transport_fixture
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.tests.test_literature_binding_model_storage import fixture as binding_fixture


@pytest.mark.parametrize('primitive', transport.PRIMITIVE_ORDER)
def test_partial_concentrations_establish_only_missing_input(primitive):
    inputs = example()
    inputs['values'][primitive] = None
    inputs['covariance'] = None
    result = transport.populate_transport_response(inputs)
    name = 'apparent_km' if primitive == 'km' else primitive
    assert result['cells'][name]['unavailable_reason'] == 'concentration_not_supplied'
    assert result['cells']['condition_response']['unavailable_reason'] == 'concentration_inputs_not_supplied'
    for other in transport.PRIMITIVE_ORDER:
        if other != primitive:
            native = 'apparent_km' if other == 'km' else other
            assert result['cells'][native]['value'] == inputs['values'][other]

@pytest.mark.parametrize('field,key,reason,component', [('curve_keys', 'km', 'kinetic_curve_identity_not_supplied', 'condition_response'), ('measurement_keys', 'km', 'primitive_measurement_identity_not_supplied', 'condition_response_variance'), ('covariance', None, 'primitive_covariance_not_supplied', 'condition_response_variance')])
def test_distinct_missing_transport_inputs(field, key, reason, component):
    inputs = example()
    if key is None:
        inputs[field] = None
    else:
        inputs[field][key] = None
    result = transport.populate_transport_response(inputs)
    assert result['cells'][component]['unavailable_reason'] == reason
    assert result['cells']['apparent_km']['value'] == 12




@pytest.mark.parametrize('kind', ['transport', 'binding'])
def test_new_selected_writer_publishes_v2_and_new_typed_missing_labels(tmp_path, kind):
    if kind == 'transport':
        store, context, args, _ = transport_fixture(tmp_path, km=False)
        cls, schema = (LiteratureTransportRepository, transport_response_cells_schema)
    else:
        store, context, args, _ = binding_fixture(tmp_path, model=False)
        cls, schema = (LiteratureBindingModelRepository, binding_model_cells_schema)
    with store:
        repo = cls(store, context.run_id)
        outcome = repo.populate(context, args, 'new-v2-selected')
        ref = outcome['result']['sheet_ref']
        saved = repo.read(ref)
        assert saved['version'] == repo.record_version
        assert saved['version'].endswith('_v2')
        rows = repo.project_cells([ref], permitted_record_refs=[ref])
        validate_schema(rows, schema())
        missing = [row for row in rows if row['unavailable_reason']]
        assert missing and all((row['unavailable_reason'].endswith('_not_supplied') for row in missing))
        if kind == 'binding':
            assert all((row['model_kind'] == 'not_supplied' for row in rows))
        assert repo.populate(context, args, 'new-v2-selected') == outcome
        assert not store.list('observation')




