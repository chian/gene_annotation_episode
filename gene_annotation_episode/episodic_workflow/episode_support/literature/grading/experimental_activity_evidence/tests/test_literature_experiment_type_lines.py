"""Every registered experiment type has one plain line (what the method is and what it reports); the page shows these lines to
its model where it names a leaf's experiment_type."""
import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CLASS_OF_EXPERIMENT_TYPE, EXPERIMENT_TYPE_LINES, EXPERIMENT_TYPES, class_of_predicate, experiment_types_of_class)


def test_every_registered_experiment_type_has_exactly_one_line_and_no_other_name_has():
    assert set(EXPERIMENT_TYPE_LINES) == set(EXPERIMENT_TYPES) == set(CLASS_OF_EXPERIMENT_TYPE)
    for name, line in EXPERIMENT_TYPE_LINES.items():
        assert isinstance(line, str) and line.strip() == line and '\n' not in line and line.endswith('.'), name


def test_the_types_of_a_class_follow_the_predicate_of_the_claim():
    binding = experiment_types_of_class(class_of_predicate('binds'))
    assert len(binding) == 25 and 'proximity' in binding and 'pulldown' in binding and 'spectro_direct' not in binding
    assert experiment_types_of_class(class_of_predicate('catalyzes')) == ('spectro_direct',)
    with pytest.raises(ValueError):
        class_of_predicate('transports')
