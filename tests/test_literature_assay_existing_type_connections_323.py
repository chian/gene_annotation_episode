"""Connect existing native reader outputs; all reports are synthetic fixtures."""
from copy import deepcopy
from dataclasses import replace
from importlib import import_module
from types import SimpleNamespace

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_assay_grading import COMPONENTS, grade_assay
from gene_annotation_episode.literature_assay_grading_inputs import read_assay_grading_inputs, source_schema
from test_literature_assay_grading_inputs import fixture as grading_fixture, SUPPORT


CASES = (
    ('kinetic', 'activity_rate', 'catalytic_efficiency', 'numerator_parameter'),
    ('binding', 'ligand_binding', 'binding_parameter', 'reference_parameter'),
    ('binding_interaction', 'ligand_binding', 'binding_discrimination_ratio', 'interaction_ratio'),
    ('binding_model', 'ligand_binding', 'log_binding_parameter_ratio', 'log_parameter_contrast'),
    ('transport', 'transport_response', 'substrate_response_ratio', 'condition_response'),
    ('optical', 'activity_rate', 'rate', 'net_rate'),
    ('partner', 'activity_rate', 'partner_rate_difference', 'partner_loss'),
    ('signal', 'protein_signal', 'signal_ratio', 'reported_ratio'),
    ('amount', 'protein_amount', 'protein_amount_ratio', 'amount_ratio'),
    ('active_site', 'protein_amount', 'sites_per_monomer', 'sites_per_total_monomer'),
    ('channel', 'transport_response', 'electrical_conductance', 'chord_conductance'),
    ('gel', 'protein_signal', 'band_display_fraction', 'direct_competitor_sensitive_shift'),
    ('gel', 'ligand_binding', 'band_display_fraction', 'direct_competitor_sensitive_shift'),
)


def native_case(path, name, **options):
    configuration = {
        'kinetic': ('test_literature_kinetic_storage', 'setup', 'kinetic', 'LiteratureKineticRepository', 'literature_kinetic_cells'),
        'binding': ('test_literature_binding_storage', 'setup_store', 'binding', 'LiteratureBindingRepository', 'literature_binding_cells'),
        'binding_interaction': ('test_literature_binding_interaction_storage', 'setup', 'binding_interaction', 'LiteratureBindingInteractionRepository', 'literature_binding_interaction_cells'),
        'binding_model': ('test_literature_binding_model_storage', 'fixture', 'binding_model', 'LiteratureBindingModelRepository', 'literature_binding_model_cells'),
        'transport': ('test_literature_transport_storage', 'fixture', 'transport', 'LiteratureTransportRepository', 'literature_transport_cells'),
        'optical': ('test_literature_optical_storage', 'setup', 'optical', 'LiteratureOpticalRepository', 'literature_optical_cells'),
        'partner': ('test_literature_partner_storage', 'fixture', 'partner', 'LiteraturePartnerRepository', 'literature_partner_cells'),
        'signal': ('test_literature_ratio_source_storage', 'native_case', 'ratio_source', 'LiteratureRatioSourceRepository', 'literature_ratio_source_cells'),
        'amount': ('test_literature_amount_storage', 'setup', 'amount', 'LiteratureAmountRepository', 'literature_amount_cells'),
        'active_site': ('test_literature_active_site_storage', 'setup', 'active_site', 'LiteratureActiveSiteRepository', 'literature_active_site_cells'),
        'channel': ('test_literature_channel_binding_188', 'setup', 'channel', 'LiteratureChannelRepository', 'literature_channel_cells'),
    }
    if name == 'gel':
        from test_literature_gel_storage import runtime_case
        store, context, arguments, repo, outcome, *_ = runtime_case(path)
        return store, context, repo, 'literature_gel_component_cells', outcome['result']['sheet_ref'], outcome
    else:
        fixture_module, setup, module, cls, namespace = configuration[name]
        store, context, arguments, *_ = getattr(import_module(fixture_module), setup)(path, **options)
        repository = getattr(import_module('gene_annotation_episode.literature_' + module + '_storage'), cls)
        repo = repository(store, context.run_id, **({'evidence_origin': 'synthetic_fixture'} if name == 'signal' else {}))
    outcome = repo.populate(context, arguments, 'native-selected')
    sheet_ref = outcome['result']['sheet_ref']
    if name == 'gel':
        context.received_record_refs = [*context.received_record_refs, *outcome['record_refs']]
    else:
        context = replace(context, received_record_refs=[*context.received_record_refs, *outcome['record_refs']])
    return store, context, repo, namespace, sheet_ref, outcome


def normalized(name, assay_type, quantity_kind, component, native):
    store, context, repo, namespace, sheet_ref, outcome = native
    if name == 'gel':
        component = next(row['component_key'] for row in outcome['result']['cells'] if row['component'] == component)
    args, source, record = grading_fixture()
    args.update(assay_type=assay_type, quantity_kind=quantity_kind)
    args['quantities'] = dict.fromkeys(args['quantities'])
    args['quantities']['effect'] = {'kind': 'received_component', 'namespace': namespace,
        'sheet_ref': sheet_ref, 'component': component}
    requests = []
    def read_cells(requested_namespace, reference, components):
        assert requested_namespace == namespace
        requests.append((reference, list(components)))
        return repo.fact_cells(context, [reference], components=components)
    extraction = read_assay_grading_inputs(args, read_source=source, read_record=record, read_cells=read_cells)
    assert requests == [(sheet_ref, [component])]
    return args, extraction, read_cells, source, record


