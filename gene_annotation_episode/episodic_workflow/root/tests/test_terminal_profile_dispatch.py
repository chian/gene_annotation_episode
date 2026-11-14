"""Current scientific profile lookup uses real library definitions, without running them."""
import importlib

import pytest

from gene_annotation_episode.episodic_workflow.root import terminal_scientific_evidence


# Literal names retained from the original public profile table. The descriptors,
# schema validators and drivers themselves are not invoked by this lookup check.
PROFILES = (
    ('native_expression_nmf', 'native_expression_nmf_contracts', 'validate_expression_nmf_run_plan'),
    ('native_fluorescence', 'native_fluorescence_contracts', 'validate_fluorescence_run_plan'),
    ('native_genomic_overlap', 'native_genomic_overlap_contracts', 'validate_genomic_overlap_run_plan'),
    ('native_chromatin_interactions', 'native_chromatin_interaction_contracts', 'validate_chromatin_run_plan'),
    ('native_atac_differential', 'native_atac_differential_contracts', 'validate_atac_run_plan'),
    ('native_protein_structure', 'native_protein_structure_contracts', 'validate_protein_structure_run_plan'),
    ('native_flux_balance', 'native_flux_balance_contracts', 'validate_flux_balance_run_plan'),
)


@pytest.mark.parametrize('profile,module_name,validator_name', PROFILES, ids=[row[0] for row in PROFILES])
def test_current_profile_resolves_actual_library_owner(profile, module_name, validator_name):
    actual_module = importlib.import_module('gene_annotation_episode.episodic_workflow.root.library.' + module_name)
    requested = {profile: {}}
    actual = terminal_scientific_evidence._profile(requested)
    assert actual is not None
    selected, validator, filename = actual
    assert selected == profile
    assert validator is getattr(actual_module, validator_name)
    assert validator.__module__ == actual_module.__name__
    assert filename == getattr(actual_module, 'RUN_PLAN_FILENAME')
    assert terminal_scientific_evidence._PROFILES[profile] == (module_name, validator_name, 'RUN_PLAN_FILENAME')
    assert requested == {profile: {}}


@pytest.mark.parametrize('requested', ({}, {'unknown_profile': {}},
    {'native_fluorescence': {}, 'native_protein_structure': {}}), ids=('absent', 'unknown', 'ambiguous'))
def test_original_unselected_profile_outcome_is_preserved(requested):
    assert terminal_scientific_evidence._profile(requested) is None
