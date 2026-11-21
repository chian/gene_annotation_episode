"""The real published paragraph (J Biol Chem 2025, PMC11795597, ThdF kinetics): its record gives only what the paragraph states, and the criteria it supports."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spectro_direct_converter import _criterion, convert_spectro_direct
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spectro_direct_grader import CRITERIA, grade_spectro_direct
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spectro_direct_cases import real_record


def test_the_real_paragraph_supports_no_criterion_it_does_not_state():
    graded = grade_spectro_direct(real_record())
    assert {name: _criterion(graded, name)['status'] for name in CRITERIA} == dict.fromkeys(CRITERIA, 'unknown')      # a kinetic-constants paragraph with no control, no wavelength, no series and no concentrations


def test_the_real_paragraph_gives_the_turnover_as_the_effect_with_no_variance_and_the_mass_unknown():
    converted = convert_spectro_direct(grade_spectro_direct(real_record()))
    quantities = converted['extraction']['quantities']
    assert quantities['effect']['value'] == 0.21 and quantities['effect']['unit'] == 's^-1' and converted['extraction']['quantity_kind'] == 'turnover'
    assert quantities['effect_variance'] is None and converted['null_components']['effect_variance'] == 'spread_kind_not_stated'      # the plus-minus sign is not named a standard error or deviation
    assert converted['enzyme_mass_g_per_mol'] is None and {c['status'] for c in converted['extraction']['interpretations'].values()} == {'unknown'}
    assert converted['direction_field_support'] == 'direct' and 'qualitative_effect' not in converted
