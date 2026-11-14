"""Complete original dynamic schemas and contract behavior; no native work."""
from copy import deepcopy
import hashlib
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import sys
from typing import get_type_hints, is_typeddict

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a104.library import protein_structure_contracts as science


@pytest.fixture(scope='module')
def original():
    name = 'gene_annotation_episode.episodic_workflow.root.a104._retained_original_protein_dynamic_contracts'
    path = Path(__file__).parent / 'fixtures/protein_structure_dynamic_schema/protein_structure_contracts.py'
    assert name not in sys.modules
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(name, loader)
    module = module_from_spec(spec)
    sys.modules[name] = module
    try:
        loader.exec_module(module)
        yield module
    finally:
        del sys.modules[name]


@pytest.mark.parametrize('action_custody', [False, True])
def test_complete_original_dynamic_definitions_and_detached_mutations(original, action_custody):
    expected = original.protein_structure_schema_definitions(action_custody=action_custody)
    actual = science.protein_structure_schema_definitions(action_custody=action_custody)
    assert canonical(actual) == canonical(expected)
    for name in actual:
        Draft202012Validator.check_schema({'$defs': actual, '$ref': '#/$defs/' + name})
    actual['FileIdentity']['properties'].clear()
    assert canonical(science.protein_structure_schema_definitions(action_custody=action_custody)) == canonical(expected)
    assert ('ProteinStructureActionCustody' in expected) is action_custody


def test_all_original_public_names_aliases_annotations_and_export_order(original):
    assert science.PUBLIC_TYPE_NAMES == original.PUBLIC_TYPE_NAMES
    assert science.__all__ == original.__all__
    for name in original.PUBLIC_TYPE_NAMES:
        assert hasattr(science, name)
        assert science.protein_structure_schema_ref(name) == original.protein_structure_schema_ref(name)
    old_types = {name: value for name, value in vars(original).items()
        if is_typeddict(value) and value.__module__ == original.__name__}
    actual_types = {name: value for name, value in vars(science).items()
        if is_typeddict(value) and value.__module__ == science.__name__}
    assert set(actual_types) == set(old_types)
    for name, typed in actual_types.items():
        assert list(get_type_hints(typed, include_extras=True)) == list(get_type_hints(old_types[name], include_extras=True))
    with pytest.raises(ValueError, match='invalid_schema'):
        science.protein_structure_schema_ref('NotAContract')


def file(raw, format):
    digest = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref='artifact_' + digest, sha256=digest, byte_length=len(raw), format=format)


@pytest.mark.parametrize('mutation', ['bool_count', 'float_count', 'extra_field', 'wrong_digest'])
def test_original_file_contract_rejects_invalid_identity(original, mutation):
    value = file(b'original schema fixture', 'pdb_3x_text')
    if mutation == 'bool_count':
        value['byte_length'] = True
    elif mutation == 'float_count':
        value['byte_length'] = float(value['byte_length'])
    elif mutation == 'extra_field':
        value['extra'] = 1
    else:
        value['sha256'] = 'f' * 64
    for owner in (original, science):
        with pytest.raises(ValueError):
            owner.validate_file_identity(value)


def saved():
    return dict(version='protein_structure_saved_sheet_v2',
        custody=dict(version='protein_structure_action_custody_v1', source_ref='source_' + 'a' * 24),
        sheet_file=file(b'engineering sheet', 'protein_structure_comparison_sheet_v1'),
        original_components_file=file(b'engineering components', 'protein_structure_components_v1'),
        operation='compare_protein_structures', original_mode='fit_then_evaluate_ca',
        allowed_uses=['recalculate', 'select_projection', 'use_transform'])


def test_original_action_descriptor_detachment_and_opt_in_cohort(original):
    value = saved()
    for owner in (original, science):
        result = owner.validate_saved_sheet_descriptor_v2(value)
        assert result == value
        result['allowed_uses'].clear()
        assert value['allowed_uses']
        legacy = owner.protein_structure_schema_definitions()
        action = owner.protein_structure_schema_definitions(action_custody=True)
        assert 'SavedSheetDescriptorV2' not in legacy and 'SavedSheetDescriptorV2' in action
        assert legacy['SavedSheetDescriptor']['properties']['version'] != action['SavedSheetDescriptorV2']['properties']['version']


@pytest.mark.parametrize('mutation', ['missing_uses', 'empty_uses', 'duplicate_uses', 'wrong_format', 'legacy_version'])
def test_original_action_descriptor_constraints(original, mutation):
    value = saved()
    if mutation == 'missing_uses':
        value.pop('allowed_uses')
    elif mutation == 'empty_uses':
        value['allowed_uses'] = []
    elif mutation == 'duplicate_uses':
        value['allowed_uses'] *= 2
    elif mutation == 'wrong_format':
        value['sheet_file']['format'] = 'text'
    else:
        value['version'] = 'protein_structure_saved_sheet_v1'
    for owner in (original, science):
        with pytest.raises(ValueError):
            owner.validate_saved_sheet_descriptor_v2(value)