@pytest.mark.parametrize('name,assay_type,quantity_kind,component', CASES)
def test_existing_reader_populates_shared_grade_with_its_native_meaning(tmp_path, name, assay_type, quantity_kind, component):
    native = native_case(tmp_path / name, name)
    try:
        args, extraction, reader, source, record = normalized(name, assay_type, quantity_kind, component, native)
        selected = args['quantities']['effect']
        rows = reader(selected['namespace'], selected['sheet_ref'], [selected['component']])
        validate_schema(rows, source_schema(selected['namespace']))
        row = rows[0]; cell = row.get('cell', row)
        assert cell['value'] is not None
        sheet = grade_assay(extraction)
        assert tuple(sheet['cells']) == COMPONENTS
        factor = .001 if cell['unit'] == 'nM' else 1.
        assert sheet['cells']['measured_effect']['value'] == pytest.approx(cell['value'] * factor)
        assert extraction['quantities']['effect']['source_refs'][0] == selected['sheet_ref']
        assert extraction['quantities']['effect']['measurement_keys']
        assert sheet['cells']['effect_variance']['value'] is None
        assert sheet['cells']['source_log_evidence_ratio']['value'] is None
        assert sheet['annotation_credit'] is None
        if name == 'gel':
            assert sheet['cells']['measured_effect']['unit'] == 'display_fraction'
            assert 'display_measurement_not_calibrated_molecular_occupancy' in sheet['cells']['measured_effect']['conditions']
        if name == 'binding':
            assert 'native_parameter_definition:ic50' in sheet['cells']['measured_effect']['conditions']
        if name == 'optical':
            assert 'native_endpoint:NADH_depletion' in sheet['cells']['measured_effect']['conditions']
        # A source's valid number cannot be rerouted into a different kind of experiment.
        invalid = deepcopy(args)
        invalid.update(assay_type='endpoint_conversion', quantity_kind='conversion_fraction')
        with pytest.raises(ContractError, match='native_quantity_mismatch'):
            read_assay_grading_inputs(invalid, read_source=source, read_record=record, read_cells=reader)
    finally:
        native[0].close()


def test_optical_estimated_covariance_is_preserved_and_not_upgraded_to_known(tmp_path):
    native = native_case(tmp_path, 'optical', status='estimated')
    try:
        args, extraction, reader, source, record = normalized('optical', 'activity_rate', 'rate', 'net_rate', native)
        args['quantities']['effect_variance'] = {**args['quantities']['effect'], 'component': 'variance_net_rate'}
        args['interpretations']['variance_correspondence'] = {'status': 'supported', 'support_refs': [SUPPORT]}
        extraction = read_assay_grading_inputs(args, read_source=source, read_record=record, read_cells=reader)
        variance = extraction['quantities']['effect_variance']
        assert variance['value'] == pytest.approx(.0024)
        assert variance['unit'] == 'uM/min_squared'
        assert 'estimated_covariance' in variance['qualifications']
        assert grade_assay(extraction)['cells']['effect_precision']['value'] == pytest.approx(1 / .0024)
        args['prediction_model'] = {'kind': 'fixed_predictions_known_normal', 'variance_interpretation': 'known',
            'support_refs': [SUPPORT]}
        with pytest.raises(ContractError, match='known_variance_conflicts_with_reader'):
            read_assay_grading_inputs(args, read_source=source, read_record=record, read_cells=reader)
    finally:
        native[0].close()


def test_binding_interaction_estimated_variance_retains_fit_context_without_becoming_an_effect(tmp_path):
    from test_literature_binding_interaction_model_inputs import setup_model
    from test_literature_binding_interaction_model_storage import populate
    from gene_annotation_episode.literature_assay_grading_inputs import _component
    store, context, native_args, model_args, *_ = setup_model(tmp_path, status='estimated')
    try:
        repo, owner, _, outcome, _ = populate(store, context, native_args, model_args)
        ref = outcome['result']['sheet_ref']
        selector = {'kind': 'received_component', 'namespace': 'literature_binding_interaction_model_cells',
            'sheet_ref': ref, 'component': 'log_interaction_variance'}
        def read_cells(namespace, reference, components):
            assert namespace == selector['namespace']
            return repo.fact_cells(owner, [reference], components=components)
        operand, row = _component(selector, read_cells)
        assert operand['value'] == pytest.approx(.16)
        assert operand['unit'] == 'dimensionless_squared'
        assert operand['origin'] == 'synthetic'
        assert 'estimated_covariance' in operand['qualifications']
        args, source, record = grading_fixture()
        args.update(assay_type='ligand_binding', quantity_kind='log_binding_discrimination')
        args['quantities'] = dict.fromkeys(args['quantities'])
        args['quantities']['effect'] = selector
        with pytest.raises(ContractError, match='native_quantity_mismatch'):
            read_assay_grading_inputs(args, read_source=source, read_record=record, read_cells=read_cells)
    finally:
        store.close()


def test_same_kinetic_reader_can_feed_transport_km_without_relabelling_other_parameters(tmp_path):
    native = native_case(tmp_path / 'km', 'kinetic', kind='Km', unit='uM')
    try:
        _, extraction, _, _, _ = normalized('kinetic', 'transport_response', 'transport_parameter', 'numerator_parameter', native)
        effect = grade_assay(extraction)['cells']['measured_effect']
        assert effect['value'] == 8 and effect['unit'] == 'uM'
    finally:
        native[0].close()
    native = native_case(tmp_path / 'kcat', 'kinetic', kind='kcat', unit='s^-1')
    try:
        with pytest.raises(ContractError, match='native_quantity_mismatch'):
            normalized('kinetic', 'transport_response', 'transport_parameter', 'numerator_parameter', native)
    finally:
        native[0].close()
