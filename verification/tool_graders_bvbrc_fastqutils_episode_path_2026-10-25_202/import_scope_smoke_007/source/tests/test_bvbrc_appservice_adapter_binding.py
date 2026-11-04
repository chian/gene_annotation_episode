"""Configured scientific implementation selection without native execution."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.bvbrc_appservice_adapters import bind_adapters, selected_adapter
from gene_annotation_episode import bvbrc_homology_bundle_adapter as homology
from test_api_bvbrc_appservice import CONFIG, original_request
from test_bvbrc_appservice_custody import selector


def pin():
    return {'adapter_id': homology.ADAPTER_ID, 'adapter_version': homology.ADAPTER_VERSION,
        'implementation_sha256': homology.implementation_sha256()}


def test_exact_installed_pin_binds_only_selected_implementation():
    row = pin()
    bound = bind_adapters([row])
    service = SimpleNamespace(scientific_adapters=bound)
    selected = {'adapter_id': row['adapter_id'], 'adapter_version': row['adapter_version'], 'parameters': {}}
    assert selected_adapter(service, selected) == (homology, row['implementation_sha256'])
    assert selected_adapter(service, None) is None
    assert selected_adapter(service, {**selected, 'adapter_version': 'other'}) is None


def test_wrong_implementation_pin_rejects_before_service_use():
    configured = deepcopy(CONFIG)
    configured['scientific_adapters'] = [{**pin(), 'implementation_sha256': '0' * 64}]
    with pytest.raises(ValueError, match='appservice_adapter_implementation_conflict'):
        BVBRCAppServiceService(SimpleNamespace(), configuration=configured)


def test_unknown_implementation_is_unbound_not_dynamically_imported():
    assert bind_adapters([{'adapter_id': 'not_installed', 'adapter_version': '1',
        'implementation_sha256': '0' * 64}]) == {}


def test_duplicate_identity_with_different_pins_is_not_an_implicit_choice():
    with pytest.raises(ValueError, match='appservice_adapter_configuration_conflict'):
        bind_adapters([pin(), {**pin(), 'implementation_sha256': '0' * 64}])


def test_bound_selector_requires_real_parameter_and_numerical_form_contract():
    configured = {**deepcopy(CONFIG), 'scientific_adapters': [pin()]}
    service = BVBRCAppServiceService(SimpleNamespace(), configuration=configured)
    selection = selector()
    selection['adapter'] = {'adapter_id': homology.ADAPTER_ID,
        'adapter_version': homology.ADAPTER_VERSION, 'parameters': {}}
    with pytest.raises(ValueError, match='homology_adapter_parameters_invalid'):
        service.result_catalog(original_request(), selection)


def test_unconfigured_scientific_selection_keeps_acquisition_operations_available():
    service = BVBRCAppServiceService(SimpleNamespace(), configuration=deepcopy(CONFIG))
    selection = selector()
    selection.update(endpoint='requested_projection',
        adapter={'adapter_id': 'not_installed', 'adapter_version': '1', 'parameters': {}})
    assert service.result_catalog(original_request(), selection)
